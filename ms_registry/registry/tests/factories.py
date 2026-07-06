import factory
from core.models import EntitlementType, EntityRole
from legal_entities.tests.factories import LegalEntityFactory
from participant.tests.factories import ParticipantFactory
from registry.models import (
    EntityEntitlement,
    EntitySupportURI,
    RegisteredEntity,
    SupervisoryAuthority,
)


class SupervisoryAuthorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupervisoryAuthority

    authority_name = factory.Sequence(lambda n: f"DPA {n}")
    country_code = "SE"
    email = factory.Sequence(lambda n: f"dpa{n}@test.se")


class RegisteredEntityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegisteredEntity

    legal_entity = factory.SubFactory(LegalEntityFactory)
    participant = factory.SubFactory(ParticipantFactory)
    entity_role = EntityRole.RELYING_PARTY
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/{n}"
    )
    domain_uri = factory.Sequence(lambda n: f"https://service{n}.example.com")
    instance_uri = factory.Sequence(
        lambda n: f"https://service{n}.example.com:{8000 + n}/"
    )
    supervisory_authority = factory.SubFactory(SupervisoryAuthorityFactory)


class EntityEntitlementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityEntitlement

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    entitlement_uri = "http://data.europa.eu/eudi/entitlement/Service_Provider"
    entitlement_type = EntitlementType.SERVICE_PROVIDER


class EntitySupportURIFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntitySupportURI

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    support_uri = factory.Sequence(lambda n: f"https://support{n}.example.com")
