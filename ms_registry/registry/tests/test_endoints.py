"""
Tests for Registry app endpoints.
"""

from unittest.mock import patch

import pytest
from core.models import EntitlementType, EntityRole
from django.urls import reverse
from legal_entities.tests.factories import LegalEntityFactory
from registry.models import RegisteredEntity, SupervisoryAuthority
from registry.tests.factories import (
    EntityEntitlementFactory,
    EntitySupportURIFactory,
    RegisteredEntityFactory,
    SupervisoryAuthorityFactory,
)
from rest_framework import status

# =============================================================================
# SupervisoryAuthority API
# =============================================================================


@pytest.mark.django_db
def test_list_supervisory_authorities(api_client):
    SupervisoryAuthorityFactory.create_batch(2)
    url = reverse("registry:supervisory-authority-list-create")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_create_supervisory_authority_api(api_client):
    url = reverse("registry:supervisory-authority-list-create")
    data = {
        "authority_name": "French CNIL",
        "country_code": "FR",
        "email": "contact@cnil.fr",
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert SupervisoryAuthority.objects.count() == 1
    assert SupervisoryAuthority.objects.first().authority_name == "French CNIL"


@pytest.mark.django_db
def test_create_supervisory_authority_requires_contact(api_client):
    url = reverse("registry:supervisory-authority-list-create")
    data = {"authority_name": "Test Authority", "country_code": "SE"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_get_supervisory_authority_detail(api_client):
    authority = SupervisoryAuthorityFactory(authority_name="Test DPA")
    url = reverse("registry:supervisory-authority-detail", args=[authority.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["authority_name"] == "Test DPA"


# =============================================================================
# RegisteredEntity API
# =============================================================================


@pytest.mark.django_db
def test_list_registered_entities(api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    RegisteredEntityFactory(legal_entity=legal_entity, supervisory_authority=authority)
    url = reverse("registry:entity-list-create")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_registry_uri_is_set_after_create(api_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "entity_role": EntityRole.RELYING_PARTY,
        "trade_name": "Test Service",
        "supervisory_authority": str(authority.id),
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    entity = RegisteredEntity.objects.get(legal_entity=legal_entity)
    assert entity.registry_uri != ""
    assert str(entity.id) in entity.registry_uri
    assert "/wrp/" in entity.registry_uri


@pytest.mark.django_db
def test_create_registered_entity_missing_required_fields(api_client):
    url = reverse("registry:entity-list-create")
    response = api_client.post(url, {"trade_name": "Test Service"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Home view
# =============================================================================


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "home.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_home_page_shows_entities(client):
    RegisteredEntityFactory(trade_name="Visible Entity")
    response = client.get(reverse("home"))
    assert b"Visible Entity" in response.content


@pytest.mark.django_db
def test_home_page_empty_state(client):
    response = client.get(reverse("home"))
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
def test_filter_by_entitlement_service_provider(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/Service_Provider"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_filter_by_entitlement_pub_eaa_provider(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_no_entitlement_filter_returns_all(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 3


@pytest.mark.django_db
def test_filter_by_entitlement_no_match_returns_empty(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
        url, {"entitlement": "http://data.europa.eu/eudi/entitlement/NonExistent"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0


@pytest.mark.django_db
def test_filter_by_entitlement_invalid_uri_returns_empty(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(url, {"entitlement": "invalid-uri"})
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
def test_filter_by_isintermediary(api_client, wrp_data, value, expected):
    response = api_client.get(reverse("registry:wrp"), {"isintermediary": value})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == expected


@pytest.mark.django_db
def test_combined_filter_entitlement_and_isintermediary_true(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
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
def test_combined_filter_entitlement_and_isintermediary_false(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
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
def test_combined_filter_no_match(api_client, wrp_data):
    url = reverse("registry:wrp")
    response = api_client.get(
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
def test_jwks_returns_real_key_when_env_var_set(api_client):
    fake_jwk = {"kty": "EC", "crv": "P-256", "x": "abc", "y": "def"}
    with patch("core.signing.public_key_as_jwk", return_value=fake_jwk):
        response = api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["keys"][0] == fake_jwk


@pytest.mark.django_db
def test_jwks_falls_back_to_placeholder_when_key_not_configured(api_client):
    from core.signing import KeyNotConfiguredError

    with patch("core.signing.public_key_as_jwk", side_effect=KeyNotConfiguredError):
        response = api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["keys"][0]["kid"] == "ms-registry-signing-key-v1"


@pytest.mark.django_db
def test_jwks_returns_500_for_invalid_key_configuration(api_client):
    with patch("core.signing.public_key_as_jwk", side_effect=ValueError("bad key")):
        response = api_client.get(reverse("jwks"))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "detail" in response.data


# =============================================================================
# LOTESEView
# =============================================================================

_SAMPLE_PEM = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIBkTCB+wIJAMockCertificateDataForTestingOnlyAAAAAAAAAAAAAAAAAAAA\n"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
    "-----END CERTIFICATE-----\n"
)


def _make_lote_setup(
    registration_status="active", entity_role=EntityRole.PID_PROVIDER, with_cert=True
):
    from tsl_generator.models import (
        ServiceCertificate,
        TrustService,
        TrustServiceProvider,
        TSLScheme,
    )

    legal_entity = LegalEntityFactory()
    entity = RegisteredEntityFactory(
        legal_entity=legal_entity,
        registration_status=registration_status,
        entity_role=entity_role,
    )
    scheme = TSLScheme.objects.create(name="Test Scheme")
    tsp = TrustServiceProvider.objects.create(legal_entity=legal_entity, scheme=scheme)
    svc = TrustService.objects.create(provider=tsp, is_active=True)
    if with_cert:
        ServiceCertificate.objects.create(service=svc, certificate_pem=_SAMPLE_PEM)
    return entity, svc


@pytest.mark.django_db
def test_lote_se_returns_200(api_client):
    url = reverse("registry:lote-se")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_lote_se_structure(api_client):
    url = reverse("registry:lote-se")
    response = api_client.get(url)
    data = response.data
    assert data["version"] == "1.0"
    assert "schemeInformation" in data
    assert "trustedEntities" in data
    assert data["schemeInformation"]["territory"] == "SE"


@pytest.mark.django_db
def test_lote_se_only_includes_active_entities(api_client):
    _make_lote_setup(registration_status="active")
    _make_lote_setup(registration_status="pending")
    url = reverse("registry:lote-se")
    response = api_client.get(url)
    assert len(response.data["trustedEntities"]) == 1


@pytest.mark.django_db
def test_lote_se_entity_fields(api_client):
    entity, _ = _make_lote_setup()
    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert te["entityId"] == entity.registry_uri
    assert "entityName" in te
    assert "entityStatus" in te
    assert "digitalIdentities" in te


@pytest.mark.django_db
def test_lote_se_digital_identity_from_service_certificate(api_client):
    _make_lote_setup(with_cert=True)
    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert len(te["digitalIdentities"]) == 1
    identity = te["digitalIdentities"][0]
    assert identity["type"] == "x509"
    assert identity["x509Certificate"]


@pytest.mark.django_db
def test_lote_se_no_certificate_gives_empty_digital_identities(api_client):
    _make_lote_setup(with_cert=False)
    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert te["digitalIdentities"] == []


@pytest.mark.django_db
def test_lote_se_entity_type_mapped(api_client):
    _make_lote_setup(entity_role=EntityRole.PID_PROVIDER)
    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert te["entityType"] == "pid-provider"


@pytest.mark.django_db
def test_lote_se_deduplicates_certificates(api_client):
    from tsl_generator.models import (
        ServiceCertificate,
        TrustService,
        TrustServiceProvider,
        TSLScheme,
    )

    legal_entity = LegalEntityFactory()
    RegisteredEntityFactory(legal_entity=legal_entity, registration_status="active")
    scheme = TSLScheme.objects.create(name="Dedup Scheme")
    tsp = TrustServiceProvider.objects.create(legal_entity=legal_entity, scheme=scheme)
    svc1 = TrustService.objects.create(provider=tsp, is_active=True)
    svc2 = TrustService.objects.create(provider=tsp, is_active=True)
    ServiceCertificate.objects.create(service=svc1, certificate_pem=_SAMPLE_PEM)
    ServiceCertificate.objects.create(service=svc2, certificate_pem=_SAMPLE_PEM)

    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert len(te["digitalIdentities"]) == 1


@pytest.mark.django_db
def test_lote_se_inactive_service_certificate_excluded(api_client):
    from tsl_generator.models import (
        ServiceCertificate,
        TrustService,
        TrustServiceProvider,
        TSLScheme,
    )

    legal_entity = LegalEntityFactory()
    RegisteredEntityFactory(legal_entity=legal_entity, registration_status="active")
    scheme = TSLScheme.objects.create(name="Inactive Scheme")
    tsp = TrustServiceProvider.objects.create(legal_entity=legal_entity, scheme=scheme)
    svc = TrustService.objects.create(provider=tsp, is_active=False)
    ServiceCertificate.objects.create(service=svc, certificate_pem=_SAMPLE_PEM)

    response = api_client.get(reverse("registry:lote-se"))
    te = response.data["trustedEntities"][0]
    assert te["digitalIdentities"] == []
