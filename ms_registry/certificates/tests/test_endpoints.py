"""
Tests for certificates endpoints.
"""

import uuid
from unittest.mock import patch

import pytest
from core.models import EntitlementType, EntityRole, RegistrationStatus
from django.urls import reverse
from registry.tests.factories import (
    EntityEntitlementFactory,
    RegisteredEntityFactory,
)
from rest_framework import status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_cnf(api_client, entity_id):
    url = reverse("certificates:cnf", args=[entity_id])
    return api_client.get(url)


def _make_active_entity(**kwargs):
    return RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE, **kwargs
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cnf_returns_200_for_active_entity(api_client):
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt", return_value="signed.jwt.token"):
        response = _get_cnf(api_client, entity.id)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["token"] == "signed.jwt.token"


@pytest.mark.django_db
def test_cnf_payload_sub_is_entity_id(api_client):
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    payload = mock_sign.call_args[0][0]
    assert payload["sub"] == str(entity.id)


@pytest.mark.django_db
def test_cnf_payload_issuer_matches_request_host(api_client):
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    payload = mock_sign.call_args[0][0]
    assert payload["iss"] == "http://testserver"


@pytest.mark.django_db
def test_cnf_payload_exp_is_24h_after_iat(api_client):
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    payload = mock_sign.call_args[0][0]
    assert payload["exp"] - payload["iat"] == 24 * 60 * 60


@pytest.mark.django_db
def test_cnf_payload_contains_entity_name(api_client):
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    cnf = mock_sign.call_args[0][0]["cnf"]
    assert cnf["name"] == entity.display_name


@pytest.mark.django_db
def test_cnf_payload_country_from_physical_address(api_client):
    """When primary_identifier has no country_code, falls back to physical_address."""
    entity = _make_active_entity()
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    cnf = mock_sign.call_args[0][0]["cnf"]
    assert (
        cnf["country"] == "SE"
    )  # LegalEntityFactory sets physical_address.country_code = "SE"


@pytest.mark.django_db
def test_cnf_payload_role_and_entitlements(api_client):
    entity = _make_active_entity(entity_role=EntityRole.RELYING_PARTY)
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    cnf = mock_sign.call_args[0][0]["cnf"]
    assert cnf["role"] == EntityRole.RELYING_PARTY
    assert EntitlementType.SERVICE_PROVIDER in cnf["entitlements"]
    assert cnf["registration_status"] == RegistrationStatus.ACTIVE


@pytest.mark.django_db
def test_cnf_payload_multiple_entitlements(api_client):
    entity = _make_active_entity(entity_role=EntityRole.ATTESTATION_PROVIDER)
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.QEAA_PROVIDER,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/QEAA_Provider",
    )
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/Service_Provider",
    )
    with patch("certificates.views.sign_jwt") as mock_sign:
        mock_sign.return_value = "token"
        _get_cnf(api_client, entity.id)
    cnf = mock_sign.call_args[0][0]["cnf"]
    assert set(cnf["entitlements"]) == {
        EntitlementType.QEAA_PROVIDER,
        EntitlementType.SERVICE_PROVIDER,
    }


# ---------------------------------------------------------------------------
# CnfPageView – HTML page
# ---------------------------------------------------------------------------


def _get_cnf_page(client, entity_id):
    url = reverse("certificates:cnf-page", args=[entity_id])
    return client.get(url)


@pytest.mark.django_db
class TestCnfPageView:
    def test_returns_200_and_renders_token_for_active_entity(self, api_client):
        entity = _make_active_entity()
        with patch(
            "certificates.views.sign_jwt", return_value="signed.jwt.token"
        ), patch("certificates.views.pyjwt.decode", return_value={"cnf": {}}):
            response = _get_cnf_page(api_client, entity.id)
        assert response.status_code == status.HTTP_200_OK
        assert b"signed.jwt.token" in response.content

    def test_does_not_show_error_on_success(self, api_client):
        entity = _make_active_entity()
        with patch("certificates.views.sign_jwt", return_value="tok"), patch(
            "certificates.views.pyjwt.decode", return_value={"cnf": {}}
        ):
            response = _get_cnf_page(api_client, entity.id)
        assert b"Could Not Issue" not in response.content

    def test_returns_404_for_unknown_entity(self, api_client):
        response = _get_cnf_page(api_client, uuid.uuid4())
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert b"Entity not found" in response.content

    def test_returns_409_for_pending_entity(self, api_client):
        entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)
        response = _get_cnf_page(api_client, entity.id)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert b"pending" in response.content

    def test_returns_409_for_suspended_entity(self, api_client):
        entity = RegisteredEntityFactory(
            registration_status=RegistrationStatus.SUSPENDED
        )
        response = _get_cnf_page(api_client, entity.id)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert b"suspended" in response.content

    def test_returns_409_for_revoked_entity(self, api_client):
        entity = RegisteredEntityFactory(registration_status=RegistrationStatus.REVOKED)
        response = _get_cnf_page(api_client, entity.id)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert b"revoked" in response.content


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cnf_returns_404_for_unknown_entity(api_client):
    response = _get_cnf(api_client, uuid.uuid4())
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_cnf_returns_409_for_pending_entity(api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)
    response = _get_cnf(api_client, entity.id)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "pending" in response.data["detail"]


@pytest.mark.django_db
def test_cnf_returns_409_for_suspended_entity(api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)
    response = _get_cnf(api_client, entity.id)
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_cnf_returns_409_for_revoked_entity(api_client):
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.REVOKED)
    response = _get_cnf(api_client, entity.id)
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_cnf_returns_409_when_no_contact_info(api_client):
    """
    GEN-6.6.1-07 [CHOICE]: cnf must be rejected if none of the three contact
    methods (support URL, email, phone) are present on the entity — the resulting
    certificate would fail upload validation anyway.
    """
    from legal_entities.tests.factories import LegalEntityFactory

    legal_entity = LegalEntityFactory(email=None, phone=None)
    entity = RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE,
        legal_entity=legal_entity,
    )
    # No support URIs, no email, no phone
    assert not entity.support_uris.exists()
    response = _get_cnf(api_client, entity.id)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "GEN-6.6.1-07" in response.data["detail"]
