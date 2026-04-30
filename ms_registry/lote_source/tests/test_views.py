"""
Tests for lote_source views.

Coverage:
  - HTTP 200 and correct root keys: version, schemeInformation, trustedEntities
  - schemeInformation fields: schemeType, territory, sequenceNumber,
    issueDate, nextUpdate, distributionPoints
  - Filtering: only matching entitlement_type and registration_status appear
  - Entities without a digital identity certificate are excluded from the LoTE
  - entityName, entityId, entityStatus, digitalIdentities, services present
  - digitalIdentities: x509Certificate non-empty base64
  - informationURIs: fallback to registry_uri when info_uri is blank
  - Multilingual entityName from EntityServiceDescription
  - PID profile: serviceStatus absent from service
  - PuB-EAA profile: serviceStatus present, active→granted, revoked→withdrawn
  - serviceType correct for each list
  - Empty list is valid (no entities registered yet)
"""

import pytest
from django.urls import reverse
from legal_entities.tests.factories import LegalEntityFactory
from rest_framework import status
from rest_framework.test import APIClient

from .factories import (
    EntityServiceDescriptionFactory,
    PIDProviderFactory,
    PubEAAProviderFactory,
    add_certificate,
    add_pid_entitlement,
    add_pubeaa_entitlement,
)

PID_URL = "lote_source:pid-providers"
PUBEAA_URL = "lote_source:pubeaa-providers"

STATUS_GRANTED = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
STATUS_WITHDRAWN = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/withdrawn"
LOTE_TYPE_PID = "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"
LOTE_TYPE_PUBEAA = "http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"
SVC_TYPE_PID = "http://uri.etsi.org/19602/SvcType/PIDProvider"
SVC_TYPE_PUBEAA = "http://uri.etsi.org/19602/SvcType/PubEAAProvider"


@pytest.fixture
def client():
    return APIClient()


def _scheme(response):
    return response.data["schemeInformation"]


def _entities(response):
    return response.data["trustedEntities"]


def _make_pid(registration_status="active", **kwargs):
    entity = PIDProviderFactory(registration_status=registration_status, **kwargs)
    add_pid_entitlement(entity)
    add_certificate(entity)
    return entity


def _make_pubeaa(registration_status="active", **kwargs):
    entity = PubEAAProviderFactory(registration_status=registration_status, **kwargs)
    add_pubeaa_entitlement(entity)
    add_certificate(entity)
    return entity


# =============================================================================
# PID Providers — schemeInformation
# =============================================================================


@pytest.mark.django_db
def test_pid_returns_200(client):
    response = client.get(reverse(PID_URL))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_pid_root_keys(client):
    response = client.get(reverse(PID_URL))
    assert "version" in response.data
    assert "schemeInformation" in response.data
    assert "trustedEntities" in response.data


@pytest.mark.django_db
def test_pid_scheme_information(client):
    response = client.get(reverse(PID_URL))
    scheme = _scheme(response)
    assert scheme["schemeType"] == LOTE_TYPE_PID
    assert response.data["version"] == "1"
    assert scheme["territory"] == "EU"
    assert scheme["issueDate"]
    assert scheme["nextUpdate"]
    assert scheme["issueDate"] < scheme["nextUpdate"]
    assert scheme["sequenceNumber"] >= 1


@pytest.mark.django_db
def test_pid_distribution_points_contain_filename(client):
    response = client.get(reverse(PID_URL))
    dps = _scheme(response)["distributionPoints"]
    assert len(dps) == 1
    assert "pid_providers.json" in dps[0]


@pytest.mark.django_db
def test_pid_empty_list_is_valid(client):
    response = client.get(reverse(PID_URL))
    assert response.status_code == status.HTTP_200_OK
    assert _entities(response) == []


# =============================================================================
# PID Providers — entity filtering
# =============================================================================


@pytest.mark.django_db
def test_pid_includes_only_active_pid_providers(client):
    _make_pid()

    # Wrong entitlement — excluded
    other = PIDProviderFactory()
    add_pubeaa_entitlement(other)
    add_certificate(other)

    # Wrong status — excluded
    pending = PIDProviderFactory(registration_status="pending")
    add_pid_entitlement(pending)
    add_certificate(pending)

    response = client.get(reverse(PID_URL))
    assert len(_entities(response)) == 1


@pytest.mark.django_db
def test_pid_excludes_revoked(client):
    _make_pid(registration_status="revoked")
    response = client.get(reverse(PID_URL))
    assert _entities(response) == []


@pytest.mark.django_db
def test_pid_excludes_entity_without_certificate(client):
    entity = PIDProviderFactory()
    add_pid_entitlement(entity)

    response = client.get(reverse(PID_URL))
    assert _entities(response) == []


# =============================================================================
# PID Providers — entity structure
# =============================================================================


@pytest.mark.django_db
def test_pid_entity_has_required_fields(client):
    _make_pid(legal_entity=LegalEntityFactory(info_uri="https://example.com"))

    response = client.get(reverse(PID_URL))
    te = _entities(response)[0]

    assert te["entityId"]
    assert te["entityName"]
    assert te["entityStatus"]
    assert "digitalIdentities" in te
    assert "services" in te


@pytest.mark.django_db
def test_pid_digital_identity_present_and_non_empty(client):
    _make_pid()

    response = client.get(reverse(PID_URL))
    di = _entities(response)[0]["digitalIdentities"]
    assert len(di) >= 1
    assert di[0]["type"] == "x509"
    assert di[0]["x509Certificate"]


@pytest.mark.django_db
def test_pid_service_status_absent(client):
    """PID profile rule: serviceStatus must not appear in the service."""
    _make_pid()

    response = client.get(reverse(PID_URL))
    svc = _entities(response)[0]["services"][0]
    assert "serviceStatus" not in svc


@pytest.mark.django_db
def test_pid_service_type(client):
    _make_pid()

    response = client.get(reverse(PID_URL))
    svc = _entities(response)[0]["services"][0]
    assert svc["serviceType"] == SVC_TYPE_PID


@pytest.mark.django_db
def test_pid_info_uri_from_legal_entity(client):
    _make_pid(
        legal_entity=LegalEntityFactory(info_uri="https://pid-provider.example.com")
    )

    response = client.get(reverse(PID_URL))
    uris = _entities(response)[0]["informationURIs"]
    assert any("pid-provider.example.com" in u["uri"] for u in uris)


@pytest.mark.django_db
def test_pid_info_uri_falls_back_to_registry_uri(client):
    le = LegalEntityFactory(info_uri=None, email=None)
    _make_pid(
        legal_entity=le,
        registry_uri="https://registry.example.com/entities/42",
    )

    response = client.get(reverse(PID_URL))
    uris = _entities(response)[0]["informationURIs"]
    assert len(uris) >= 1
    assert any("registry.example.com" in u["uri"] for u in uris)


@pytest.mark.django_db
def test_pid_name_from_service_description(client):
    entity = PIDProviderFactory(trade_name="Fallback Name")
    add_pid_entitlement(entity)
    add_certificate(entity)
    EntityServiceDescriptionFactory(
        registered_entity=entity, lang="en", content="English PID Service"
    )
    EntityServiceDescriptionFactory(
        registered_entity=entity, lang="de", content="Deutsches PID Service"
    )

    response = client.get(reverse(PID_URL))
    names = _entities(response)[0]["entityName"]
    assert {"language": "en", "value": "English PID Service"} in names
    assert {"language": "de", "value": "Deutsches PID Service"} in names
    assert not any(n["value"] == "Fallback Name" for n in names)


@pytest.mark.django_db
def test_pid_name_fallback_to_trade_name(client):
    _make_pid(trade_name="My PID Corp")

    response = client.get(reverse(PID_URL))
    names = _entities(response)[0]["entityName"]
    assert names[0]["value"] == "My PID Corp"


# =============================================================================
# PuB-EAA Providers — schemeInformation
# =============================================================================


@pytest.mark.django_db
def test_pubeaa_returns_200(client):
    response = client.get(reverse(PUBEAA_URL))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_pubeaa_scheme_information(client):
    response = client.get(reverse(PUBEAA_URL))
    scheme = _scheme(response)
    assert scheme["schemeType"] == LOTE_TYPE_PUBEAA
    assert scheme["territory"] == "EU"
    assert scheme["issueDate"] < scheme["nextUpdate"]


@pytest.mark.django_db
def test_pubeaa_distribution_points_contain_filename(client):
    response = client.get(reverse(PUBEAA_URL))
    dps = _scheme(response)["distributionPoints"]
    assert len(dps) == 1
    assert "pubeaa_providers.json" in dps[0]


# =============================================================================
# PuB-EAA Providers — entity filtering
# =============================================================================


@pytest.mark.django_db
def test_pubeaa_includes_active_and_revoked(client):
    _make_pubeaa(registration_status="active")
    _make_pubeaa(registration_status="revoked")

    response = client.get(reverse(PUBEAA_URL))
    assert len(_entities(response)) == 2


@pytest.mark.django_db
def test_pubeaa_excludes_pending(client):
    _make_pubeaa(registration_status="pending")
    response = client.get(reverse(PUBEAA_URL))
    assert _entities(response) == []


@pytest.mark.django_db
def test_pubeaa_excludes_wrong_entitlement(client):
    entity = PubEAAProviderFactory()
    add_pid_entitlement(entity)
    add_certificate(entity)
    response = client.get(reverse(PUBEAA_URL))
    assert _entities(response) == []


@pytest.mark.django_db
def test_pubeaa_excludes_entity_without_certificate(client):
    entity = PubEAAProviderFactory()
    add_pubeaa_entitlement(entity)

    response = client.get(reverse(PUBEAA_URL))
    assert _entities(response) == []


# =============================================================================
# PuB-EAA Providers — ServiceStatus mapping
# =============================================================================


@pytest.mark.django_db
def test_pubeaa_active_maps_to_granted(client):
    _make_pubeaa(registration_status="active")

    response = client.get(reverse(PUBEAA_URL))
    svc = _entities(response)[0]["services"][0]
    assert svc["serviceStatus"] == STATUS_GRANTED


@pytest.mark.django_db
def test_pubeaa_revoked_maps_to_withdrawn(client):
    _make_pubeaa(registration_status="revoked")

    response = client.get(reverse(PUBEAA_URL))
    svc = _entities(response)[0]["services"][0]
    assert svc["serviceStatus"] == STATUS_WITHDRAWN


@pytest.mark.django_db
def test_pubeaa_service_status_always_present(client):
    """PuB-EAA profile rule: serviceStatus must always be present."""
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    svc = _entities(response)[0]["services"][0]
    assert "serviceStatus" in svc


@pytest.mark.django_db
def test_pubeaa_service_type(client):
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    svc = _entities(response)[0]["services"][0]
    assert svc["serviceType"] == SVC_TYPE_PUBEAA


@pytest.mark.django_db
def test_pubeaa_digital_identity_present_and_non_empty(client):
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    di = _entities(response)[0]["digitalIdentities"]
    assert len(di) >= 1
    assert di[0]["type"] == "x509"
    assert di[0]["x509Certificate"]


# =============================================================================
# Cross-list isolation
# =============================================================================


@pytest.mark.django_db
def test_pid_entity_does_not_appear_in_pubeaa_list(client):
    _make_pid()
    response = client.get(reverse(PUBEAA_URL))
    assert _entities(response) == []


@pytest.mark.django_db
def test_pubeaa_entity_does_not_appear_in_pid_list(client):
    _make_pubeaa()
    response = client.get(reverse(PID_URL))
    assert _entities(response) == []


@pytest.mark.django_db
def test_entity_with_both_entitlements_appears_in_both_lists(client):
    le = LegalEntityFactory(info_uri="https://dual.example.com")
    entity = PIDProviderFactory(legal_entity=le, registration_status="active")
    add_pid_entitlement(entity)
    add_pubeaa_entitlement(entity)
    add_certificate(entity)

    pid_response = client.get(reverse(PID_URL))
    pubeaa_response = client.get(reverse(PUBEAA_URL))
    assert len(_entities(pid_response)) == 1
    assert len(_entities(pubeaa_response)) == 1
