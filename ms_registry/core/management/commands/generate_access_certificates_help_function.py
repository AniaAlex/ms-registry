"""
Development helper: generate an X.509 access certificate from a cnf JWT.

Decodes the signed cnf token returned by GET /certificates/cnf/<entity_id>/,
maps the registry data to X.509 Subject DN and extensions, and produces a
self-signed certificate together with a fresh EC P-256 key pair.

This is a LOCAL DEVELOPMENT TOOL only — not for production use.
In production the certificate is signed by the registered Access CA.

Usage:
    python manage.py generate_access_certificates_help_function \\
        --token <jwt_string>

Example token (from /certificates/cnf/<entity_id>/):
    eyJhbGciOiJFUzI1NiIsImtpZCI6Im1zLXJlZ2lzdHJ5LXNpZ25pbmcta2V5LXYxIiwidHlwIjoiSldUIn0...
"""

from datetime import datetime, timedelta, timezone

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from django.core.management.base import BaseCommand, CommandError

# ---------------------------------------------------------------------------
# OID mappings (ETSI TS 119 411-8 / TS 119 475)
# ---------------------------------------------------------------------------

# Certificate policy OIDs by entity role
# NCP-l-eudiwrp for legal persons, NCP-n-eudiwrp for natural persons
_POLICY_OID_BY_ROLE = {
    "relying_party": "0.4.0.194118.1.2",  # NCP-l-eudiwrp
    "pid_provider": "0.4.0.194118.1.2",  # NCP-l-eudiwrp
    "attestation_provider": "0.4.0.194118.1.2",  # NCP-l-eudiwrp
}

# Entitlement OIDs (ETSI TS 119 475)
_ENTITLEMENT_OID = {
    "Service_Provider": "0.4.0.19475.1.1",
    "QEAA_Provider": "0.4.0.19475.1.2",
    "Non_Q_EAA_Provider": "0.4.0.19475.1.3",
    "PUB_EAA_Provider": "0.4.0.19475.1.4",
    "PID_Provider": "0.4.0.19475.1.5",
}

# organizationIdentifier scheme prefixes (ETSI EN 319 412-1)
_ORG_ID_PREFIX = {
    "EUID": "EUID",
    "VAT_NUMBER": "VAT",
    "LEI": "LEI",
    "EORI": "EORI",
    "NATIONAL_BUSINESS_REG": "NTR",
    "NATIONAL_TAX_REG": "TAX",
    "SERIAL_NUMBER": "PAS",
    "OTHER": "OTH",
}


def _format_org_identifier(
    identifier_value: str,
    identifier_type: str,
    country: str,
) -> str:
    """
    Format the organizationIdentifier per ETSI EN 319 412-1.
    Example: VAT_NUMBER + SE + 123456 → "VATSE-123456"
    """
    prefix = _ORG_ID_PREFIX.get(identifier_type, "OTH")
    return f"{prefix}{country}-{identifier_value}"


def generate_certificate_from_cnf(cnf: dict) -> tuple[str, str]:
    """
    Generate a self-signed X.509 access certificate from decoded cnf data.

    Returns (certificate_pem, private_key_pem).
    """
    name = cnf.get("name", "Unknown")
    country = cnf.get("country") or "XX"
    org_identifier = cnf.get("org_identifier")
    org_identifier_type = cnf.get("org_identifier_type", "OTHER")
    role = cnf.get("role", "relying_party")
    entitlements = cnf.get("entitlements", [])

    # Generate entity key pair (EC P-256, per ARF recommendation)
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Build Subject DN
    name_attributes = [
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, name),
        x509.NameAttribute(NameOID.COMMON_NAME, name),
    ]
    if org_identifier:
        formatted = _format_org_identifier(org_identifier, org_identifier_type, country)
        name_attributes.append(
            x509.NameAttribute(NameOID.ORGANIZATION_IDENTIFIER, formatted)
        )

    subject = x509.Name(name_attributes)
    # Self-signed: entity is both subject and issuer (dev only)
    issuer = subject

    # Certificate policy
    policy_oid_str = _POLICY_OID_BY_ROLE.get(role, "0.4.0.194118.1.2")
    policy_oid = x509.ObjectIdentifier(policy_oid_str)

    # Build certificate
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
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
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.CertificatePolicies(
                [x509.PolicyInformation(policy_oid, policy_qualifiers=None)]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
    )

    # Add entitlement OIDs as SubjectAlternativeName RegisteredID entries
    san_entries = []
    for entitlement in entitlements:
        oid_str = _ENTITLEMENT_OID.get(entitlement)
        if oid_str:
            san_entries.append(x509.RegisteredID(x509.ObjectIdentifier(oid_str)))
    if san_entries:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )

    cert = builder.sign(private_key, hashes.SHA256())

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return cert_pem, key_pem


class Command(BaseCommand):
    help = (
        "DEV TOOL: Generate a self-signed X.509 access certificate from a cnf JWT. "
        "Not for production use."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--token",
            required=True,
            help="Signed cnf JWT returned by GET /certificates/cnf/<entity_id>/",
        )

    def handle(self, *args, **options):
        token = options["token"]

        try:
            cnf_payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["ES256"],
            )
        except jwt.DecodeError as e:
            raise CommandError(f"Failed to decode token: {e}")

        cnf = cnf_payload.get("cnf")
        if not cnf:
            raise CommandError("Token does not contain a 'cnf' claim.")

        self.stdout.write("\n=== cnf data ===")
        for key, value in cnf.items():
            self.stdout.write(f"  {key}: {value}")

        cert_pem, key_pem = generate_certificate_from_cnf(cnf)

        self.stdout.write(self.style.WARNING("\n=== PRIVATE KEY (keep secret) ==="))
        self.stdout.write(key_pem)

        self.stdout.write(self.style.SUCCESS("\n=== ACCESS CERTIFICATE ==="))
        self.stdout.write(cert_pem)

        self.stdout.write(self.style.SUCCESS("=== Certificate fields ==="))
        from cryptography import x509 as cx509

        cert = cx509.load_pem_x509_certificate(cert_pem.encode())
        self.stdout.write(f"Subject DN : {cert.subject.rfc4514_string()}")
        self.stdout.write(f"Issuer DN  : {cert.issuer.rfc4514_string()}")
        self.stdout.write(f"Serial     : {cert.serial_number}")
        self.stdout.write(f"Not before : {cert.not_valid_before_utc}")
        self.stdout.write(f"Not after  : {cert.not_valid_after_utc}")
        fingerprint = cert.fingerprint(hashes.SHA256()).hex().upper()
        formatted_fp = ":".join(
            fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2)
        )
        self.stdout.write(f"SHA-256    : {formatted_fp}")
        self.stdout.write(
            self.style.WARNING(
                "\nNOTE: This is a self-signed dev certificate. "
                "In production the certificate is signed by the registered Access CA."
            )
        )
