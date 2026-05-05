import factory
from core.models import EntitlementType
from legal_entities.tests.factories import LegalEntityFactory
from registry.models import EntityEntitlement, EntityServiceDescription
from registry.tests.factories import RegisteredEntityFactory
from tsl_generator.models import (
    ServiceCertificate,
    TrustService,
    TrustServiceProvider,
    TSLScheme,
)

# Fake PEM — get_base64_der() only strips headers, so structure is enough.
_FAKE_PEM = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIBmjCCAQOgAwIBAgIUFakeCertForLoteSourceTests1234567890wCgYIKoZI\n"
    "zj0EAwIwDzENMAsGA1UEAxMEdGVzdDAeFw0yNjA0MzAxMjAwMDBaFw0yNzA0MzAx\n"
    "MjAwMDBaMA8xDTALBgNVBAMTBHRlc3QwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNC\n"
    "AARfakePublicKeyDataHereForTestingPurposesOnlyDoNotUseFakeKeyXyzABC\n"
    "-----END CERTIFICATE-----\n"
)


class TSLSchemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TSLScheme

    name = factory.Sequence(lambda n: f"Test Scheme {n}")
    territory = "EU"


class TrustServiceProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustServiceProvider

    scheme = factory.SubFactory(TSLSchemeFactory)
    legal_entity = factory.SubFactory(LegalEntityFactory)
    is_active = True


class TrustServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustService

    provider = factory.SubFactory(TrustServiceProviderFactory)
    is_active = True


class ServiceCertificateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceCertificate

    service = factory.SubFactory(TrustServiceFactory)
    certificate_pem = _FAKE_PEM


class PIDProviderFactory(RegisteredEntityFactory):
    """Active PID Provider."""

    trade_name = factory.Sequence(lambda n: f"PID Provider {n}")
    registration_status = "active"
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/pid-{n}"
    )


class PubEAAProviderFactory(RegisteredEntityFactory):
    """Active PuB-EAA Provider."""

    trade_name = factory.Sequence(lambda n: f"PuB-EAA Provider {n}")
    registration_status = "active"
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/pubeaa-{n}"
    )


class EntityEntitlementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityEntitlement

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    entitlement_type = EntitlementType.PID_PROVIDER
    entitlement_uri = "http://uri.etsi.org/19602/SvcType/PIDProvider"


class EntityServiceDescriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityServiceDescription

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    lang = "en"
    content = factory.Sequence(lambda n: f"Service description {n}")


def add_pid_entitlement(entity):
    return EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.PID_PROVIDER,
        entitlement_uri="http://uri.etsi.org/19602/SvcType/PIDProvider",
    )


def add_pubeaa_entitlement(entity):
    return EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.PUB_EAA_PROVIDER,
        entitlement_uri="http://uri.etsi.org/19602/SvcType/PubEAAProvider",
    )


def add_certificate(entity):
    """Add a ServiceCertificate via the correct chain: TSP → TrustService → cert."""
    tsp = TrustServiceProviderFactory(legal_entity=entity.legal_entity)
    svc = TrustServiceFactory(provider=tsp)
    return ServiceCertificateFactory(service=svc)
