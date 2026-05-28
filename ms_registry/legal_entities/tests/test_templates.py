"""
Tests for Legal Entities HTML form flow.
"""

import pytest
from django.urls import reverse
from legal_entities.models import LegalEntity
from rest_framework import status


@pytest.mark.django_db
def test_get_legal_entity_create_form(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    response = auth_client.get(url, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_200_OK
    assert "add_legal_entity.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_get_form_passes_serializer_to_context(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    response = auth_client.get(url, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_200_OK
    assert "serializer" in response.context


@pytest.mark.django_db
def test_form_post_legal_person_redirects_to_success(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "Acme",
        "country_code": "SE",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("legal_entities:legal-entity-create-success")
    assert LegalEntity.objects.count() == 1


@pytest.mark.django_db
def test_form_post_natural_person_redirects_to_success(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "given_name": "Anna",
        "family_name": "Svensson",
        "country_code": "SE",
    }
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("legal_entities:legal-entity-create-success")
    assert LegalEntity.objects.count() == 1


@pytest.mark.django_db
def test_success_page_renders(auth_client):
    url = reverse("legal_entities:legal-entity-create-success")
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "add_legal_entity_success.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_form_post_invalid_data_rerenders_form(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "country_code": "SE"}  # missing legal_name
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "add_legal_entity.html" in [t.name for t in response.templates]
    assert LegalEntity.objects.count() == 0


@pytest.mark.django_db
def test_form_post_invalid_passes_serializer_with_errors(auth_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "country_code": "SE"}  # missing legal_name
    response = auth_client.post(url, data, HTTP_ACCEPT="text/html")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "serializer" in response.context
    assert response.context["serializer"].errors
