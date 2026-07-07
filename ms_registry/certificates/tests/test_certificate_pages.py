"""
Tests for the certificate HTML pages:
- GET/POST /certificates/issue/<entity_id>/view/  (IssueCertificatePageView)
- GET      /certificates/detail/<entity_id>/view/ (AccessCertificateDetailPageView)
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from certificates.models import EntityAccessCertificate
from core.models import RegistrationStatus
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.urls import reverse
from registry.tests.factories import (
    EntityEntitlementFactory,
    RegisteredEntityFactory,
)

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_entity(operator, **kwargs):
    """Create an entity operated by ``operator`` (active by default).

    Certificate pages are scoped to an entity's operators, so the authenticated
    participant must be an operator to reach the page logic.
    """
    kwargs.setdefault("registration_status", RegistrationStatus.ACTIVE)
    kwargs.setdefault("operators", [operator])
    return RegisteredEntityFactory(**kwargs)


def _issue_page_url(entity_id):
    return reverse("certificates:issue-page", args=[entity_id])


def _detail_page_url(entity_id):
    return reverse("certificates:detail-page", args=[entity_id])


def _make_csr_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .sign(key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode()


def _make_cert_record(entity, **kwargs):
    """Create an EntityAccessCertificate row with sensible defaults."""
    now = datetime.now(tz=timezone.utc)
    defaults = dict(
        registered_entity=entity,
        certificate_serial="AABBCC",
        not_before=now - timedelta(days=1),
        not_after=now + timedelta(days=364),
        is_current=True,
    )
    defaults.update(kwargs)
    return EntityAccessCertificate.objects.create(**defaults)


# ── issue HTML page (generate certificate from CSR) ─────────────────────────────


@pytest.mark.django_db
def test_issue_page_get_returns_200(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    response = authenticated_api_client.get(_issue_page_url(entity.id))
    assert response.status_code == 200
    assert b"Generate Access Certificate" in response.content


@pytest.mark.django_db
def test_issue_page_get_shows_entity_name(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    response = authenticated_api_client.get(_issue_page_url(entity.id))
    assert entity.display_name.encode() in response.content


@pytest.mark.django_db
def test_issue_page_get_404_for_unknown_entity(authenticated_api_client):
    response = authenticated_api_client.get(_issue_page_url(uuid.uuid4()))
    assert response.status_code == 404


@pytest.mark.django_db
def test_issue_page_post_success_shows_cert_details(authenticated_api_client):
    # The page reuses the JSON issue endpoint's issuance path; mock the CA
    # signing (covered by test_issue / test_ca_integration) and assert the
    # page renders the issued certificate.
    entity = _make_entity(authenticated_api_client.participant)
    EntityEntitlementFactory(registered_entity=entity)
    now = datetime.now(timezone.utc)
    cert_record = EntityAccessCertificate(
        registered_entity=entity,
        certificate_serial="AABBCCDD",
        certificate_fingerprint_sha256="a" * 64,
        issuer_dn="CN=SE Access Certificate Authority",
        subject_dn="CN=Test Entity",
        not_before=now,
        not_after=now + timedelta(days=365),
        certificate_pem=(
            "-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
        ),
    )
    with patch(
        "certificates.ca_integration.issue_access_certificate",
        return_value=cert_record,
    ):
        response = authenticated_api_client.post(
            _issue_page_url(entity.id),
            {"csr_pem": _make_csr_pem()},
        )
    assert response.status_code == 201
    assert b"Certificate Issued" in response.content
    assert b"AABBCCDD" in response.content


@pytest.mark.django_db
def test_issue_page_post_shows_validation_errors(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    EntityEntitlementFactory(registered_entity=entity)
    response = authenticated_api_client.post(
        _issue_page_url(entity.id),
        {"csr_pem": "garbage"},
    )
    assert response.status_code == 400
    assert b"Validation Errors" in response.content


@pytest.mark.django_db
def test_issue_page_post_409_for_pending_entity(authenticated_api_client):
    entity = _make_entity(
        authenticated_api_client.participant,
        registration_status=RegistrationStatus.PENDING,
    )
    response = authenticated_api_client.post(
        _issue_page_url(entity.id),
        {"csr_pem": _make_csr_pem()},
    )
    assert response.status_code == 409


# ── Certificate detail page ────────────────────────────────────────────────────


def _self_signed_pem() -> str:
    """A minimal self-signed EC cert with EKU, for exercising the full decode."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Sometradename")])
    now = datetime.now(tz=timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(0x1234ABCD)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=364))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA384())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.mark.django_db
def test_detail_page_returns_200_for_valid_cert(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    _make_cert_record(entity)
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"AABBCC" in response.content


@pytest.mark.django_db
def test_detail_page_decodes_full_certificate(authenticated_api_client):
    # When a PEM is stored, the page decodes and shows all fields/extensions.
    entity = _make_entity(authenticated_api_client.participant)
    _make_cert_record(entity, certificate_pem=_self_signed_pem())
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    body = response.content
    assert response.status_code == 200
    assert b"Extensions" in body
    assert b"Public Key" in body
    assert b"Basic Constraints" in body
    assert b"TLS Web Client Authentication" in body
    assert b"Elliptic Curve (EC)" in body


@pytest.mark.django_db
def test_detail_page_returns_404_for_unknown_entity(authenticated_api_client):
    response = authenticated_api_client.get(_detail_page_url(uuid.uuid4()))
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_page_shows_no_cert_message_when_none_stored(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content


@pytest.mark.django_db
def test_detail_page_excludes_not_yet_valid_cert(authenticated_api_client):
    """
    A certificate whose not_before is in the future must not be shown —
    the query filters not_before__lte=now in addition to not_after__gt=now.
    """
    entity = _make_entity(authenticated_api_client.participant)
    future = datetime.now(tz=timezone.utc) + timedelta(days=1)
    _make_cert_record(entity, not_before=future)
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content


@pytest.mark.django_db
def test_detail_page_excludes_expired_cert(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    _make_cert_record(
        entity,
        not_before=past - timedelta(days=365),
        not_after=past,
    )
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content


@pytest.mark.django_db
def test_detail_page_excludes_revoked_cert(authenticated_api_client):
    entity = _make_entity(authenticated_api_client.participant)
    _make_cert_record(
        entity,
        revoked_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
    )
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content
