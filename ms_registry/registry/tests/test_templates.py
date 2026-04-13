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
def test_get_supervisory_authority_form(client):
    url = reverse("registry:supervisory-authority-add-form")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "add_supervisory_authority.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_supervisory_authority_renders_success_template(client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {
        "authority_name": "Swedish IMY",
        "country_code": "SE",
        "email": "imy@imy.se",
    }
    response = client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "add_supervisory_authority_success.html" in [
        t.name for t in response.templates
    ]
    assert SupervisoryAuthority.objects.count() == 1


@pytest.mark.django_db
def test_form_post_supervisory_authority_invalid_rerenders_form(client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {"authority_name": "Swedish IMY", "country_code": "SE"}  # missing contact
    response = client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "add_supervisory_authority.html" in [t.name for t in response.templates]
    assert SupervisoryAuthority.objects.count() == 0


@pytest.mark.django_db
def test_form_post_supervisory_authority_preserves_form_data_on_error(client):
    url = reverse("registry:supervisory-authority-add-form")
    data = {"authority_name": "Swedish IMY", "country_code": "SE"}  # missing contact
    response = client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["form_data"]["country_code"] == "SE"
    assert response.context["errors"] is not None


# =============================================================================
# RegisteredEntityListCreateView — HTML form flow
# =============================================================================


@pytest.mark.django_db
def test_get_register_entity_form(client):
    url = reverse("registry:entity-list-create")
    response = client.get(url, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_200_OK
    assert "register_entity.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_register_entity_renders_success_template(client):
    legal_entity = LegalEntityFactory()
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "legal_entity": str(legal_entity.id),
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "trade_name": "Test Service",
    }
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_register_entity_invalid_rerenders_form(client):
    url = reverse("registry:entity-list-create")
    data = {"trade_name": "Test Service"}  # missing required fields
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 0


@pytest.mark.django_db
def test_form_post_register_entity_preserves_errors_in_context(client):
    url = reverse("registry:entity-list-create")
    data = {"trade_name": "Test Service"}  # missing required fields
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["errors"] is not None


@pytest.mark.django_db
def test_form_post_inline_legal_entity_creation(client):
    authority = SupervisoryAuthorityFactory()
    url = reverse("registry:entity-list-create")
    data = {
        "create_new_legal_entity": "true",
        "le_entity_type": "legal_person",
        "le_legal_name": "NewCorp",
        "le_country_code": "SE",
        "supervisory_authority": str(authority.id),
        "entity_role": "relying_party",
        "trade_name": "New Service",
    }
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert RegisteredEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_inline_legal_entity_invalid_rerenders_form(client):
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
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert response.context["legal_entity_errors"] is not None


@pytest.mark.django_db
def test_form_post_inline_supervisory_authority_creation(client):
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
    }
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_201_CREATED
    assert "register_entity_success.html" in [t.name for t in response.templates]
    assert SupervisoryAuthority.objects.count() == 1


@pytest.mark.django_db
def test_form_post_inline_supervisory_authority_invalid_rerenders_form(client):
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
    response = client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "register_entity.html" in [t.name for t in response.templates]
    assert response.context["sa_errors"] is not None
