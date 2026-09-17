"""
Tests for the Trust Service form's RegisteredEntity prefill.

The prefill returns an entity's registration details and its signing
certificate PEM, so it must be scoped to the entity's operators the same way
registry's EntityDetailView is.
"""

import pytest
from core.models import EntitlementType
from django.urls import reverse
from django.utils import timezone
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


@pytest.mark.django_db
def test_prefill_404s_for_entitlement_the_entity_does_not_hold(
    auth_client, authenticated_participant
):
    # QEAA_Provider is publishable in the TL, so it survives the map lookup in
    # build_trust_service_prefill - only the entity's own entitlements rule it
    # out. Without that check the form prefills a qualified service type for a
    # non-qualified issuer, with an empty certificate box and no warning.
    entity, _ = _eaa_issuer_entity(operators=[authenticated_participant])
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.QEAA_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_prefill_404s_for_entitlement_not_published_in_the_tl(
    auth_client, authenticated_participant
):
    # PID_Provider is published in its own LoTE, not the TL, so it has no
    # entry in ENTITLEMENT_TO_SERVICE_TYPE.
    entity, _ = _eaa_issuer_entity(operators=[authenticated_participant])
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.PID_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_prefill_404s_for_malformed_entity_id(auth_client):
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(url, {"registered_entity": "not-a-uuid"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_prefill_redirects_to_signing_page_when_certificate_is_missing(
    auth_client, authenticated_participant
):
    # Entitled, but nothing to publish yet: registry's entity page refuses to
    # link here at all in this state, so the form must not offer a prefill
    # with an empty certificate box either.
    entity = RegisteredEntityFactory(
        trade_name="EAA Issuer",
        operators=[authenticated_participant],
    )
    EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.NON_Q_EAA_PROVIDER,
        entitlement_uri="http://data.europa.eu/eudi/entitlement/non_q_EAA_Provider",
    )
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.NON_Q_EAA_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse(
        "certificates:signing-page", kwargs={"entity_id": entity.id}
    )


@pytest.mark.django_db
def test_prefill_redirects_to_signing_page_when_certificate_is_revoked(
    auth_client, authenticated_participant
):
    entity, certificate = _eaa_issuer_entity(operators=[authenticated_participant])
    certificate.revoked_at = timezone.now()
    certificate.is_current = False
    certificate.save(update_fields=["revoked_at", "is_current"])
    url = reverse("tsl_generator:service-add-form")

    response = auth_client.get(
        url,
        {
            "registered_entity": str(entity.id),
            "entitlement_type": EntitlementType.NON_Q_EAA_PROVIDER,
        },
    )

    assert response.status_code == status.HTTP_302_FOUND
