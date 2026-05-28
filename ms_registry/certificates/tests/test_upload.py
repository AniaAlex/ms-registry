"""
Tests for POST /certificates/upload/<entity_id>/  (AccessCertificateUploadView)
and GET/POST /certificates/upload/<entity_id>/view/  (AccessCertificateUploadPageView).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from certificates.models import EntityAccessCertificate
from core.management.commands.generate_access_certificates_help_function import (
    generate_certificate_from_cnf,
)
from core.models import EntitlementType, Identifier, IdentifierType, RegistrationStatus
from django.urls import reverse
from registry.tests.factories import (
    EntityEntitlementFactory,
    RegisteredEntityFactory,
)
from rest_framework import status

# TODO: Add a proper CT log implementation, e.g. using the python-ct library
# _MOCK_CT = ("mock-log-id", 1_700_000_000_000, b'{"sct_version":"v2"}')

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_active_entity(**kwargs):
    return RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE, **kwargs
    )


def _upload_url(entity_id):
    return reverse("certificates:upload", args=[entity_id])


def _upload_page_url(entity_id):
    return reverse("certificates:upload-page", args=[entity_id])


def _post_upload(authenticated_api_client, entity_id, pem, **extra):
    return authenticated_api_client.post(
        _upload_url(entity_id),
        {"certificate_pem": pem},
        format="json",
        **extra,
    )


# ── certificate builder (reuses the dev-tool helper) ──────────────────────────


def _make_cert_pem(entity) -> str:
    """Generate a valid self-signed certificate matching the entity's registry data."""
    from registry.tests.factories import EntitySupportURIFactory

    # GEN-6.6.1-05: organizationIdentifier is mandatory for legal persons.
    # Ensure a primary identifier exists before building the cert so that the
    # generated certificate and the registry data are consistent.
    if (
        entity.legal_entity.entity_type == "legal_person"
        and not entity.primary_identifier
    ):
        _add_identifier(entity)

    entity.refresh_from_db()
    primary_id = entity.primary_identifier

    # Ensure entity has at least one support URI (required by GEN-6.6.1-07)
    support_uri = entity.support_uris.first()
    if not support_uri:
        support_uri = EntitySupportURIFactory(registered_entity=entity, is_primary=True)

    cnf = {
        "entity_type": entity.legal_entity.entity_type,
        "name": entity.legal_entity.display_name,
        "country": (primary_id.country_code if primary_id else None)
        or (
            entity.legal_entity.physical_address.country_code
            if entity.legal_entity.physical_address
            else "XX"
        ),
        "org_identifier": primary_id.identifier_value if primary_id else None,
        "org_identifier_type": primary_id.identifier_type if primary_id else None,
        "role": entity.entity_role,
        "entitlements": [e.entitlement_type for e in entity.entitlements.all()],
        "urls": [support_uri.support_uri],
        "contact": {"email": entity.legal_entity.email, "phone": None},
    }
    pem, _ = generate_certificate_from_cnf(cnf)
    return pem


def _add_identifier(
    entity,
    identifier_value="5568002755",
    identifier_type=IdentifierType.NATIONAL_BUSINESS_REG,
    country="SE",
):
    """Attach a primary Identifier to the entity's LegalEntity."""
    identifier = Identifier.objects.create(
        identifier_type=identifier_type,
        identifier_value=identifier_value,
        country_code=country,
    )
    entity.legal_entity.primary_identifier = identifier
    entity.legal_entity.save()
    entity.refresh_from_db()
    return identifier


# ── upload JSON API – happy path ───────────────────────────────────────────────


@pytest.mark.django_db
def test_upload_returns_201_for_valid_cert(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_upload_response_contains_expected_fields(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    response = _post_upload(authenticated_api_client, entity.id, pem)
    data = response.data
    for field in (
        "id",
        "certificate_serial",
        "certificate_fingerprint_sha256",
        "subject_dn",
        "issuer_dn",
        "not_before",
        "not_after",
    ):
        assert field in data, f"Missing field: {field}"


@pytest.mark.django_db
def test_upload_stores_certificate_in_db(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    _post_upload(authenticated_api_client, entity.id, pem)
    assert EntityAccessCertificate.objects.filter(registered_entity=entity).exists()


@pytest.mark.django_db
def test_upload_sets_is_current_true(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    _post_upload(authenticated_api_client, entity.id, pem)
    cert = EntityAccessCertificate.objects.get(registered_entity=entity)
    assert cert.is_current is True


@pytest.mark.django_db
def test_upload_marks_previous_cert_not_current(authenticated_api_client):
    entity = _make_active_entity()
    # Pre-create an existing current certificate
    old_cert = EntityAccessCertificate.objects.create(
        registered_entity=entity,
        certificate_serial="OLD",
        not_before=datetime.now(tz=timezone.utc) - timedelta(days=10),
        not_after=datetime.now(tz=timezone.utc) + timedelta(days=355),
        is_current=True,
    )
    pem = _make_cert_pem(entity)
    _post_upload(authenticated_api_client, entity.id, pem)
    old_cert.refresh_from_db()
    assert old_cert.is_current is False


# TODO: Add a proper CT log implementation, e.g. using the python-ct library
# @pytest.mark.django_db
# def test_upload_stores_ct_log_fields(authenticated_api_client):
#     entity = _make_active_entity()
#     pem = _make_cert_pem(entity)
#     _post_upload(authenticated_api_client, entity.id, pem)
#     cert = EntityAccessCertificate.objects.get(registered_entity=entity)
#     assert cert.ct_log_id == "mock-log-id"
#     assert cert.ct_sct == b'{"sct_version":"v2"}'


@pytest.mark.django_db
def test_upload_stores_certificate_pem(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    _post_upload(authenticated_api_client, entity.id, pem)
    cert = EntityAccessCertificate.objects.get(registered_entity=entity)
    assert "BEGIN CERTIFICATE" in cert.certificate_pem


@pytest.mark.django_db
def test_upload_with_identifier_validates_org_identifier(authenticated_api_client):
    entity = _make_active_entity()
    _add_identifier(entity)
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    pem = _make_cert_pem(entity)
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_upload_lei_identifier_uses_xg_country_code(authenticated_api_client):
    """
    ETSI EN 319 412-1 LEG-5.1.4-03 item 4: LEI is a global scheme; the country
    code in the organizationIdentifier shall be 'XG', not the entity's national
    country code.  e.g. LEIXG-<value>, never LEISE-<value>.
    """
    entity = _make_active_entity()
    _add_identifier(
        entity,
        identifier_value="9695007586BDF3CACA97",
        identifier_type=IdentifierType.LEI,
        country="SE",
    )
    pem = _make_cert_pem(entity)
    # Certificate must be accepted — organizationIdentifier should be LEIXG-…
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_201_CREATED
    # Confirm the stored DN actually contains XG, not SE
    cert = EntityAccessCertificate.objects.get(registered_entity=entity)
    assert "LEIXG-" in cert.subject_dn
    assert "LEISE-" not in cert.subject_dn


# ── upload JSON API – error cases ─────────────────────────────────────────────


@pytest.mark.django_db
def test_upload_returns_404_for_unknown_entity(authenticated_api_client):
    response = _post_upload(
        authenticated_api_client,
        uuid.uuid4(),
        "-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_upload_returns_409_for_pending_entity(authenticated_api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)
    response = _post_upload(authenticated_api_client, entity.id, "pem")
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_upload_returns_409_for_suspended_entity(authenticated_api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)
    response = _post_upload(authenticated_api_client, entity.id, "pem")
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_upload_returns_409_for_revoked_entity(authenticated_api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.REVOKED)
    response = _post_upload(authenticated_api_client, entity.id, "pem")
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_upload_returns_400_for_invalid_pem(authenticated_api_client):
    entity = _make_active_entity()
    response = _post_upload(authenticated_api_client, entity.id, "not-a-cert")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_returns_400_for_wrong_organization_name(authenticated_api_client):
    from certificates.tests._cert_builder import build_cert_with_overrides

    entity = _make_active_entity()
    pem = build_cert_with_overrides(entity, org_name="Wrong Company Name")
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    errors = str(response.data)
    assert "organization" in errors.lower()


@pytest.mark.django_db
def test_upload_returns_400_for_wrong_country(authenticated_api_client):
    from certificates.tests._cert_builder import build_cert_with_overrides

    entity = _make_active_entity()
    pem = build_cert_with_overrides(entity, country="DE")
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "country" in str(response.data).lower()


@pytest.mark.django_db
def test_upload_returns_400_for_expired_cert(authenticated_api_client):
    from certificates.tests._cert_builder import build_cert_with_overrides

    entity = _make_active_entity()
    past = datetime.now(tz=timezone.utc) - timedelta(days=400)
    pem = build_cert_with_overrides(
        entity,
        not_valid_before=past - timedelta(days=365),
        not_valid_after=past,
    )
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "expired" in str(response.data).lower()


@pytest.mark.django_db
def test_upload_returns_400_for_missing_entitlement_oid(authenticated_api_client):
    entity = _make_active_entity()
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    # Build cert with no entitlements in SAN
    from core.management.commands.generate_access_certificates_help_function import (
        generate_certificate_from_cnf,
    )

    cnf = {
        "name": entity.display_name,
        "country": entity.legal_entity.physical_address.country_code,
        "org_identifier": None,
        "org_identifier_type": None,
        "role": entity.entity_role,
        "entitlements": [],  # intentionally empty
        "urls": ["https://example.com"],  # satisfy GEN-6.6.1-07 contact requirement
        "contact": {"email": None, "phone": None},
    }
    pem, _ = generate_certificate_from_cnf(cnf)
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "entitlement" in str(response.data).lower()


@pytest.mark.django_db
def test_upload_returns_400_for_legal_person_without_primary_identifier(
    authenticated_api_client,
):
    """
    GEN-6.6.1-05: organizationIdentifier is mandatory for legal persons.
    If the entity has no primary_identifier in the registry, the certificate
    cannot carry a valid organizationIdentifier and must be rejected.
    """
    from core.management.commands.generate_access_certificates_help_function import (
        generate_certificate_from_cnf,
    )

    entity = _make_active_entity()
    # Confirm no primary identifier is set (factory default)
    assert entity.primary_identifier is None

    cnf = {
        "entity_type": "legal_person",
        "name": entity.display_name,
        "country": entity.legal_entity.physical_address.country_code,
        "org_identifier": None,  # no identifier → cert has no organizationIdentifier
        "org_identifier_type": None,
        "role": entity.entity_role,
        "entitlements": [],
        "urls": ["https://example.com"],
        "contact": {"email": None, "phone": None},
    }
    pem, _ = generate_certificate_from_cnf(cnf)
    response = _post_upload(authenticated_api_client, entity.id, pem)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "organizationidentifier" in str(response.data).lower()


# ── upload HTML page ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_upload_page_get_returns_200(authenticated_api_client):
    entity = _make_active_entity()
    response = authenticated_api_client.get(_upload_page_url(entity.id))
    assert response.status_code == 200
    assert b"Upload Access Certificate" in response.content


@pytest.mark.django_db
def test_upload_page_get_shows_entity_name(authenticated_api_client):
    entity = _make_active_entity()
    response = authenticated_api_client.get(_upload_page_url(entity.id))
    assert entity.display_name.encode() in response.content


@pytest.mark.django_db
def test_upload_page_get_404_for_unknown_entity(authenticated_api_client):
    response = authenticated_api_client.get(_upload_page_url(uuid.uuid4()))
    assert response.status_code == 404


@pytest.mark.django_db
def test_upload_page_post_success_shows_cert_details(authenticated_api_client):
    entity = _make_active_entity()
    pem = _make_cert_pem(entity)
    response = authenticated_api_client.post(
        _upload_page_url(entity.id),
        {"certificate_pem": pem},
    )
    assert response.status_code == 201
    assert b"Certificate Accepted" in response.content


@pytest.mark.django_db
def test_upload_page_post_shows_validation_errors(authenticated_api_client):
    entity = _make_active_entity()
    response = authenticated_api_client.post(
        _upload_page_url(entity.id),
        {"certificate_pem": "garbage"},
    )
    assert response.status_code == 400
    assert b"Validation Errors" in response.content


# ── Certificate detail page ────────────────────────────────────────────────────


def _detail_page_url(entity_id):
    return reverse("certificates:detail-page", args=[entity_id])


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


@pytest.mark.django_db
def test_detail_page_returns_200_for_valid_cert(authenticated_api_client):
    entity = _make_active_entity()
    _make_cert_record(entity)
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"AABBCC" in response.content


@pytest.mark.django_db
def test_detail_page_returns_404_for_unknown_entity(authenticated_api_client):
    import uuid

    response = authenticated_api_client.get(_detail_page_url(uuid.uuid4()))
    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_page_shows_no_cert_message_when_none_stored(authenticated_api_client):
    entity = _make_active_entity()
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content


@pytest.mark.django_db
def test_detail_page_excludes_not_yet_valid_cert(authenticated_api_client):
    """
    A certificate whose not_before is in the future must not be shown —
    the query filters not_before__lte=now in addition to not_after__gt=now.
    """
    entity = _make_active_entity()
    future = datetime.now(tz=timezone.utc) + timedelta(days=1)
    _make_cert_record(entity, not_before=future)
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content


@pytest.mark.django_db
def test_detail_page_excludes_expired_cert(authenticated_api_client):
    entity = _make_active_entity()
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
    entity = _make_active_entity()
    _make_cert_record(
        entity,
        revoked_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
    )
    response = authenticated_api_client.get(_detail_page_url(entity.id))
    assert response.status_code == 200
    assert b"No active certificate found" in response.content
