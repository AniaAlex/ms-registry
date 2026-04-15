"""
Tests for core/signing.py and the generate_registry_signing_key management command.
"""

import base64
from unittest.mock import patch

import jwt
import pytest
from core import signing as signing_module
from core.signing import public_key_as_jwk, sign_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cached_key():
    """Reset the module-level key cache between tests."""
    original = signing_module._private_key
    yield
    signing_module._private_key = original


@pytest.fixture
def ec_private_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def ec_private_key_pem(ec_private_key):
    return ec_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


# ---------------------------------------------------------------------------
# sign_jwt
# ---------------------------------------------------------------------------


def test_sign_jwt_returns_valid_es256_token(ec_private_key_pem, ec_private_key):
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": ec_private_key_pem}):
        signing_module._private_key = None
        token = sign_jwt({"iss": "test", "sub": "123", "iat": 0, "exp": 9999999999})

    decoded = jwt.decode(token, ec_private_key.public_key(), algorithms=["ES256"])
    assert decoded["sub"] == "123"
    assert decoded["iss"] == "test"


def test_sign_jwt_sets_kid_header(ec_private_key_pem, ec_private_key):
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": ec_private_key_pem}):
        signing_module._private_key = None
        token = sign_jwt({"iat": 0, "exp": 9999999999})

    header = jwt.get_unverified_header(token)
    assert header["kid"] == "ms-registry-signing-key-v1"
    assert header["alg"] == "ES256"


def test_sign_jwt_raises_when_key_not_set():
    with patch.dict("os.environ", {}, clear=True):
        signing_module._private_key = None
        with pytest.raises(RuntimeError, match="REGISTRY_SIGNING_KEY_PEM is not set"):
            sign_jwt({"iat": 0, "exp": 9999999999})


def test_sign_jwt_raises_for_non_ec_key():
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": rsa_pem}):
        signing_module._private_key = None
        with pytest.raises(RuntimeError, match="must be an EC private key"):
            sign_jwt({"iat": 0, "exp": 9999999999})


def test_sign_jwt_caches_private_key(ec_private_key_pem):
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": ec_private_key_pem}):
        signing_module._private_key = None
        sign_jwt({"iat": 0, "exp": 9999999999})
        cached = signing_module._private_key
        sign_jwt({"iat": 0, "exp": 9999999999})
        assert signing_module._private_key is cached


# ---------------------------------------------------------------------------
# public_key_as_jwk
# ---------------------------------------------------------------------------


def test_public_key_as_jwk_returns_correct_structure(ec_private_key_pem):
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": ec_private_key_pem}):
        signing_module._private_key = None
        jwk = public_key_as_jwk()

    assert jwk["kty"] == "EC"
    assert jwk["crv"] == "P-256"
    assert jwk["alg"] == "ES256"
    assert jwk["use"] == "sig"
    assert jwk["kid"] == "ms-registry-signing-key-v1"
    assert "x" in jwk
    assert "y" in jwk


def test_public_key_as_jwk_coordinates_match_key(ec_private_key_pem, ec_private_key):
    with patch.dict("os.environ", {"REGISTRY_SIGNING_KEY_PEM": ec_private_key_pem}):
        signing_module._private_key = None
        jwk = public_key_as_jwk()

    pub_numbers = ec_private_key.public_key().public_numbers()

    def b64url_decode(s):
        padding = "=" * (-len(s) % 4)
        return int.from_bytes(base64.urlsafe_b64decode(s + padding), byteorder="big")

    assert b64url_decode(jwk["x"]) == pub_numbers.x
    assert b64url_decode(jwk["y"]) == pub_numbers.y
