"""
Tests for Legal Entities app endpoints.
"""

import pytest
from django.urls import reverse
from legal_entities.models import LegalEntity
from legal_entities.tests.factories import LegalEntityFactory
from rest_framework import status

# =============================================================================
# LegalEntityCreateView — GET (form) & POST (create)
# =============================================================================


@pytest.mark.django_db
def test_create_legal_person_entity(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "Acme",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert LegalEntity.objects.count() == 1
    entity = LegalEntity.objects.first()
    assert entity.entity_type == "legal_person"
    assert entity.legal_person.legal_name == "Acme"


@pytest.mark.django_db
def test_create_legal_person_entity_multi_word_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "Acme Corporation",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    entity = LegalEntity.objects.first()
    assert entity.legal_person.legal_name == "Acme Corporation"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "legal_name",
    ["AT&T", "3M", "Smith & Co.", "Acme Corp.", "Volvo Group AB"],
)
def test_create_legal_person_entity_punctuated_name(
    authenticated_api_client, legal_name
):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": legal_name,
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert LegalEntity.objects.first().legal_person.legal_name == legal_name


@pytest.mark.django_db
def test_create_natural_person_entity(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "given_name": "Anna",
        "family_name": "Svensson",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert LegalEntity.objects.count() == 1
    entity = LegalEntity.objects.first()
    assert entity.entity_type == "natural_person"
    assert entity.natural_person.given_name == "Anna"


@pytest.mark.django_db
def test_create_legal_entity_with_identifier(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "TestCorp",
        "country_code": "DE",
        "identifier_type": "LEI",
        "identifier_value": "ABCDE12345",
        "issuing_authority": "GLEIF",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    entity = LegalEntity.objects.first()
    assert entity.primary_identifier is not None
    assert entity.primary_identifier.identifier_value == "ABCDE12345"


@pytest.mark.django_db
def test_create_legal_person_missing_legal_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "country_code": "SE"}
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_natural_person_missing_given_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "family_name": "Svensson",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_natural_person_missing_family_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "given_name": "Anna",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_legal_entity_missing_country_code(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "legal_person", "legal_name": "Acme"}
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_legal_entity_invalid_legal_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "legal_person",
        "legal_name": "Acme @ Corp!",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_legal_entity_invalid_given_name(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {
        "entity_type": "natural_person",
        "given_name": "Anna1",
        "family_name": "Svensson",
        "country_code": "SE",
    }
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_legal_entity_invalid_entity_type(authenticated_api_client):
    url = reverse("legal_entities:legal-entity-create")
    data = {"entity_type": "corporation", "country_code": "SE"}
    response = authenticated_api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# LegalEntityDetailView — GET, PATCH, DELETE
# =============================================================================


@pytest.mark.django_db
def test_get_legal_entity_detail(authenticated_api_client):
    entity = LegalEntityFactory()
    url = reverse("legal_entities:legal-entity-detail", args=[entity.id])
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert str(response.data["id"]) == str(entity.id)
    assert response.data["entity_type"] == entity.entity_type


@pytest.mark.django_db
def test_get_nonexistent_legal_entity(authenticated_api_client):
    import uuid

    url = reverse("legal_entities:legal-entity-detail", args=[uuid.uuid4()])
    response = authenticated_api_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_legal_entity(authenticated_api_client):
    entity = LegalEntityFactory()
    url = reverse("legal_entities:legal-entity-detail", args=[entity.id])
    response = authenticated_api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert LegalEntity.objects.count() == 0
