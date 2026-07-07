"""
Tests for Registry app endpoints.
"""

from unittest.mock import patch

import pytest
from core.models import EntitlementType, EntityRole, RegistrationStatus
from django.test import Client
from django.urls import reverse
from legal_entities.tests.factories import LegalEntityFactory
from participant.tests.factories import ParticipantFactory
from registry.models import RegisteredEntity, SupervisoryAuthority
from registry.tests.factories import (
    EntityEntitlementFactory,
    EntitySupportURIFactory,
    RegisteredEntityFactory,
    SupervisoryAuthorityFactory,
)
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# =============================================================================
# SupervisoryAuthority API
# =============================================================================


@pytest.mark.django_db
def test_list_supervisory_authorities(authenticated_api_client):
    SupervisoryAuthorityFactory.create_batch(2)
    url = reverse("registry:supervisory-authority-list-create")
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_create_supervisory_authority_api(authenticated_api_client):
    url = reverse("registry:supervisory-authority-list-create")
    data = {
        "authority_name": "French CNIL",
        "country_code": "FR",
        "email": "contact@cnil.fr",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert SupervisoryAuthority.objects.count() == 1
    assert SupervisoryAuthority.objects.first().authority_name == "French CNIL"


@pytest.mark.django_db
def test_create_supervisory_authority_requires_contact(authenticated_api_client):
    url = reverse("registry:supervisory-authority-list-create")
    data = {"authority_name": "Test Authority", "country_code": "SE"}
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_get_supervisory_authority_detail(authenticated_api_client):
    authority = SupervisoryAuthorityFactory(authority_name="Test DPA")
    url = reverse("registry:supervisory-authority-detail", args=[authority.id])
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["authority_name"] == "Test DPA"


# =============================================================================
# RegisteredEntity API
# =============================================================================


@pytest.mark.django_db
def test_list_registered_entities(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    RegisteredEntityFactory(legal_entity=legal_entity, supervisory_authority=authority)
    url = reverse("registry:entity-list-create")
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_registry_uri_is_set_after_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "trade_name": "Test Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    assert entity.registry_uri != ""
    assert str(entity.id) in entity.registry_uri
    assert "/wrp/" in entity.registry_uri


@pytest.mark.django_db
def test_entity_is_active_after_registration(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "trade_name": "Test Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    assert entity.registration_status == RegistrationStatus.ACTIVE


@pytest.mark.django_db
def test_create_entity_adds_authenticated_user_as_first_operator():
    participant = ParticipantFactory()
    token = str(RefreshToken.for_user(participant).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "trade_name": "My Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    # The registering user is the sole (first) operator — never empty.
    assert list(entity.operators.all()) == [participant]


@pytest.mark.django_db
def test_wrp_post_adds_authenticated_user_as_operator():
    participant = ParticipantFactory()
    token = str(RefreshToken.for_user(participant).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    url = reverse("registry:wrp")
    data = {
        "legal_entity_identifier": "SE5560360793",
        "legal_entity_identifier_type": "EUID",
        "legal_name": "WRP Test AB",
        "country_code": "SE",
        "domain_uri": "https://wrp.example.com",
        "entitlements": ["https://uri.etsi.org/19475/Entitlement/Service_Provider"],
        "support_uris": ["https://support.example.com"],
        "supervisory_authority_name": "Swedish DPA",
        "supervisory_authority_country": "SE",
    }
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(id=response.data["id"])
    assert list(entity.operators.all()) == [participant]


@pytest.mark.django_db
def test_wrp_post_entity_is_active_after_registration():
    participant = ParticipantFactory()
    token = str(RefreshToken.for_user(participant).access_token)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    url = reverse("registry:wrp")
    data = {
        "legal_entity_identifier": "SE5560360793",
        "legal_entity_identifier_type": "EUID",
        "legal_name": "WRP Test AB",
        "country_code": "SE",
        "domain_uri": "https://wrp.example.com",
        "entitlements": ["https://uri.etsi.org/19475/Entitlement/Service_Provider"],
        "support_uris": ["https://support.example.com"],
        "supervisory_authority_name": "Swedish DPA",
        "supervisory_authority_country": "SE",
    }
    response = client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(id=response.data["id"])
    assert entity.registration_status == RegistrationStatus.ACTIVE


@pytest.mark.django_db
def test_entity_detail_page_denies_non_operator(authenticated_api_client):
    """The HTML detail page must not disclose an entity a participant does not
    operate. Non-operators get 404 (not 403) so entity IDs are not enumerable.
    """
    entity = RegisteredEntityFactory(operators=[ParticipantFactory()])
    url = reverse("registry:entity-detail", args=[entity.id])
    assert authenticated_api_client.get(url).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_entity_detail_page_allows_operator(authenticated_api_client):
    entity = RegisteredEntityFactory(operators=[authenticated_api_client.participant])
    url = reverse("registry:entity-detail", args=[entity.id])
    assert authenticated_api_client.get(url).status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_wrp_put_denied_for_non_operator(authenticated_api_client):
    entity = RegisteredEntityFactory(
        operators=[ParticipantFactory()], entity_role=EntityRole.RELYING_PARTY
    )
    response = authenticated_api_client.put(
        reverse("registry:wrp"),
        {"id": str(entity.id), "trade_name": "Hijacked"},
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    entity.refresh_from_db()
    assert entity.trade_name != "Hijacked"


@pytest.mark.django_db
def test_wrp_delete_denied_for_non_operator(authenticated_api_client):
    entity = RegisteredEntityFactory(operators=[ParticipantFactory()])
    response = authenticated_api_client.delete(
        reverse("registry:wrp"), {"id": str(entity.id)}, format="json"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert RegisteredEntity.objects.filter(id=entity.id).exists()


@pytest.mark.django_db
def test_operators_m2m_supports_multiple_and_is_never_empty():
    # Factory default: at least one operator (invariant mirror).
    entity = RegisteredEntityFactory()
    assert entity.operators.count() == 1

    # A second operator can be added and both are responsible for the entity.
    op1 = entity.operators.first()
    op2 = ParticipantFactory()
    entity.operators.add(op2)

    assert entity.operators.count() == 2
    assert set(entity.operators.all()) == {op1, op2}
    # Reverse accessor: each operator sees the shared entity.
    assert entity in op1.registered_entities.all()
    assert entity in op2.registered_entities.all()


@pytest.mark.django_db
def test_factory_accepts_explicit_operators():
    op1 = ParticipantFactory()
    op2 = ParticipantFactory()
    entity = RegisteredEntityFactory(operators=[op1, op2])
    assert set(entity.operators.all()) == {op1, op2}


@pytest.mark.django_db
def test_create_registered_entity_missing_required_fields(authenticated_api_client):
    url = reverse("registry:entity-list-create")
    response = authenticated_api_client.post(
        url, {"trade_name": "Test Service"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_domain_uri_is_saved_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "trade_name": "Test Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    assert entity.domain_uri == "https://service.example.com"


@pytest.mark.django_db
def test_domain_uri_returned_in_response(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["data"]["domain_uri"] == "https://service.example.com"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad_domain_uri",
    [
        "https://service.example.com:8008",  # port
        "https://service.example.com:8008/",  # port + trailing slash
        "https://service.example.com/verifier_1",  # path
        "https://service.example.com/?q=1",  # query
    ],
)
def test_domain_uri_rejects_port_or_path(authenticated_api_client, bad_domain_uri):
    """Only the host survives into the cert dNSName, so a port/path in
    domain_uri is rejected rather than silently dropped."""
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": bad_domain_uri,
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "domain_uri" in response.data["errors"]


@pytest.mark.django_db
def test_domain_uri_required_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "domain_uri" in response.data["errors"]


@pytest.mark.django_db
def test_instance_uri_required_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "instance_uri" in response.data["errors"]


@pytest.mark.django_db
def test_instance_uri_saved_and_returned_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["data"]["instance_uri"] == "https://service.example.com:8008/"
    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    assert entity.instance_uri == "https://service.example.com:8008/"


@pytest.mark.django_db
def test_domain_uri_rejected_for_different_legal_entity(authenticated_api_client):
    """A domain_uri already claimed by another legal entity is rejected."""
    other_entity = RegisteredEntityFactory(domain_uri="https://service.example.com")
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    assert other_entity.legal_entity_id != legal_entity.id
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "domain_uri" in response.data["errors"]


@pytest.mark.django_db
def test_domain_uri_clash_detected_across_scheme_port_path(authenticated_api_client):
    """The guard compares the host, so a different legal entity cannot bypass
    it by varying scheme/port/path while minting the same dNSName."""
    RegisteredEntityFactory(domain_uri="https://service.example.com")
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        # same host, different scheme/port/path → same SAN dNSName
        "domain_uri": "http://service.example.com:8008/path",
        "instance_uri": "https://service.example.com:9000/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "domain_uri" in response.data["errors"]


@pytest.mark.django_db
def test_domain_uri_different_host_allowed(authenticated_api_client):
    """A genuinely different host is not a clash."""
    RegisteredEntityFactory(domain_uri="https://service.example.com")
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://other.example.com",
        "instance_uri": "https://other.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_domain_uri_reusable_by_same_legal_entity(authenticated_api_client):
    """The same legal entity may reuse its domain_uri across registrations."""
    legal_entity = LegalEntityFactory()
    RegisteredEntityFactory(
        legal_entity=legal_entity, domain_uri="https://service.example.com"
    )
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_support_uris_required_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider"],
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "support_uris" in response.data["errors"]


@pytest.mark.django_db
def test_entitlements_required_on_create(authenticated_api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": ["https://support.example.com"],
        "supervisory_authority": str(authority.id),
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "entitlements" in response.data["errors"]


@pytest.mark.django_db
def test_domain_uri_returned_in_wrp_response(authenticated_api_client):
    entity = RegisteredEntityFactory(domain_uri="https://wrp.example.com")
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/Service_Provider",
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    EntitySupportURIFactory(registered_entity=entity)
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["domainURI"] == "https://wrp.example.com"


# =============================================================================
# Home view
# =============================================================================


@pytest.mark.django_db
def test_home_page_loads(auth_client):
    response = auth_client.get(reverse("home"))
    assert response.status_code == 200
    assert "home.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_home_page_shows_own_entities(operator, operator_client):
    RegisteredEntityFactory(trade_name="Visible Entity", operators=[operator])
    response = operator_client.get(reverse("home"))
    assert b"Visible Entity" in response.content


@pytest.mark.django_db
def test_home_page_hides_other_operators_entities(operator, operator_client):
    # Entity owned by a different operator must not appear on this operator's
    # dashboard.
    RegisteredEntityFactory(trade_name="Someone Elses Entity")
    response = operator_client.get(reverse("home"))
    assert b"Someone Elses Entity" not in response.content


@pytest.mark.django_db
def test_home_page_shows_shared_entity_to_all_operators(operator):
    # An entity with two operators is visible to both of them.
    other = ParticipantFactory()
    RegisteredEntityFactory(trade_name="Shared Entity", operators=[operator, other])

    for user in (operator, other):
        client = Client()
        token = str(RefreshToken.for_user(user).access_token)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        response = client.get(reverse("home"))
        assert b"Shared Entity" in response.content


@pytest.mark.django_db
def test_home_page_empty_state(auth_client):
    response = auth_client.get(reverse("home"))
    assert b"No registered entities yet" in response.content


# =============================================================================
# WRP filter API
# =============================================================================


@pytest.fixture
def wrp_data(db):
    entity_intermediary = RegisteredEntityFactory(is_intermediary=True)
    entity_not_intermediary = RegisteredEntityFactory(is_intermediary=False)
    entity_pub_eaa = RegisteredEntityFactory(
        entity_role=EntityRole.ATTESTATION_PROVIDER, is_psb=True
    )

    EntityEntitlementFactory(
        registered_entity=entity_intermediary,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/Service_Provider",
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    EntityEntitlementFactory(
        registered_entity=entity_not_intermediary,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/Service_Provider",
        entitlement_type=EntitlementType.SERVICE_PROVIDER,
    )
    EntityEntitlementFactory(
        registered_entity=entity_pub_eaa,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider",
        entitlement_type=EntitlementType.PUB_EAA_PROVIDER,
    )

    EntitySupportURIFactory(registered_entity=entity_intermediary)
    EntitySupportURIFactory(registered_entity=entity_not_intermediary)
    EntitySupportURIFactory(registered_entity=entity_pub_eaa)

    return entity_intermediary, entity_not_intermediary, entity_pub_eaa


@pytest.mark.django_db
def test_filter_by_entitlement_service_provider(authenticated_api_client, wrp_data):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/Service_Provider"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_filter_by_entitlement_pub_eaa_provider(authenticated_api_client, wrp_data):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_no_entitlement_filter_returns_all(authenticated_api_client, wrp_data):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 3


@pytest.mark.django_db
def test_filter_by_entitlement_no_match_returns_empty(
    authenticated_api_client, wrp_data
):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/NonExistent"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0


@pytest.mark.django_db
def test_filter_by_entitlement_invalid_uri_returns_empty(
    authenticated_api_client, wrp_data
):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(url, {"entitlement": "invalid-uri"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", 1),
        ("1", 1),
        ("false", 2),
        ("0", 2),
        ("invalid", 2),
    ],
)
def test_filter_by_isintermediary(authenticated_api_client, wrp_data, value, expected):
    response = authenticated_api_client.get(
        reverse("registry:wrp"), {"isintermediary": value}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == expected


@pytest.mark.django_db
def test_combined_filter_entitlement_and_isintermediary_true(
    authenticated_api_client, wrp_data
):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url,
        {
            "entitlement": "http://data.europa.eu/eudi/entitlement/Service_Provider",
            "isintermediary": "true",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["isIntermediary"] is True


@pytest.mark.django_db
def test_combined_filter_entitlement_and_isintermediary_false(
    authenticated_api_client, wrp_data
):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url,
        {
            "entitlement": "http://data.europa.eu/eudi/entitlement/Service_Provider",
            "isintermediary": "false",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["isIntermediary"] is False


@pytest.mark.django_db
def test_combined_filter_no_match(authenticated_api_client, wrp_data):
    url = reverse("registry:wrp")
    response = authenticated_api_client.get(
        url,
        {
            "entitlement": "http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider",
            "isintermediary": "true",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0


# =============================================================================
# JWKSView
# =============================================================================


@pytest.mark.django_db
def test_jwks_returns_real_key_when_env_var_set(authenticated_api_client):
    fake_jwk = {"kty": "EC", "crv": "P-256", "x": "abc", "y": "def"}
    with patch("core.signing.public_key_as_jwk", return_value=fake_jwk):
        response = authenticated_api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["keys"][0] == fake_jwk


@pytest.mark.django_db
def test_jwks_falls_back_to_placeholder_when_key_not_configured(
    authenticated_api_client,
):
    from core.signing import KeyNotConfiguredError

    with patch("core.signing.public_key_as_jwk", side_effect=KeyNotConfiguredError):
        response = authenticated_api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["keys"][0]["kid"] == "ms-registry-signing-key-v1"


@pytest.mark.django_db
def test_jwks_returns_500_for_invalid_key_configuration(authenticated_api_client):
    with patch("core.signing.public_key_as_jwk", side_effect=ValueError("bad key")):
        response = authenticated_api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "detail" in response.data
