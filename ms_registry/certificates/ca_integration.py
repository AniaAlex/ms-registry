"""
Access CA Integration Layer

Bridges ms-registry's RegisteredEntity data with django-ca for certificate issuance.
Implements the Integrated Model per ETSI TS 119 475 Annex D.1.

Flow:
1. Entity submits CSR to /certificates/issue/<entity_id>/
2. This module reads entity data from registry database
3. Builds certificate parameters (Subject DN, SAN, extensions)
4. Calls django-ca to sign the certificate
5. Stores result in both django-ca and EntityAccessCertificate

References:
- ETSI TS 119 411-8: Access Certificate Policy
- ETSI TS 119 475: WRP entitlement OIDs
- ETSI EN 319 412-1: organizationIdentifier format
"""

import hashlib
import logging
from datetime import timedelta
from urllib.parse import urlparse

from certificates.models import EntityAccessCertificate
from core.models import RegistrationStatus
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_ca.profiles import get_profile
from registry.models import RegisteredEntity

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# ETSI TS 119 475 Annex A — Entitlement OIDs
# ──────────────────────────────────────────────────────────────────────────────

ENTITLEMENT_OIDS = {
    "Service_Provider": "0.4.0.19475.1.1",
    "QEAA_Provider": "0.4.0.19475.1.2",
    "Non_Q_EAA_Provider": "0.4.0.19475.1.3",
    "PUB_EAA_Provider": "0.4.0.19475.1.4",
    "PID_Provider": "0.4.0.19475.1.5",
    "QCert_for_ESeal_Provider": "0.4.0.19475.1.6",
    "QCert_for_ESig_Provider": "0.4.0.19475.1.7",
    "rQSealCDs_Provider": "0.4.0.19475.1.8",
    "rQSigCDs_Provider": "0.4.0.19475.1.9",
    "ESig_ESeal_Creation_Provider": "0.4.0.19475.1.10",
}

# ETSI TS 119 411-8 §5.3 — Certificate Policy OIDs
POLICY_OIDS = {
    "NCP-n-eudiwrp": "0.4.0.194118.1.1",  # Natural person
    "NCP-l-eudiwrp": "0.4.0.194118.1.2",  # Legal person
    "QCP-n-eudiwrp": "0.4.0.194118.1.3",  # Qualified, natural person
    "QCP-l-eudiwrp": "0.4.0.194118.1.4",  # Qualified, legal person
}

# Entitlements that require Qualified Certificate Policy (QCP-*)
# Per ETSI TS 119 475 and eIDAS Article 45a
QUALIFIED_ENTITLEMENTS = {
    "QEAA_Provider",  # Qualified EAA Provider
    "QCert_for_ESeal_Provider",
    "QCert_for_ESig_Provider",
}

# ETSI EN 319 412-5 — QcStatements OIDs
QC_COMPLIANCE_OID = "0.4.0.1862.1.1"  # id-etsi-qcs-QcCompliance
QC_TYPE_OID = "0.4.0.1862.1.6"  # id-etsi-qcs-QcType
QC_TYPE_ESIGN_OID = "0.4.0.1862.1.6.1"  # id-etsi-qct-esign (natural persons)
QC_TYPE_ESEAL_OID = "0.4.0.1862.1.6.2"  # id-etsi-qct-eseal (legal persons)

# ETSI EN 319 412-1 §5.1.4 — organizationIdentifier scheme prefixes
ORG_ID_PREFIXES = {
    "EUID": "EUID",
    "VAT_NUMBER": "VAT",
    "LEI": "LEI",
    "EORI": "EORI",
    "NATIONAL_BUSINESS_REG": "NTR",
    "NATIONAL_TAX_REG": "TAX",
    "SERIAL_NUMBER": "PAS",
    "OTHER": "OTH",
}

# X.500 OID constants (ETSI EN 319 412-1)
OID_COUNTRY_NAME = "2.5.4.6"
OID_ORGANIZATION_NAME = "2.5.4.10"
OID_COMMON_NAME = "2.5.4.3"
OID_GIVEN_NAME = "2.5.4.42"
OID_SURNAME = "2.5.4.4"
OID_SERIAL_NUMBER = "2.5.4.5"
OID_ORGANIZATION_IDENTIFIER = "2.5.4.97"  # ETSI EN 319 412-1 §5.1.4

# Readable attribute names (used in subject dicts and validation)
ATTR_COUNTRY = "C"
ATTR_ORGANIZATION = "O"
ATTR_COMMON_NAME = "CN"
ATTR_GIVEN_NAME = "GN"
ATTR_SURNAME = "SN"
ATTR_SERIAL_NUMBER = "serialNumber"
ATTR_ORGANIZATION_IDENTIFIER = "organizationIdentifier"


def format_org_identifier(
    identifier_value: str, identifier_type: str, country: str
) -> str:
    """
    Format organizationIdentifier per ETSI EN 319 412-1 §5.1.4.

    Example: VAT_NUMBER + SE + 123456 → "VATSE-123456"

    Per LEG-5.1.4-03 item 4: LEI (ISO 17442) is a global scheme; its country
    code shall be set to 'XG', not the entity's national country code.
    """
    prefix = ORG_ID_PREFIXES.get(identifier_type, "OTH")
    effective_country = "XG" if identifier_type == "LEI" else country
    # Strip formatting separators per ETSI EN 319 412-1 §5.1.4
    clean_value = identifier_value.replace("-", "").replace(" ", "")
    return f"{prefix}{effective_country}-{clean_value}"


class CertificateIssuanceError(Exception):
    """Raised when certificate issuance fails.

    Attributes:
        http_status: Suggested HTTP status code for the view layer.
    """

    def __init__(self, message: str, http_status: int = 500) -> None:
        super().__init__(message)
        self.http_status = http_status


def get_entity_for_issuance(entity_id: str) -> RegisteredEntity:
    """
    Fetch RegisteredEntity with all relations needed for certificate issuance.

    Raises:
        RegisteredEntity.DoesNotExist: Entity not found
        CertificateIssuanceError: Entity not eligible for certificate
    """
    entity = (
        RegisteredEntity.objects.select_related(
            "legal_entity__legal_person",
            "legal_entity__natural_person",
            "legal_entity__primary_identifier",
            "legal_entity__physical_address",
        )
        .prefetch_related("entitlements", "support_uris")
        .get(id=entity_id)
    )

    if entity.registration_status != RegistrationStatus.ACTIVE:
        raise CertificateIssuanceError(
            f"Entity registration status is '{entity.registration_status}', "
            f"not 'active'. Certificates can only be issued for active entities.",
            http_status=409,
        )

    # domain_uri and instance_uri are the entity's certificate SAN entries
    # (dNSName and uniformResourceIdentifier respectively) and both are
    # mandatory to issue an access certificate. Their presence also satisfies
    # ETSI TS 119 411-8 GEN-6.6.1-07 (SAN must contain at least one URI).
    # Refuse issuance if either is missing.
    missing = [
        name
        for name, value in (
            ("domain_uri", entity.domain_uri),
            ("instance_uri", entity.instance_uri),
        )
        if not value
    ]
    if missing:
        raise CertificateIssuanceError(
            "Entity is missing required certificate SAN field(s): "
            f"{', '.join(missing)}. Both domain_uri and instance_uri must be "
            "set before an access certificate can be issued.",
            http_status=400,
        )

    # GEN-6.6.1-05: organizationIdentifier is mandatory for legal persons.
    # Without a registry primary_identifier, build_subject_from_entity would
    # omit it and the issued certificate would be non-conformant.
    if (
        entity.legal_entity.entity_type == "legal_person"
        and entity.legal_entity.primary_identifier is None
    ):
        raise CertificateIssuanceError(
            "Legal person has no primary identifier; organizationIdentifier is "
            "mandatory for the access certificate (GEN-6.6.1-05).",
            http_status=400,
        )

    return entity


def build_subject_from_entity(entity: RegisteredEntity) -> dict:
    """
    Build X.509 Subject DN attributes from registry data.

    Legal person (ETSI EN 319 412-3):
        C, O (legal name), CN (trade name), organizationIdentifier

    Natural person (ETSI EN 319 412-2):
        C, GN (given name), SN (family name), CN (trade name), serialNumber
    """
    legal_entity = entity.legal_entity
    primary_id = legal_entity.primary_identifier
    address = legal_entity.physical_address

    # Determine country code
    country = (
        (primary_id.country_code if primary_id else None)
        or (address.country_code if address else None)
        or "XX"
    )

    subject = {ATTR_COUNTRY: country}

    if legal_entity.entity_type == "natural_person" and legal_entity.natural_person:
        # Natural person Subject DN
        np = legal_entity.natural_person
        subject[ATTR_GIVEN_NAME] = np.given_name
        subject[ATTR_SURNAME] = np.family_name
        subject[ATTR_COMMON_NAME] = (
            entity.trade_name or f"{np.given_name} {np.family_name}"
        )

        if primary_id:
            # serialNumber for natural persons
            subject[ATTR_SERIAL_NUMBER] = format_org_identifier(
                primary_id.identifier_value, primary_id.identifier_type, country
            )
    else:
        # Legal person Subject DN
        if legal_entity.legal_person:
            subject[ATTR_ORGANIZATION] = legal_entity.legal_person.legal_name
        subject[ATTR_COMMON_NAME] = entity.trade_name or legal_entity.display_name

        if primary_id:
            subject[ATTR_ORGANIZATION_IDENTIFIER] = format_org_identifier(
                primary_id.identifier_value, primary_id.identifier_type, country
            )

    return subject


# X.500 OID to short name mapping for CSR subject validation
X500_OID_MAP = {
    OID_COUNTRY_NAME: ATTR_COUNTRY,
    OID_ORGANIZATION_NAME: ATTR_ORGANIZATION,
    OID_COMMON_NAME: ATTR_COMMON_NAME,
    OID_GIVEN_NAME: ATTR_GIVEN_NAME,
    OID_SURNAME: ATTR_SURNAME,
    OID_SERIAL_NUMBER: ATTR_SERIAL_NUMBER,
    OID_ORGANIZATION_IDENTIFIER: ATTR_ORGANIZATION_IDENTIFIER,
}


def validate_csr_subject(
    csr: x509.CertificateSigningRequest, entity: RegisteredEntity
) -> list[str]:
    """
    Validate that the CSR subject matches registry data.

    Checks critical fields:
    - Country (C) must match
    - Organization (O) must match legal name (for legal persons)
    - organizationIdentifier must match primary identifier

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    expected = build_subject_from_entity(entity)

    # Parse CSR subject into a dict
    csr_subject = {}
    for attr in csr.subject:
        oid = attr.oid.dotted_string
        name = X500_OID_MAP.get(oid, oid)
        csr_subject[name] = attr.value

    # Validate Country
    if "C" in expected:
        csr_country = csr_subject.get(ATTR_COUNTRY, "").upper()
        expected_country = expected[ATTR_COUNTRY].upper()
        if csr_country != expected_country:
            errors.append(
                f"Country mismatch: CSR has '{csr_country}', "
                f"registry expects '{expected_country}'"
            )

    # Validate Organization (for legal persons)
    if ATTR_ORGANIZATION in expected:
        csr_org = csr_subject.get(ATTR_ORGANIZATION, "")
        expected_org = expected[ATTR_ORGANIZATION]
        if csr_org.lower() != expected_org.lower():
            errors.append(
                f"Organization mismatch: CSR has '{csr_org}', "
                f"registry expects '{expected_org}'"
            )

    # Validate organizationIdentifier (critical for entity identification)
    if ATTR_ORGANIZATION_IDENTIFIER in expected:
        csr_org_id = csr_subject.get(ATTR_ORGANIZATION_IDENTIFIER, "")
        expected_org_id = expected[ATTR_ORGANIZATION_IDENTIFIER]
        if csr_org_id.upper() != expected_org_id.upper():
            errors.append(
                f"organizationIdentifier mismatch: CSR has '{csr_org_id}', "
                f"registry expects '{expected_org_id}'"
            )

    # Validate serialNumber (for natural persons)
    if ATTR_SERIAL_NUMBER in expected:
        csr_serial = csr_subject.get(ATTR_SERIAL_NUMBER, "")
        expected_serial = expected[ATTR_SERIAL_NUMBER]
        if csr_serial.upper() != expected_serial.upper():
            errors.append(
                f"serialNumber mismatch: CSR has '{csr_serial}', "
                f"registry expects '{expected_serial}'"
            )

    return errors


def validate_csr_key_algorithm(
    csr: x509.CertificateSigningRequest,
) -> str | None:
    """
    Reject CSRs whose subject key is not EC on the P-256 curve.

    The EUDI Wallet / OpenID4VP profile pins ES256 (ECDSA over P-256) for
    request-object signing and key binding, so the access certificate's subject
    key must be EC P-256. The CA signs with ECDSA regardless of the subject key,
    so without this check an RSA CSR is silently signed into a non-conformant
    leaf. See ETSI TS 119 312 / ARF for the algorithm requirements.

    Returns an error string, or None if the key is acceptable.
    """
    public_key = csr.public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        algo = type(public_key).__name__.replace("PublicKey", "")
        return (
            f"Unsupported key algorithm: CSR uses {algo}, but access "
            f"certificates require EC P-256 (secp256r1) per the EUDI Wallet "
            f"ES256 profile."
        )
    curve = public_key.curve.name
    if curve != ec.SECP256R1.name:
        return (
            f"Unsupported EC curve: CSR uses '{curve}', but access "
            f"certificates require P-256 (secp256r1)."
        )
    return None


def _der_tlv(tag: int, content: bytes) -> bytes:
    """DER tag-length-value with correct short/long-form length encoding."""
    n = len(content)
    if n < 0x80:
        length = bytes([n])
    else:
        width = (n.bit_length() + 7) // 8
        length = bytes([0x80 | width]) + n.to_bytes(width, "big")
    return bytes([tag]) + length + content


def _der_utf8string(value: bytes) -> bytes:
    return _der_tlv(0x0C, value)


def _encode_oid(dotted: str) -> bytes:
    """DER-encode a dotted OID string as the OID body (without tag/length)."""
    parts = [int(p) for p in dotted.split(".")]
    first = parts[0] * 40 + parts[1]
    body = []
    for part in [first] + parts[2:]:
        enc = [part & 0x7F]
        part >>= 7
        while part:
            enc.insert(0, (part & 0x7F) | 0x80)
            part >>= 7
        body.extend(enc)
    return bytes(body)


def build_san_from_entity(entity: RegisteredEntity) -> list[x509.GeneralName]:
    """
    Build Subject Alternative Name entries from registry data.

    Per ETSI TS 119 411-8 GEN-6.6.1-07, SAN must contain at least one of:
    - URI: instance_uri (entity's own endpoint) / support_uris (helpdesk)
    - rfc822Name: contact email
    - otherName (id-at-telephoneNumber OID 2.5.4.20): contact phone

    domain_uri is carried as a dNSName (host only — no scheme/port/path).
    instance_uri is carried as a uniformResourceIdentifier, which preserves
    the port and therefore distinguishes instances co-hosted on one domain.

    Entitlement OIDs (ETSI TS 119 475) go in qcStatements, NOT in SAN.
    """
    san_entries: list[x509.GeneralName] = []

    # Domain/host as dNSName. A dNSName carries only the hostname, so parse it
    # out of domain_uri (which may be a full URL); the port/path are dropped
    # here on purpose and preserved by instance_uri below.
    if entity.domain_uri:
        host = urlparse(entity.domain_uri).hostname
        if host:
            san_entries.append(x509.DNSName(host))

    # Full per-instance endpoint as a uniformResourceIdentifier. This is the
    # entity's own service URL incl. port, and uniquely locates this instance
    # among others sharing the same domain. (Replaces registry_uri here, which
    # is the Registrar's national registry API URL, not the entity's endpoint.)
    if entity.instance_uri:
        san_entries.append(x509.UniformResourceIdentifier(entity.instance_uri))

    # Support/contact URIs
    for support_uri in entity.support_uris.all():
        san_entries.append(x509.UniformResourceIdentifier(support_uri.support_uri))

    # Contact email (rfc822Name)
    if entity.legal_entity.email:
        san_entries.append(x509.RFC822Name(entity.legal_entity.email))

    # Contact phone — otherName with id-at-telephoneNumber (OID 2.5.4.20)
    if entity.legal_entity.phone:
        phone_bytes = entity.legal_entity.phone.encode("utf-8")
        san_entries.append(
            x509.OtherName(
                x509.ObjectIdentifier("2.5.4.20"),
                _der_utf8string(phone_bytes),
            )
        )

    return san_entries


def requires_qualified_policy(entity: RegisteredEntity) -> bool:
    """
    Check if entity has entitlements requiring a Qualified Certificate Policy.

    QEAA providers and qualified certificate providers need QCP-* policies.
    """
    entity_entitlements = {e.entitlement_type for e in entity.entitlements.all()}
    return bool(entity_entitlements & QUALIFIED_ENTITLEMENTS)


def get_policy_oid(entity: RegisteredEntity) -> str:
    """
    Determine certificate policy OID based on entity type and entitlements.

    Qualified entitlements (QEAA, etc.):
        Natural person → QCP-n-eudiwrp
        Legal person → QCP-l-eudiwrp

    Non-qualified (Service Provider, PID Provider, etc.):
        Natural person → NCP-n-eudiwrp
        Legal person → NCP-l-eudiwrp
    """
    is_qualified = requires_qualified_policy(entity)
    is_natural = entity.legal_entity.entity_type == "natural_person"

    if is_qualified:
        return POLICY_OIDS["QCP-n-eudiwrp" if is_natural else "QCP-l-eudiwrp"]
    return POLICY_OIDS["NCP-n-eudiwrp" if is_natural else "NCP-l-eudiwrp"]


def build_certificate_policies_extension(
    policy_oid: str, cps_uri: str | None = None
) -> x509.Extension:
    """
    Build the Certificate Policies extension (ETSI TS 119 411-8 GEN-6.6.1-06).

    When a CPS URI is provided it is added as a policy qualifier. cryptography's
    PolicyInformation accepts a plain str qualifier and interprets it as a CPS
    URI, so no PolicyQualifierInfo wrapper is needed.
    """
    policy_qualifiers = [cps_uri] if cps_uri else None
    return x509.Extension(
        oid=x509.ExtensionOID.CERTIFICATE_POLICIES,
        critical=False,
        value=x509.CertificatePolicies(
            [
                x509.PolicyInformation(
                    x509.ObjectIdentifier(policy_oid), policy_qualifiers
                ),
            ]
        ),
    )


def build_qc_statements_value(
    entity: RegisteredEntity, is_qualified: bool
) -> bytes | None:
    """
    Build the DER value of the qcStatements extension (OID 1.3.6.1.5.5.7.1.3).

    qcStatements is a single ``SEQUENCE OF QCStatement`` carrying, in order:

    - ``QcCompliance`` + ``QcType`` (qualified certificates only,
      ETSI EN 319 412-5).
    - One entitlement statement per registered entitlement
      (ETSI TS 119 475), each encoded as ``SEQUENCE { statementId OID }``.
      Entitlements are encoded for every access-cert type, including
      non-qualified ones (e.g. Service_Provider).

    Returns the DER-encoded extension value, or ``None`` when the entity has
    neither qualified statements nor any recognised entitlement (so the
    extension is omitted entirely).
    """
    qc_der = b""

    # QcCompliance + QcType for qualified certificates (EN 319 412-5).
    if is_qualified:
        qc_compliance_oid = _der_tlv(0x06, _encode_oid(QC_COMPLIANCE_OID))
        qc_der += _der_tlv(0x30, qc_compliance_oid)

        # QcType: eSign (natural persons) / eSeal (legal persons).
        # SEQUENCE { OID id-etsi-qcs-QcType, SEQUENCE { OID <qct> } }
        is_natural = entity.legal_entity.entity_type == "natural_person"
        qct_oid = QC_TYPE_ESIGN_OID if is_natural else QC_TYPE_ESEAL_OID
        qc_type_oid = _der_tlv(0x06, _encode_oid(QC_TYPE_OID))
        qc_type_qct = _der_tlv(0x06, _encode_oid(qct_oid))
        qc_type_value = _der_tlv(0x30, qc_type_qct)  # SEQUENCE { qct OID }
        qc_der += _der_tlv(0x30, qc_type_oid + qc_type_value)

    # Entitlement OIDs (TS 119 475) — one QCStatement per entitlement. Uses the
    # same entitlement set as requires_qualified_policy() so the qualified flag
    # and the encoded entitlements stay consistent.
    for entitlement in entity.entitlements.all():
        oid_str = ENTITLEMENT_OIDS.get(entitlement.entitlement_type)
        if oid_str:
            qc_der += _der_tlv(0x30, _der_tlv(0x06, _encode_oid(oid_str)))

    return _der_tlv(0x30, qc_der) if qc_der else None  # outer SEQUENCE


def issue_access_certificate(
    entity_id: str,
    csr: x509.CertificateSigningRequest,
) -> EntityAccessCertificate:
    """
    Issue an access certificate for a registered entity.

    Args:
        entity_id: UUID of the RegisteredEntity
        csr: Parsed CertificateSigningRequest (already validated by the serializer)

    Returns:
        EntityAccessCertificate record with issued certificate

    Raises:
        RegisteredEntity.DoesNotExist: Entity not found
        CertificateIssuanceError: Issuance failed
    """
    # Import here to avoid circular imports and allow graceful failure if
    # django-ca is not installed
    try:
        from django_ca.models import Certificate, CertificateAuthority
    except ImportError:
        raise CertificateIssuanceError(
            "django-ca is not installed. Run: pip install django-ca"
        )

    # 1. Get entity and validate eligibility
    entity = get_entity_for_issuance(entity_id)

    # 2. Get the CA
    # Priority: CA_DEFAULT_CA serial (env-driven) → name → first usable
    ca = None
    ca_serial = getattr(settings, "CA_DEFAULT_CA", None)
    if ca_serial:
        ca = CertificateAuthority.objects.filter(serial=ca_serial).first()
    if not ca:
        ca = CertificateAuthority.objects.filter(name="SE Access CA").first()
    if not ca:
        ca = CertificateAuthority.objects.usable().first()
    if not ca:
        raise CertificateIssuanceError(
            "No usable CA found. Create one with: make init-ca"
        )

    # 3. Validate CSR subject matches registry data
    validation_errors = validate_csr_subject(csr, entity)
    if validation_errors:
        raise CertificateIssuanceError(
            f"CSR subject validation failed: {'; '.join(validation_errors)}",
            http_status=400,
        )

    # 4. Validate CSR key algorithm (EUDI Wallet ES256 profile → EC P-256)
    key_error = validate_csr_key_algorithm(csr)
    if key_error:
        raise CertificateIssuanceError(key_error, http_status=400)

    # 5. Build certificate extensions from registry data
    # Note: Subject DN comes from the CSR - we only add authoritative extensions
    san_entries = build_san_from_entity(entity)
    policy_oid = get_policy_oid(entity)
    is_qualified = requires_qualified_policy(entity)

    # qcStatements (ETSI EN 319 412-5 + ETSI TS 119 475): qualified statements
    # for qualified certs plus one entitlement statement per registered
    # entitlement. See build_qc_statements_value() for the encoding.
    QC_STATEMENTS_OID = x509.ObjectIdentifier("1.3.6.1.5.5.7.1.3")
    qc_value = build_qc_statements_value(entity, is_qualified)

    # 6. Build extensions as cryptography x509.Extension objects.
    # BasicConstraints and KeyUsage are handled by the eudiwrp profile — only
    # pass extensions that carry per-entity data.

    # Certificate Policies with optional CPS URI (ETSI TS 119 411-8 GEN-6.6.1-06)
    cps_uri = getattr(settings, "CA_CPS_URI", None)

    extensions = [
        x509.Extension(
            oid=x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
            critical=False,
            value=x509.SubjectAlternativeName(san_entries),
        ),
        build_certificate_policies_extension(policy_oid, cps_uri),
    ]

    # Add qcStatements whenever there is content: entitlement OIDs (any
    # access-cert type) and/or QcCompliance+QcType (qualified certificates).
    if qc_value:
        extensions.append(
            x509.Extension(
                oid=QC_STATEMENTS_OID,
                critical=False,
                value=x509.UnrecognizedExtension(QC_STATEMENTS_OID, qc_value),
            )
        )

    # 7. Issue certificate via django-ca
    # Subject DN is taken from the CSR, CA only adds extensions
    not_after = timezone.now() + timedelta(
        days=getattr(settings, "CA_DEFAULT_EXPIRES", 365)
    )

    # 7. Sign and persist atomically — both writes go to the same DB so one
    # transaction covers both. A failed local write rolls back the django-ca
    # Certificate too, preventing orphan CA records.
    with transaction.atomic():
        try:
            key_backend_options = ca.key_backend.get_use_private_key_options(ca, {})
            profile_name = getattr(settings, "CA_DEFAULT_PROFILE", "eudiwrp")
            cert = Certificate.objects.create_cert(
                ca=ca,
                key_backend_options=key_backend_options,
                csr=csr,
                subject=csr.subject,
                not_after=not_after,
                # WP4 access certificate policy mandates ecdsa-with-SHA384.
                # The CA's stored default may differ (e.g. SHA-512), so pin it
                # per issuance.
                algorithm=hashes.SHA384(),
                extensions=extensions,
                profile=get_profile(profile_name),
                allow_unrecognized_extensions=True,
            )
        except Exception as e:
            raise CertificateIssuanceError(f"Certificate signing failed: {e}")

        cert_obj = cert.pub.loaded
        cert_pem = cert.pub.pem
        cert_der = cert_obj.public_bytes(serialization.Encoding.DER)
        fingerprint = hashlib.sha256(cert_der).hexdigest()

        # Mark any existing current certificates as non-current
        EntityAccessCertificate.objects.filter(
            registered_entity=entity, is_current=True
        ).update(is_current=False)

        access_cert = EntityAccessCertificate.objects.create(
            registered_entity=entity,
            django_ca_certificate=cert,
            certificate_serial=format(cert_obj.serial_number, "x").upper(),
            certificate_fingerprint_sha256=fingerprint,
            issuer_dn=cert_obj.issuer.rfc4514_string(),
            subject_dn=cert_obj.subject.rfc4514_string(),
            not_before=cert_obj.not_valid_before_utc,
            not_after=cert_obj.not_valid_after_utc,
            is_current=True,
            certificate_pem=cert_pem,
        )

    return access_cert


def revoke_entity_certificates(
    entity: RegisteredEntity,
    reason: str = "cessationOfOperation",
) -> int:
    """
    Revoke all active certificates for an entity.

    Called when entity status changes to SUSPENDED or REVOKED.

    Args:
        entity: RegisteredEntity whose certificates should be revoked
        reason: Revocation reason (RFC 5280 ReasonCode)

    Returns:
        Number of certificates revoked
    """
    try:
        from django_ca.models import Certificate  # noqa: F401
    except ImportError:
        # django-ca not installed, just update local records
        return EntityAccessCertificate.objects.filter(
            registered_entity=entity,
            is_current=True,
            revoked_at__isnull=True,
        ).update(
            revoked_at=timezone.now(),
            revocation_reason=reason,
        )

    count = 0
    now = timezone.now()

    # Get all current, non-revoked certificates for this entity
    certs = EntityAccessCertificate.objects.filter(
        registered_entity=entity,
        is_current=True,
        revoked_at__isnull=True,
    ).select_related("django_ca_certificate")

    for access_cert in certs:
        if access_cert.django_ca_certificate:
            try:
                access_cert.django_ca_certificate.revoke(reason=reason)
            except Exception as exc:
                # Do NOT mark the local record as revoked: keeping local state
                # in sync with django-ca (OCSP/CRL) is more important than a
                # partial update. The operator must investigate and retry.
                logger.error(
                    "Failed to revoke certificate %s in django-ca for entity %s: %s. "
                    "Local record left unchanged to avoid OCSP/CRL desync.",
                    access_cert.certificate_serial,
                    entity.id,
                    exc,
                    exc_info=True,
                )
                continue

        access_cert.revoked_at = now
        access_cert.revocation_reason = reason
        access_cert.save(update_fields=["revoked_at", "revocation_reason"])
        count += 1

    return count
