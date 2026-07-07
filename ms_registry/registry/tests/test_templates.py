"""
Tests for Registry app HTML form flows.
"""

import pytest
from django.urls import reverse
from legal_entities.tests.factories import LegalEntityFactory
from registry.models import RegisteredEntity, SupervisoryAuthority
from registry.tests.factories import (
    SupervisoryAuthorityFactory,
)
from rest_framework import status

# =============================================================================
# SupervisoryAuthorityFormView — HTML form flow
# =============================================================================


@pytest.mark.django_db
def test_get_supervisory_authority_form(auth_client):
    url = reverse("registry:supervisory-authority-add-form")
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "add_supervisory_authority.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_supervisory_authority_renders_success_template(auth_client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {
        "authority_name": "Swedish IMY",
        "country_code": "SE",
        "email": "imy@imy.se",
    }
    response = auth_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "add_supervisory_authority_success.html" in [
        t.name for t in response.templates
    ]
    assert SupervisoryAuthority.objects.count() == 1


@pytest.mark.django_db
def test_form_post_supervisory_authority_invalid_rerenders_form(auth_client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {"authority_name": "Swedish IMY", "country_code": "SE"}  # missing contact
    response = auth_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "add_supervisory_authority.html" in [t.name for t in response.templates]
    assert SupervisoryAuthority.objects.count() == 0


@pytest.mark.django_db
def test_form_post_supervisory_authority_preserves_form_data_on_error(auth_client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {"authority_name": "Swedish IMY", "country_code": "SE"}  # missing contact
    response = auth_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["form_data"]["country_code"] == "SE"
    assert response.context["errors"] is not None


# =============================================================================
# RegisteredEntityListCreateView — HTML form flow
# =============================================================================


@pytest.mark.django_db
def test_get_register_entity_form(auth_client):
    url = reverse("registry:entity-list-create")
    response = auth_client.get(url, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_200_OK
    assert "register_entity.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_register_entity_renders_success_template(auth_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "trade_name": "Test Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": "https://support.example.com",
        "entitlements": "Service_Provider",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_domain_uri_is_saved(auth_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": "https://support.example.com",
        "entitlements": "Service_Provider",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    entity = RegisteredEntity.objects.get()
    assert entity.domain_uri == "https://service.example.com"


@pytest.mark.django_db
def test_form_post_domain_uri_required(auth_client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "support_uris": "https://support.example.com",
        "entitlements": "Service_Provider",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "domain_uri" in response.context["errors"]
    assert RegisteredEntity.objects.count() == 0


@pytest.mark.django_db
def test_domain_uri_displayed_in_entity_detail(auth_client, authenticated_participant):
    from registry.tests.factories import RegisteredEntityFactory

    # The detail page is scoped to operators, so auth_client's participant must
    # operate the entity.
    entity = RegisteredEntityFactory(
        domain_uri="https://service.example.com",
        operators=[authenticated_participant],
    )
    url = reverse("registry:entity-detail", args=[entity.id])
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert b"https://service.example.com" in response.content


@pytest.mark.django_db
def test_domain_uri_not_displayed_when_absent(auth_client, authenticated_participant):
    from registry.tests.factories import RegisteredEntityFactory

    entity = RegisteredEntityFactory(
        domain_uri=None, operators=[authenticated_participant]
    )
    url = reverse("registry:entity-detail", args=[entity.id])
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert b"Domain URI" not in response.content


@pytest.mark.django_db
def test_form_post_register_entity_invalid_rerenders_form(auth_client):
    url = reverse("registry:entity-list-create")
    data = {"trade_name": "Test Service"}  # missing required fields
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 0


@pytest.mark.django_db
def test_form_post_register_entity_preserves_errors_in_context(auth_client):
    url = reverse("registry:entity-list-create")
    data = {"trade_name": "Test Service"}  # missing required fields
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["errors"] is not None


@pytest.mark.django_db
def test_form_post_inline_legal_entity_creation(auth_client):
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "create_new_legal_entity": "true",
        "le_entity_type": "legal_person",
        "le_legal_name": "NewCorp",
        "le_country_code": "SE",
        "le_email": "contact@newcorp.se",
        "le_identifier_type": "LEI",
        "le_identifier_value": "5493001KSF2Z4PTCYX31",
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "trade_name": "New Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": "https://support.example.com",
        "entitlements": "Service_Provider",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_inline_legal_entity_invalid_rerenders_form(auth_client):
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "create_new_legal_entity": "true",
        "le_entity_type": "legal_person",
        "le_country_code": "SE",  # missing le_legal_name
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "trade_name": "New Service",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert response.context["legal_entity_errors"] is not None


@pytest.mark.django_db
def test_form_post_inline_supervisory_authority_creation(auth_client):
    legal_entity = LegalEntityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "create_new_sa": "true",
        "sa_authority_name": "New DPA",
        "sa_country_code": "DE",
        "sa_email": "dpa@de.de",
        "entity_role": "relying_party",
        "trade_name": "New Service",
        "domain_uri": "https://service.example.com",
        "instance_uri": "https://service.example.com:8008/",
        "support_uris": "https://support.example.com",
        "entitlements": "Service_Provider",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert SupervisoryAuthority.objects.count() == 1


@pytest.mark.django_db
def test_form_post_inline_supervisory_authority_invalid_rerenders_form(auth_client):
    legal_entity = LegalEntityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "create_new_sa": "true",
        "sa_authority_name": "New DPA",
        "sa_country_code": "DE",  # missing contact (email/phone)
        "entity_role": "relying_party",
        "trade_name": "New Service",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert response.context["sa_errors"] is not None


# =============================================================================
# form_data / prefill preservation on validation errors
# =============================================================================


@pytest.mark.django_db
def test_main_form_error_preserves_supervisory_authority_selection(auth_client):
    """form_data carries the submitted SA id so the dropdown stays selected."""
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "supervisory_authority": str(authority.id),
        # deliberately omit entity_role / legal_entity to trigger main-form errors
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["form_data"]["supervisory_authority"] == str(authority.id)


@pytest.mark.django_db
def test_main_form_error_preserves_selected_entitlements(auth_client):
    """selected_entitlements carries the submitted values so checkboxes stay checked."""
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "supervisory_authority": str(authority.id),
        "entitlements": ["Service_Provider", "PID_Provider"],
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Service_Provider" in response.context["selected_entitlements"]
    assert "PID_Provider" in response.context["selected_entitlements"]


@pytest.mark.django_db
def test_inline_sa_error_preserves_sa_form_data(auth_client):
    """When inline SA creation fails, filled SA fields are returned in sa_form_data."""
    legal_entity = LegalEntityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "create_new_sa": "true",
        "sa_authority_name": "New DPA",
        "sa_country_code": "DE",  # missing contact
        "entity_role": "relying_party",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["sa_form_data"]["authority_name"] == "New DPA"
    assert response.context["sa_form_data"]["country_code"] == "DE"


@pytest.mark.django_db
def test_inline_sa_error_preserves_form_data(auth_client):
    """When inline SA creation fails, form_data is also available for other fields."""
    legal_entity = LegalEntityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "create_new_sa": "true",
        "sa_authority_name": "New DPA",
        "sa_country_code": "DE",
        "entity_role": "relying_party",
        "trade_name": "My Service",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["form_data"]["trade_name"] == "My Service"


@pytest.mark.django_db
def test_inline_le_error_preserves_sa_form_data_when_sa_open(auth_client):
    """When LE creation fails and SA inline form was also open, sa_form_data is set."""
    url = reverse("registry:entity-list-create")
    data = {
        "create_new_legal_entity": "true",
        "le_entity_type": "legal_person",
        "le_country_code": "SE",  # missing le_legal_name → LE error
        "create_new_sa": "true",
        "sa_authority_name": "Typed DPA Name",
        "sa_country_code": "SE",
        "entity_role": "relying_party",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["legal_entity_errors"] is not None
    assert response.context["sa_form_data"]["authority_name"] == "Typed DPA Name"
    assert response.context["sa_form_data"]["country_code"] == "SE"


@pytest.mark.django_db
def test_inline_le_error_no_sa_form_data_when_sa_not_open(auth_client):
    """When LE creation fails and SA inline form was NOT open, sa_form_data is empty."""
    url = reverse("registry:entity-list-create")
    data = {
        "create_new_legal_entity": "true",
        "le_entity_type": "legal_person",
        "le_country_code": "SE",  # missing le_legal_name → LE error
        "entity_role": "relying_party",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["legal_entity_errors"] is not None
    assert response.context["sa_form_data"] == {}
