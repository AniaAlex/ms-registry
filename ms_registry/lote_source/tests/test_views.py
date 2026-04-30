"""
Tests for lote_source views.

Coverage:
  - HTTP 200 and correct root {"LoTE": ...} envelope
  - ListAndSchemeInformation fields: LoTEType, SchemeTerritory, LoTEVersionIdentifier,
    ListIssueDateTime, NextUpdate, DistributionPoints
  - Filtering: only matching entitlement_type and registration_status appear
  - Entities without a digital identity certificate are excluded from the LoTE
  - TrustedEntityInformation: TEName, TEAddress (never null), TEInformationURI
  - ServiceDigitalIdentity: non-empty X509Certificates present
  - PID profile: ServiceStatus absent
  - PuB-EAA profile: ServiceStatus present, active→granted, revoked→withdrawn
  - ServiceTypeIdentifier correct for each list
  - TEInformationURI fallback to registry_uri when info_uri is blank
  - Multilingual TEName from EntityServiceDescription
  - Empty list is valid (no entities registered yet)
"""

import pytest
from django.urls import reverse
from legal_entities.tests.factories import LegalEntityFactory, PhysicalAddressFactory
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


def _lote(response):
    return response.data["LoTE"]


def _scheme(response):
    return _lote(response)["ListAndSchemeInformation"]


def _entities(response):
    return _lote(response)["TrustedEntitiesList"]


def _make_pid(registration_status="active", **kwargs):
    """Create a PID provider with entitlement and certificate."""
    entity = PIDProviderFactory(registration_status=registration_status, **kwargs)
    add_pid_entitlement(entity)
    add_certificate(entity)
    return entity


def _make_pubeaa(registration_status="active", **kwargs):
    """Create a PuB-EAA provider with entitlement and certificate."""
    entity = PubEAAProviderFactory(registration_status=registration_status, **kwargs)
    add_pubeaa_entitlement(entity)
    add_certificate(entity)
    return entity


# =============================================================================
# PID Providers — ListAndSchemeInformation
# =============================================================================


@pytest.mark.django_db
def test_pid_returns_200(client):
    response = client.get(reverse(PID_URL))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_pid_root_envelope(client):
    response = client.get(reverse(PID_URL))
    assert "LoTE" in response.data
    assert "ListAndSchemeInformation" in _lote(response)
    assert "TrustedEntitiesList" in _lote(response)


@pytest.mark.django_db
def test_pid_scheme_information(client):
    response = client.get(reverse(PID_URL))
    scheme = _scheme(response)
    assert scheme["LoTEType"] == LOTE_TYPE_PID
    assert scheme["LoTEVersionIdentifier"] == 1
    assert scheme["SchemeTerritory"] == "EU"
    assert scheme["ListIssueDateTime"]
    assert scheme["NextUpdate"]
    assert scheme["ListIssueDateTime"] < scheme["NextUpdate"]


@pytest.mark.django_db
def test_pid_distribution_points_contain_filename(client):
    response = client.get(reverse(PID_URL))
    dps = _scheme(response)["DistributionPoints"]
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
    """Entities without a certificate must not appear in LoTE output."""
    entity = PIDProviderFactory()
    add_pid_entitlement(entity)
    # deliberately no add_certificate()

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

    assert "TrustedEntityInformation" in te
    assert "TrustedEntityServices" in te
    info = te["TrustedEntityInformation"]
    assert info["TEName"]
    assert info["TEAddress"] is not None
    assert info["TEInformationURI"]


@pytest.mark.django_db
def test_pid_service_digital_identity_present_and_non_empty(client):
    """ServiceDigitalIdentity must contain at least one X509 certificate."""
    _make_pid()

    response = client.get(reverse(PID_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    sdi = svc_info["ServiceDigitalIdentity"]
    assert sdi
    assert len(sdi["X509Certificates"]) >= 1
    assert sdi["X509Certificates"][0]["val"]


@pytest.mark.django_db
def test_pid_service_status_absent(client):
    """PID profile rule: ServiceStatus must not appear at all."""
    _make_pid()

    response = client.get(reverse(PID_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert "ServiceStatus" not in svc_info


@pytest.mark.django_db
def test_pid_service_type_identifier(client):
    _make_pid()

    response = client.get(reverse(PID_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert svc_info["ServiceTypeIdentifier"] == SVC_TYPE_PID


@pytest.mark.django_db
def test_pid_te_address_never_null(client):
    """TEAddress must not be null — g119612 validate.go rejects null."""
    _make_pid(legal_entity=LegalEntityFactory(physical_address=None))

    response = client.get(reverse(PID_URL))
    addr = _entities(response)[0]["TrustedEntityInformation"]["TEAddress"]
    assert addr is not None
    assert "TEPostalAddress" in addr
    assert "TEElectronicAddress" in addr


@pytest.mark.django_db
def test_pid_te_address_includes_postal_fields(client):
    addr = PhysicalAddressFactory(
        street_address="Main St 1",
        locality="Berlin",
        postal_code="10115",
        country_code="DE",
    )
    _make_pid(legal_entity=LegalEntityFactory(physical_address=addr))

    response = client.get(reverse(PID_URL))
    postal = _entities(response)[0]["TrustedEntityInformation"]["TEAddress"][
        "TEPostalAddress"
    ]
    assert len(postal) == 1
    assert postal[0]["StreetAddress"] == "Main St 1"
    assert postal[0]["Locality"] == "Berlin"
    assert postal[0]["PostalCode"] == "10115"
    assert postal[0]["Country"] == "DE"


@pytest.mark.django_db
def test_pid_te_info_uri_from_legal_entity(client):
    _make_pid(
        legal_entity=LegalEntityFactory(info_uri="https://pid-provider.example.com")
    )

    response = client.get(reverse(PID_URL))
    uri_list = _entities(response)[0]["TrustedEntityInformation"]["TEInformationURI"]
    assert any("pid-provider.example.com" in u["uriValue"] for u in uri_list)


@pytest.mark.django_db
def test_pid_te_info_uri_falls_back_to_registry_uri(client):
    """registry_uri is used as fallback when LegalEntity has no info_uri."""
    le = LegalEntityFactory(info_uri=None, email=None)
    _make_pid(
        legal_entity=le,
        registry_uri="https://registry.example.com/entities/42",
    )

    response = client.get(reverse(PID_URL))
    uri_list = _entities(response)[0]["TrustedEntityInformation"]["TEInformationURI"]
    assert len(uri_list) >= 1
    assert any("registry.example.com" in u["uriValue"] for u in uri_list)


@pytest.mark.django_db
def test_pid_te_name_from_service_description(client):
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
    names = _entities(response)[0]["TrustedEntityInformation"]["TEName"]
    assert {"lang": "en", "value": "English PID Service"} in names
    assert {"lang": "de", "value": "Deutsches PID Service"} in names
    assert not any(n["value"] == "Fallback Name" for n in names)


@pytest.mark.django_db
def test_pid_te_name_fallback_to_trade_name(client):
    _make_pid(trade_name="My PID Corp")

    response = client.get(reverse(PID_URL))
    names = _entities(response)[0]["TrustedEntityInformation"]["TEName"]
    assert names[0]["value"] == "My PID Corp"


# =============================================================================
# PuB-EAA Providers — ListAndSchemeInformation
# =============================================================================


@pytest.mark.django_db
def test_pubeaa_returns_200(client):
    response = client.get(reverse(PUBEAA_URL))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_pubeaa_scheme_information(client):
    response = client.get(reverse(PUBEAA_URL))
    scheme = _scheme(response)
    assert scheme["LoTEType"] == LOTE_TYPE_PUBEAA
    assert scheme["LoTEVersionIdentifier"] == 1
    assert scheme["SchemeTerritory"] == "EU"
    assert scheme["ListIssueDateTime"] < scheme["NextUpdate"]


@pytest.mark.django_db
def test_pubeaa_distribution_points_contain_filename(client):
    response = client.get(reverse(PUBEAA_URL))
    dps = _scheme(response)["DistributionPoints"]
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
    """Entities without a certificate must not appear in LoTE output."""
    entity = PubEAAProviderFactory()
    add_pubeaa_entitlement(entity)
    # deliberately no add_certificate()

    response = client.get(reverse(PUBEAA_URL))
    assert _entities(response) == []


# =============================================================================
# PuB-EAA Providers — ServiceStatus mapping
# =============================================================================


@pytest.mark.django_db
def test_pubeaa_active_maps_to_granted(client):
    _make_pubeaa(registration_status="active")

    response = client.get(reverse(PUBEAA_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert svc_info["ServiceStatus"] == STATUS_GRANTED


@pytest.mark.django_db
def test_pubeaa_revoked_maps_to_withdrawn(client):
    _make_pubeaa(registration_status="revoked")

    response = client.get(reverse(PUBEAA_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert svc_info["ServiceStatus"] == STATUS_WITHDRAWN


@pytest.mark.django_db
def test_pubeaa_service_status_always_present(client):
    """PuB-EAA profile rule: ServiceStatus must always be present."""
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert "ServiceStatus" in svc_info


@pytest.mark.django_db
def test_pubeaa_service_type_identifier(client):
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    assert svc_info["ServiceTypeIdentifier"] == SVC_TYPE_PUBEAA


@pytest.mark.django_db
def test_pubeaa_service_digital_identity_present_and_non_empty(client):
    """ServiceDigitalIdentity must contain at least one X509 certificate."""
    _make_pubeaa()

    response = client.get(reverse(PUBEAA_URL))
    svc_info = _entities(response)[0]["TrustedEntityServices"][0]["ServiceInformation"]
    sdi = svc_info["ServiceDigitalIdentity"]
    assert sdi
    assert len(sdi["X509Certificates"]) >= 1
    assert sdi["X509Certificates"][0]["val"]


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
