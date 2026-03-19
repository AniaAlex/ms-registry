"""
WRPRC Signing Backends

Provides different signing implementations:
- RegistrySigner: Uses the registry's main signing key (integrated mode)
- LocalSigner: For development (key in memory/file)
- KMSSigner: For production (AWS KMS)
- HSMSigner: For high-security (Hardware Security Module)

Configuration (settings.py):
    WRPRC_SIGNER_TYPE = 'registry'  # Use registry's key (integrated mode)
    WRPRC_SIGNER_TYPE = 'local'     # Separate key from file/env
    WRPRC_SIGNER_TYPE = 'kms'       # Separate key in AWS KMS
"""

import base64
import json
from abc import ABC, abstractmethod
from typing import Optional

import jwt
from django.conf import settings


class BaseSigner(ABC):
    """Abstract base class for WRPRC signers."""

    @abstractmethod
    def sign(self, payload: dict, headers: dict) -> str:
        """
        Sign a WRPRC payload and return the complete JWT.

        Args:
            payload: The JWT payload (claims)
            headers: The JWT headers (typ, alg, x5c, etc.)

        Returns:
            The signed JWT as a string
        """
        pass

    @abstractmethod
    def get_public_key_jwk(self) -> dict:
        """Get the public key in JWK format."""
        pass


class RegistrySigner(BaseSigner):
    """
    Uses the registry's main signing key for WRPRC issuance.

    Integrated mode: One key signs everything (API responses, WRPRCs, etc.)

    The key is configured via:
    - REGISTRY_SIGNING_KEY_PATH: Path to PEM-encoded private key
    - REGISTRY_SIGNING_KEY: Base64-encoded PEM (env var)
    """

    def __init__(self):
        """Initialize using registry's signing key."""
        self.private_key = self._load_registry_key()

    def _load_registry_key(self):
        """Load the registry's signing key."""
        import os

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        # Try settings path
        key_path = getattr(settings, "REGISTRY_SIGNING_KEY_PATH", None)
        if key_path:
            with open(key_path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )

        # Try environment variable (base64-encoded PEM)
        key_b64 = os.environ.get("REGISTRY_SIGNING_KEY")
        if key_b64:
            key_pem = base64.b64decode(key_b64)
            return serialization.load_pem_private_key(
                key_pem, password=None, backend=default_backend()
            )

        raise ValueError(
            "No registry signing key configured. Set REGISTRY_SIGNING_KEY_PATH "
            "in settings or REGISTRY_SIGNING_KEY environment variable."
        )

    def sign(self, payload: dict, headers: dict) -> str:
        """Sign the payload with the registry's private key."""
        algorithm = headers.get("alg", "ES256")

        return jwt.encode(
            payload, self.private_key, algorithm=algorithm, headers=headers
        )

    def get_public_key_jwk(self) -> dict:
        """Get the public key in JWK format."""
        public_key = self.private_key.public_key()
        public_numbers = public_key.public_numbers()

        return {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(public_numbers.x.to_bytes(32, "big"))
            .decode()
            .rstrip("="),
            "y": base64.urlsafe_b64encode(public_numbers.y.to_bytes(32, "big"))
            .decode()
            .rstrip("="),
        }


class LocalSigner(BaseSigner):
    """
    Local signing for development/testing.

    WARNING: Not for production use. Key is stored in file/env.
    """

    def __init__(self, private_key_path: Optional[str] = None):
        """
        Initialize with a private key.

        Args:
            private_key_path: Path to PEM-encoded private key file.
                            If None, uses WRPRC_PRIVATE_KEY_PATH from settings
                            or WRPRC_PRIVATE_KEY env var.
        """
        self.private_key = self._load_private_key(private_key_path)

    def _load_private_key(self, path: Optional[str]):
        """Load the private key from file or environment."""
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        # Try path argument
        if path:
            with open(path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )

        # Try settings
        key_path = getattr(settings, "WRPRC_PRIVATE_KEY_PATH", None)
        if key_path:
            with open(key_path, "rb") as f:
                return serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )

        # Try environment variable (base64-encoded PEM)
        import os

        key_b64 = os.environ.get("WRPRC_PRIVATE_KEY")
        if key_b64:
            key_pem = base64.b64decode(key_b64)
            return serialization.load_pem_private_key(
                key_pem, password=None, backend=default_backend()
            )

        raise ValueError(
            "No private key configured. Set WRPRC_PRIVATE_KEY_PATH in settings "
            "or WRPRC_PRIVATE_KEY environment variable."
        )

    def sign(self, payload: dict, headers: dict) -> str:
        """Sign the payload with the local private key."""
        algorithm = headers.get("alg", "ES256")

        return jwt.encode(
            payload, self.private_key, algorithm=algorithm, headers=headers
        )

    def get_public_key_jwk(self) -> dict:
        """Get the public key in JWK format."""
        public_key = self.private_key.public_key()

        # Get the public numbers
        public_numbers = public_key.public_numbers()

        # Convert to JWK
        return {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(public_numbers.x.to_bytes(32, "big"))
            .decode()
            .rstrip("="),
            "y": base64.urlsafe_b64encode(public_numbers.y.to_bytes(32, "big"))
            .decode()
            .rstrip("="),
        }


class KMSSigner(BaseSigner):
    """
    AWS KMS signing for production.

    The private key never leaves AWS KMS.
    """

    def __init__(self, key_id: str, region: Optional[str] = None):
        """
        Initialize with an AWS KMS key.

        Args:
            key_id: The KMS key ID or ARN
            region: AWS region (optional, uses default if not specified)
        """
        import boto3

        self.key_id = key_id
        self.kms = boto3.client("kms", region_name=region)
        self._public_key_cache = None

    def sign(self, payload: dict, headers: dict) -> str:
        """Sign using AWS KMS."""
        import hashlib

        # Build the JWT header and payload
        header_b64 = self._base64url_encode(json.dumps(headers))
        payload_b64 = self._base64url_encode(json.dumps(payload))

        # Create the signing input
        signing_input = f"{header_b64}.{payload_b64}"

        # Hash the signing input (KMS expects a digest for ECDSA)
        digest = hashlib.sha256(signing_input.encode()).digest()

        # Sign with KMS
        response = self.kms.sign(
            KeyId=self.key_id,
            Message=digest,
            MessageType="DIGEST",
            SigningAlgorithm="ECDSA_SHA_256",
        )

        # Convert DER signature to raw R||S format for JWT
        signature = self._der_to_raw_signature(response["Signature"])
        signature_b64 = self._base64url_encode_bytes(signature)

        return f"{signing_input}.{signature_b64}"

    def get_public_key_jwk(self) -> dict:
        """Get the public key from KMS in JWK format."""
        if self._public_key_cache:
            return self._public_key_cache

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import load_der_public_key

        response = self.kms.get_public_key(KeyId=self.key_id)

        public_key = load_der_public_key(
            response["PublicKey"], backend=default_backend()
        )

        public_numbers = public_key.public_numbers()

        self._public_key_cache = {
            "kty": "EC",
            "crv": "P-256",
            "x": self._base64url_encode_bytes(public_numbers.x.to_bytes(32, "big")),
            "y": self._base64url_encode_bytes(public_numbers.y.to_bytes(32, "big")),
        }

        return self._public_key_cache

    def _base64url_encode(self, data: str) -> str:
        """Base64url encode a string."""
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")

    def _base64url_encode_bytes(self, data: bytes) -> str:
        """Base64url encode bytes."""
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    def _der_to_raw_signature(self, der_sig: bytes) -> bytes:
        """Convert DER-encoded ECDSA signature to raw R||S format."""
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

        r, s = decode_dss_signature(der_sig)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")


class HSMSigner(BaseSigner):
    """
    HSM signing via PKCS#11.

    For high-security deployments with hardware security modules.
    """

    def __init__(self, library_path: str, token_label: str, key_label: str, pin: str):
        """
        Initialize PKCS#11 connection to HSM.

        Args:
            library_path: Path to PKCS#11 library
            token_label: HSM token label
            key_label: Label of the signing key
            pin: PIN for the token
        """
        try:
            import pkcs11
        except ImportError:
            raise ImportError("python-pkcs11 required for HSM signing")

        self.lib = pkcs11.lib(library_path)
        self.token = self.lib.get_token(token_label=token_label)
        self.key_label = key_label
        self.pin = pin

    def sign(self, payload: dict, headers: dict) -> str:
        """Sign using HSM via PKCS#11."""
        import pkcs11
        from pkcs11 import Mechanism

        # Build signing input
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(headers).encode()).decode().rstrip("=")
        )
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )

        signing_input = f"{header_b64}.{payload_b64}".encode()

        # Open session and sign
        with self.token.open(user_pin=self.pin) as session:
            private_key = session.get_key(
                label=self.key_label, object_class=pkcs11.ObjectClass.PRIVATE_KEY
            )

            signature = private_key.sign(
                signing_input, mechanism=Mechanism.ECDSA_SHA256
            )

        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def get_public_key_jwk(self) -> dict:
        """Get public key from HSM."""
        import pkcs11

        with self.token.open(user_pin=self.pin) as session:
            public_key = session.get_key(
                label=self.key_label, object_class=pkcs11.ObjectClass.PUBLIC_KEY
            )

            # Extract EC point
            ec_point = public_key[pkcs11.Attribute.EC_POINT]

            # Parse the EC point (skip the 0x04 prefix for uncompressed point)
            x = ec_point[1:33]
            y = ec_point[33:65]

            return {
                "kty": "EC",
                "crv": "P-256",
                "x": base64.urlsafe_b64encode(x).decode().rstrip("="),
                "y": base64.urlsafe_b64encode(y).decode().rstrip("="),
            }
