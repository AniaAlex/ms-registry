"""
Registry signing key utilities.

Loads the ms-registry ECDSA P-256 private key from the REGISTRY_SIGNING_KEY_PEM
environment variable and provides helpers for:
  - Signing JWTs (ES256) — used for cnf responses, LoTE documents, and any
    other signed registry response
  - Exporting the public key as a JWK for /.well-known/jwks.json
"""

import base64
import os

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey

_private_key: EllipticCurvePrivateKey | None = None


class KeyNotConfiguredError(RuntimeError):
    """Raised when REGISTRY_SIGNING_KEY_PEM is not set in the environment."""


def load_private_key() -> EllipticCurvePrivateKey:
    """Load and cache the private key from the environment."""
    global _private_key
    if _private_key is not None:
        return _private_key

    pem = os.environ.get("REGISTRY_SIGNING_KEY_PEM", "")
    if not pem:
        raise KeyNotConfiguredError(
            "REGISTRY_SIGNING_KEY_PEM is not set. "
            "Run: python manage.py generate_registry_signing_key"
        )

    key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(key, EllipticCurvePrivateKey):
        raise RuntimeError("REGISTRY_SIGNING_KEY_PEM must be an EC private key")

    _private_key = key
    return _private_key


def sign_jwt(payload: dict) -> str:
    """
    Sign a payload as a JWT using ES256.

    The caller is responsible for setting standard claims
    ('iss', 'sub', 'iat', 'exp') and any domain-specific claims in the payload.
    """
    private_key = load_private_key()
    return jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": "ms-registry-signing-key-v1"},
    )


def public_key_as_jwk() -> dict:
    """
    Return the public key as a JWK dict for inclusion in the JWKS document.
    Coordinates are base64url-encoded per RFC 7517.
    """
    private_key = load_private_key()
    pub = private_key.public_key()
    pub_numbers = pub.public_numbers()
    key_size = (pub_numbers.curve.key_size + 7) // 8

    def _b64url(n: int) -> str:
        return (
            base64.urlsafe_b64encode(n.to_bytes(key_size, byteorder="big"))
            .rstrip(b"=")
            .decode()
        )

    return {
        "kty": "EC",
        "crv": "P-256",
        "use": "sig",
        "alg": "ES256",
        "kid": "ms-registry-signing-key-v1",
        "x": _b64url(pub_numbers.x),
        "y": _b64url(pub_numbers.y),
    }
