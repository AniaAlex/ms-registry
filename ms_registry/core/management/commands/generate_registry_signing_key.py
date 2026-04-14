"""
Generate the ms-registry ECDSA P-256 signing key pair.

Run once per deployment to create the key. Store the private key in
REGISTRY_SIGNING_KEY_PEM (single-line escaped) and never commit it.

Usage:
    python manage.py generate_registry_signing_key
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate the ms-registry ECDSA P-256 signing key pair"

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )

        self.stdout.write(self.style.WARNING("\n=== PRIVATE KEY (keep secret) ==="))
        self.stdout.write(private_pem)

        self.stdout.write(self.style.SUCCESS("\n=== PUBLIC KEY ==="))
        self.stdout.write(public_pem)

        escaped = private_pem.replace("\n", "\\n")
        self.stdout.write(self.style.SUCCESS("\n=== Set this in your environment ==="))
        self.stdout.write(f'REGISTRY_SIGNING_KEY_PEM="{escaped}"')
        self.stdout.write(
            "\nAdd REGISTRY_SIGNING_KEY_PEM to your .env or secrets manager."
        )
