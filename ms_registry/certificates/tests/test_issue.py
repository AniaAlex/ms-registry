"""
Tests for POST /certificates/issue/<entity_id>/  (IssueCertificateView).

issue_access_certificate is mocked for all endpoint tests — no real CA needed.
Auto-revocation tests use transaction=True so transaction.on_commit() fires.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from certificates.ca_integration import CertificateIssuanceError
from certificates.models import EntityAccessCertificate
from core.models import RegistrationStatus
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.urls import reverse
from django.utils import timezone
from registry.tests.factories import EntityEntitlementFactory, RegisteredEntityFactory
from rest_framework import status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _issue_url(entity_id):
    return reverse("certificates:issue", args=[entity_id])


def _make_active_entity(**kwargs):
    return RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE, **kwargs
    )


def _make_csr_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .sign(key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode()


def _make_cert_record(entity) -> EntityAccessCertificate:
    now = timezone.now()
    return EntityAccessCertificate.objects.create(
        registered_entity=entity,
        certificate_serial="AABBCCDD",
        certificate_fingerprint_sha256="a" * 64,
        issuer_dn="CN=Test CA",
        subject_dn="CN=Test Entity",
        not_before=now,
        not_after=now + timedelta(days=365),
        is_current=True,
        certificate_pem=(
            "-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
        ),
    )


def _post_issue(authenticated_api_client, entity_id, csr_pem, **extra):
    return authenticated_api_client.post(
        _issue_url(entity_id),
        {"csr_pem": csr_pem},
        format="json",
        **extra,
    )


def _patch_issue(return_value=None, side_effect=None):
    kwargs = {}
    if return_value is not None:
        kwargs["return_value"] = return_value
    if side_effect is not None:
        kwargs["side_effect"] = side_effect
    return patch("certificates.ca_integration.issue_access_certificate", **kwargs)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_issue_returns_201_for_valid_csr(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert_record = _make_cert_record(entity)

    with _patch_issue(return_value=cert_record):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_issue_response_contains_expected_fields(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert_record = _make_cert_record(entity)

    with _patch_issue(return_value=cert_record):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    data = response.data
    for field in (
        "id",
        "certificate_pem",
        "certificate_serial",
        "certificate_fingerprint_sha256",
        "subject_dn",
        "issuer_dn",
        "not_before",
        "not_after",
    ):
        assert field in data, f"missing field: {field}"


@pytest.mark.django_db
def test_issue_response_values_match_cert_record(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert_record = _make_cert_record(entity)

    with _patch_issue(return_value=cert_record):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    data = response.data
    assert data["id"] == str(cert_record.id)
    assert data["certificate_serial"] == cert_record.certificate_serial
    assert (
        data["certificate_fingerprint_sha256"]
        == cert_record.certificate_fingerprint_sha256
    )
    assert data["subject_dn"] == cert_record.subject_dn
    assert data["issuer_dn"] == cert_record.issuer_dn


# ---------------------------------------------------------------------------
# Entity not found
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_issue_returns_404_for_unknown_entity(authenticated_api_client):
    response = _post_issue(authenticated_api_client, uuid.uuid4(), _make_csr_pem())
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# CSR validation errors  (serializer rejects before CA is called)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_issue_returns_400_when_csr_pem_missing(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)

    response = authenticated_api_client.post(_issue_url(entity.id), {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_issue_returns_400_for_non_pem_input(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)

    response = _post_issue(authenticated_api_client, entity.id, "not-a-csr")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_issue_returns_400_for_certificate_pem_instead_of_csr(authenticated_api_client):
    """Submitting a certificate PEM where a CSR is expected must be rejected."""
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    # A PEM block with CERTIFICATE header is not a valid CSR
    fake_cert_pem = "-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
    response = _post_issue(authenticated_api_client, entity.id, fake_cert_pem)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Entity eligibility errors  (serializer validates before CA is called)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_issue_returns_409_for_pending_entity(authenticated_api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)
    EntityEntitlementFactory(registered_entity=entity)

    response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_issue_returns_409_for_suspended_entity(authenticated_api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)
    EntityEntitlementFactory(registered_entity=entity)

    response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_issue_returns_400_for_entity_without_entitlements(authenticated_api_client):
    entity = _make_active_entity()
    # no entitlements attached

    response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# CA / issuance errors  (CertificateIssuanceError with structured http_status)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_issue_returns_500_on_ca_signing_failure(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)

    with _patch_issue(
        side_effect=CertificateIssuanceError("Certificate signing failed: CA error")
    ):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
def test_issue_returns_500_when_no_ca_configured(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)

    with _patch_issue(side_effect=CertificateIssuanceError("No usable CA found.")):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
def test_issue_returns_409_on_race_condition_entity_inactive(authenticated_api_client):
    """
    If the entity becomes inactive between serializer validation and CA call
    (race condition), CertificateIssuanceError with http_status=409 is returned.
    """
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)

    with _patch_issue(
        side_effect=CertificateIssuanceError("Entity not active.", http_status=409)
    ):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_issue_error_response_contains_detail(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    msg = "No usable CA found."

    with _patch_issue(side_effect=CertificateIssuanceError(msg)):
        response = _post_issue(authenticated_api_client, entity.id, _make_csr_pem())

    assert response.data["detail"] == msg


# ---------------------------------------------------------------------------
# Auto-revocation on entity status change
# Complements test_signals.py; here we verify that a cert created via the
# issue flow (EntityAccessCertificate in DB) is revoked when the entity is
# later suspended or revoked.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_issued_cert_revoked_when_entity_suspended():
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert = _make_cert_record(entity)

    entity.registration_status = RegistrationStatus.SUSPENDED
    entity.save()

    cert.refresh_from_db()
    assert cert.revoked_at is not None
    assert cert.revocation_reason == "certificateHold"


@pytest.mark.django_db(transaction=True)
def test_issued_cert_revoked_when_entity_revoked():
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert = _make_cert_record(entity)

    entity.registration_status = RegistrationStatus.REVOKED
    entity.save()

    cert.refresh_from_db()
    assert cert.revoked_at is not None
    assert cert.revocation_reason == "cessationOfOperation"


@pytest.mark.django_db(transaction=True)
def test_cert_not_revoked_when_entity_remains_active():
    entity = _make_active_entity()
    EntityEntitlementFactory(registered_entity=entity)
    cert = _make_cert_record(entity)

    entity.registration_status = RegistrationStatus.ACTIVE
    entity.save()

    cert.refresh_from_db()
    assert cert.revoked_at is None
