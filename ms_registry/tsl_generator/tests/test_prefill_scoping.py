"""
Tests for the Trust Service form's RegisteredEntity prefill.

The prefill returns an entity's registration details and its signing
certificate PEM, so it must be scoped to the entity's operators the same way
registry's EntityDetailView is.
"""

import pytest
from core.models import EntitlementType
from django.urls import reverse
from lote_source.tests.factories import (
    EntityEntitlementFactory,
    add_certificate,
)
from registry.tests.factories import RegisteredEntityFactory
from rest_framework import status


def _eaa_issuer_entity(operators=None):
    entity = RegisteredEntityFactory(
        trade_name="EAA Issuer",
        operators=operators or [],
    )
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.NON_Q_EAA_PROVIDER,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/non_q_EAA_Provider",
    )
    (certificate,) = add_certificate(entity)
    return entity, certificate


@pytest.mark.django_db
def test_prefill_returns_entity_data_for_its_operator(
    auth_client, authenticated_participant
):
    entity, certificate = _eaa_issuer_entity(operators=[authenticated_participant])
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.NON_Q_EAA_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    initial = response.context["initial"]
    assert initial["provider_name"] == entity.display_name
    assert initial["certificate_pem"] == certificate.certificate_pem


@pytest.mark.django_db
def test_prefill_404s_for_entity_the_requester_does_not_operate(auth_client):
    # Operated by someone else — the requester only knows (or guesses) the ID.
    entity, certificate = _eaa_issuer_entity()
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.NON_Q_EAA_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert certificate.certificate_pem.encode() not in response.content


@pytest.mark.django_db
def test_form_without_registered_entity_renders_blank(auth_client):
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.context["initial"] is None
