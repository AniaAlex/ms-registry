"""
Generate a test certificate for Skatteverket as a PID Provider.
This creates an ECDSA P-256 certificate suitable for signing PIDs.

Usage:
    python manage.py generate_pid_cert
"""

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a test certificate for Skatteverket PID Provider"

    def handle(self, *args, **options):
        # Generate ECDSA key pair (P-256, recommended for EUDI Wallet per ARF)
        private_key = ec.generate_private_key(ec.SECP256R1())

        # Certificate subject for Skatteverket as PID Provider
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "SE"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Stockholm"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Solna"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Skatteverket"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "PID Provider"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Skatteverket PID Issuer"),
                x509.NameAttribute(NameOID.SERIAL_NUMBER, "SE202100544801"),
            ]
        )

        # Build self-signed certificate (3-year validity for testing)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365 * 3))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=True,  # non-repudiation for signing
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
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Output PEM formats
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        # Print results
        self.stdout.write(self.style.SUCCESS("\n=== CERTIFICATE PEM ==="))
        self.stdout.write(cert_pem)

        self.stdout.write(
            self.style.WARNING("\n=== PRIVATE KEY PEM (keep secure!) ===")
        )
        self.stdout.write(key_pem)

        self.stdout.write(self.style.SUCCESS("\n=== Certificate Details ==="))
        self.stdout.write(f"Subject DN: {cert.subject.rfc4514_string()}")
        self.stdout.write(f"Issuer DN:  {cert.issuer.rfc4514_string()}")
        self.stdout.write(f"Serial Number: {cert.serial_number}")
        self.stdout.write(f"Not Valid Before: {cert.not_valid_before_utc}")
        self.stdout.write(f"Not Valid After:  {cert.not_valid_after_utc}")
        self.stdout.write(f"Algorithm: ECDSA with SHA-256 (P-256/secp256r1)")

        # Calculate fingerprint
        fingerprint = cert.fingerprint(hashes.SHA256()).hex().upper()
        formatted_fp = ":".join(
            fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2)
        )
        self.stdout.write(f"SHA-256 Fingerprint: {formatted_fp}")

        self.stdout.write(self.style.SUCCESS("\n✓ Certificate generated successfully!"))
        self.stdout.write(
            "Copy the CERTIFICATE PEM to the 'certificate_pem' field in the admin."
        )
