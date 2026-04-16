"""
Test helper: build X.509 certificates with overridable fields.

Used in tests to exercise specific validation failure paths.
"""

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# Certificate policy OIDs by entity type (ETSI TS 119 411-8 §5.3, GEN-6.6.1-03)
_POLICY_OID_BY_ENTITY_TYPE = {
    "natural_person": x509.ObjectIdentifier("0.4.0.194118.1.1"),  # NCP-n-eudiwrp
    "legal_person": x509.ObjectIdentifier("0.4.0.194118.1.2"),  # NCP-l-eudiwrp
}


def build_cert_with_overrides(
    entity,
    *,
    country: str | None = None,
    org_name: str | None = None,
    friendly_name: str | None = None,
    url: str | None = None,
    contact_email: str | None = None,
    not_valid_before: datetime | None = None,
    not_valid_after: datetime | None = None,
) -> str:
    """
    Build a self-signed certificate for `entity` with selective field overrides.
    All unspecified fields are derived from the entity's registry data.
    Returns the PEM string.
    """
    primary_id = entity.primary_identifier
    resolved_country = country or (
        (primary_id.country_code if primary_id else None)
        or (
            entity.legal_entity.physical_address.country_code
            if entity.legal_entity.physical_address
            else "XX"
        )
    )
    entity_type = entity.legal_entity.entity_type
    # O (legal person) or GN+SN (natural person) — not the trade name
    resolved_org = org_name or entity.legal_entity.display_name
    # CN: user-friendly / trade name (GEN-6.1.1-04)
    resolved_friendly_name = (
        friendly_name or entity.trade_name or entity.legal_entity.display_name
    )

    primary_support_uri = (
        entity.support_uris.filter(is_primary=True).first()
        or entity.support_uris.first()
    )
    resolved_url = url or (
        primary_support_uri.support_uri if primary_support_uri else None
    )
    resolved_email = contact_email or entity.legal_entity.email

    now = datetime.now(timezone.utc)
    resolved_not_before = not_valid_before or (now - timedelta(seconds=1))
    resolved_not_after = not_valid_after or (now + timedelta(days=365))

    private_key = ec.generate_private_key(ec.SECP256R1())

    # Subject DN structure depends on entity type:
    # Legal person  (ETSI EN 319 412-3): C, O, CN, organizationIdentifier
    # Natural person (ETSI EN 319 412-2): C, GN, SN, CN, serialNumber
    if entity_type == "natural_person":
        np = entity.legal_entity.natural_person
        name_attributes = [
            x509.NameAttribute(NameOID.COUNTRY_NAME, resolved_country),
            # GN and SN hold the official name; CN holds the friendly/display name
            x509.NameAttribute(NameOID.GIVEN_NAME, np.given_name if np else ""),
            x509.NameAttribute(NameOID.SURNAME, np.family_name if np else ""),
            x509.NameAttribute(NameOID.COMMON_NAME, resolved_friendly_name),
        ]
    else:
        name_attributes = [
            x509.NameAttribute(NameOID.COUNTRY_NAME, resolved_country),
            # O carries the legal name from the official record, not the trade name
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, resolved_org),
            x509.NameAttribute(NameOID.COMMON_NAME, resolved_friendly_name),
        ]
    subject = x509.Name(name_attributes)

    san_names = []
    if resolved_url:
        san_names.append(x509.UniformResourceIdentifier(resolved_url))
    if resolved_email:
        san_names.append(x509.RFC822Name(resolved_email))

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(resolved_not_before)
        .not_valid_after(resolved_not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.CertificatePolicies(
                # GEN-6.6.1-03: NCP-n for natural persons, NCP-l for legal persons
                [
                    x509.PolicyInformation(
                        _POLICY_OID_BY_ENTITY_TYPE.get(
                            entity_type,
                            _POLICY_OID_BY_ENTITY_TYPE["legal_person"],
                        ),
                        policy_qualifiers=None,
                    )
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
    )

    if san_names:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_names),
            critical=False,
        )

    cert = builder.sign(private_key, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM).decode()
