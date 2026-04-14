"""
Tests for the generate_registry_signing_key management command.
"""

from io import StringIO

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management import call_command


def test_generate_key_outputs_private_key():
    out = StringIO()
    call_command("generate_registry_signing_key", stdout=out)
    assert "BEGIN PRIVATE KEY" in out.getvalue()
    assert "END PRIVATE KEY" in out.getvalue()


def test_generate_key_outputs_public_key():
    out = StringIO()
    call_command("generate_registry_signing_key", stdout=out)
    assert "BEGIN PUBLIC KEY" in out.getvalue()
    assert "END PUBLIC KEY" in out.getvalue()


def test_generate_key_outputs_env_var_instruction():
    out = StringIO()
    call_command("generate_registry_signing_key", stdout=out)
    assert "REGISTRY_SIGNING_KEY_PEM" in out.getvalue()


def test_generate_key_produces_valid_ec_p256_key():
    out = StringIO()
    call_command("generate_registry_signing_key", stdout=out)

    for line in out.getvalue().splitlines():
        if line.startswith("REGISTRY_SIGNING_KEY_PEM="):
            pem = line.split("=", 1)[1].strip('"').replace("\\n", "\n")
            key = serialization.load_pem_private_key(pem.encode(), password=None)
            assert isinstance(key, ec.EllipticCurvePrivateKey)
            assert key.key_size == 256
            return

    pytest.fail("REGISTRY_SIGNING_KEY_PEM line not found in output")


def test_generate_key_produces_unique_keys_each_run():
    out1, out2 = StringIO(), StringIO()
    call_command("generate_registry_signing_key", stdout=out1)
    call_command("generate_registry_signing_key", stdout=out2)
    assert out1.getvalue() != out2.getvalue()
