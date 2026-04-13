"""
Tests for Legal Entities HTML form flow.
"""

import pytest
from django.urls import reverse
from legal_entities.models import LegalEntity
from rest_framework import status


@pytest.mark.django_db
def test_get_legal_entity_create_form(client):
    url = reverse("legal_entities:legal-entity-create")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "add_legal_entity.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_legal_person_renders_success_template(client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "Acme",
        "country_code": "SE",
    }
    response = client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "add_legal_entity_success.html" in [t.name for t in response.templates]
    assert LegalEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_natural_person_renders_success_template(client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "given_name": "Anna",
        "family_name": "Svensson",
        "country_code": "SE",
    }
    response = client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "add_legal_entity_success.html" in [t.name for t in response.templates]
    assert LegalEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_invalid_data_rerenders_form(client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "country_code": "SE"}  # missing legal_name
    response = client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "add_legal_entity.html" in [t.name for t in response.templates]
    assert LegalEntity.objects.count() == 0


@pytest.mark.django_db
def test_form_post_preserves_form_data_on_error(client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "country_code": "SE"}  # missing legal_name
    response = client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.context["form_data"]["country_code"] == "SE"
    assert response.context["errors"] is not None
