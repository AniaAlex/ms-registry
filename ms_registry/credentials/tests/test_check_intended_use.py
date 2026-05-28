"""
Tests for GET /registry/wrp/check-intended-use/
"""

import base64
import json

import pytest
from core.models import Identifier, IdentifierType
from credentials.serializers import create_intended_use
from django.urls import reverse
from legal_entities.models import LegalEntityIdentifier
from registry.tests.factories import RegisteredEntityFactory
from rest_framework import status

CHECK_URL = reverse("registry:wrp-check-intended-use")


def _payload(response):
    """Return the decoded payload dict regardless of signing state.

    When REGISTRY_SIGNING_KEY_PEM is set the view returns a JWS compact
    serialization (application/jwt).  Decode the middle segment without
    signature verification so tests work in both signed and unsigned modes.
    """
    if response.get("Content-Type", "").startswith("application/jwt"):
        segment = response.data.split(".")[1]
        padded = segment + "=" * (-len(segment) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    return response.data


_IU_PAYLOAD = {
    "purposes": [{"lang": "en", "content": "Age verification"}],
    "privacy_policy": [{"policy_uri": "https://example.com/privacy"}],
    "credentials": [
        {
            "format": "dc+sd-jwt",
            "meta": {"vct_values": ["https://credentials.example.com/identity"]},
            "claims": [
                {"path": ["given_name"]},
                {"path": ["address", "street_address"]},
            ],
        }
    ],
}


def _make_entity(identifier_value="TEST-ID-001"):
    """Create a RegisteredEntity with a linked legal entity identifier."""
    entity = RegisteredEntityFactory()
    identifier = Identifier.objects.create(
        identifier_type=IdentifierType.EUID,
        identifier_value=identifier_value,
    )
    LegalEntityIdentifier.objects.create(
        legal_entity=entity.legal_entity,
        identifier=identifier,
        is_primary=True,
    )
    return entity


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_rpidentifier_returns_400(authenticated_api_client):
    response = authenticated_api_client.get(CHECK_URL)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Entity lookup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unknown_rpidentifier_returns_false(authenticated_api_client):
    response = authenticated_api_client.get(
        CHECK_URL, {"rpidentifier": "DOES-NOT-EXIST"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert _payload(response)["data"]["isRegistered"] is False


@pytest.mark.django_db
def test_entity_with_no_intended_use_returns_false(authenticated_api_client):
    entity = _make_entity()
    response = authenticated_api_client.get(CHECK_URL, {"rpidentifier": "TEST-ID-001"})
    assert response.status_code == status.HTTP_200_OK
    assert _payload(response)["data"]["isRegistered"] is False
    _ = entity  # used via rpidentifier lookup


# ---------------------------------------------------------------------------
# Basic positive case
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_entity_with_active_intended_use_returns_true(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(CHECK_URL, {"rpidentifier": "TEST-ID-001"})
    assert response.status_code == status.HTTP_200_OK
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_revoked_intended_use_not_counted(authenticated_api_client):
    """validity_end set → excluded from active IU check."""
    from datetime import date

    entity = _make_entity()
    iu = create_intended_use(entity, _IU_PAYLOAD)
    iu.validity_end = date.today()
    iu.save(update_fields=["validity_end", "updated_at"])

    response = authenticated_api_client.get(CHECK_URL, {"rpidentifier": "TEST-ID-001"})
    assert _payload(response)["data"]["isRegistered"] is False


# ---------------------------------------------------------------------------
# Filter: intendeduseidentifier
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_intendeduseidentifier_match(authenticated_api_client):
    entity = _make_entity()
    iu = create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {
            "rpidentifier": "TEST-ID-001",
            "intendeduseidentifier": iu.intended_use_identifier,
        },
    )
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_filter_intendeduseidentifier_no_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "intendeduseidentifier": "IU-WRONG"},
    )
    assert _payload(response)["data"]["isRegistered"] is False


# ---------------------------------------------------------------------------
# Filter: credentialformat
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_credentialformat_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "credentialformat": "dc+sd-jwt"},
    )
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_filter_credentialformat_no_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "credentialformat": "mso_mdoc"},
    )
    assert _payload(response)["data"]["isRegistered"] is False


# ---------------------------------------------------------------------------
# Filter: claimpath
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_claimpath_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "claimpath": "given_name"},
    )
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_filter_claimpath_nested_element_match(authenticated_api_client):
    """'street_address' is inside ['address', 'street_address'] — should match."""
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "claimpath": "street_address"},
    )
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_filter_claimpath_no_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {"rpidentifier": "TEST-ID-001", "claimpath": "date_of_birth"},
    )
    assert _payload(response)["data"]["isRegistered"] is False


# ---------------------------------------------------------------------------
# Filter: policyurl
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filter_policyurl_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {
            "rpidentifier": "TEST-ID-001",
            "policyurl": "https://example.com/privacy",
        },
    )
    assert _payload(response)["data"]["isRegistered"] is True


@pytest.mark.django_db
def test_filter_policyurl_no_match(authenticated_api_client):
    entity = _make_entity()
    create_intended_use(entity, _IU_PAYLOAD)
    response = authenticated_api_client.get(
        CHECK_URL,
        {
            "rpidentifier": "TEST-ID-001",
            "policyurl": "https://other.com/privacy",
        },
    )
    assert _payload(response)["data"]["isRegistered"] is False


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_response_contains_iss_and_iat(authenticated_api_client):
    _make_entity()
    response = authenticated_api_client.get(CHECK_URL, {"rpidentifier": "TEST-ID-001"})
    data = _payload(response)
    assert "iss" in data
    assert "iat" in data
    assert isinstance(data["iat"], int)


@pytest.mark.django_db
def test_signed_response_is_application_jwt(authenticated_api_client, monkeypatch):
    """When sign_jwt succeeds the Content-Type is application/jwt."""
    import core.signing

    monkeypatch.setattr(core.signing, "sign_jwt", lambda payload: "header.payload.sig")
    _make_entity()

    response = authenticated_api_client.get(CHECK_URL, {"rpidentifier": "TEST-ID-001"})
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "application/jwt"
    assert response["x-jku-url"].endswith("/.well-known/jwks.json")
