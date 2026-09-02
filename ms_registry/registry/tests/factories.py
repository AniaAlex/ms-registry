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
        skip_postgeneration_save = True

    legal_entity = factory.SubFactory(LegalEntityFactory)
    entity_role = EntityRole.RELYING_PARTY
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/{n}"
    )
    domain_uri = factory.Sequence(lambda n: f"https://service{n}.example.com")
    instance_uri = factory.Sequence(
        lambda n: f"https://service{n}.example.com:{8000 + n}/"
    )
    supervisory_authority = factory.SubFactory(SupervisoryAuthorityFactory)

    @factory.post_generation
    def operators(self, create, extracted, **kwargs):
        """Attach operators to the M2M.

        Pass ``operators=[user, ...]`` to set specific operators; otherwise a
        fresh Participant is created so the entity always has at least one
        operator (mirroring the "never empty" invariant enforced on creation).
        """
        if not create:
            return
        if extracted:
            for operator in extracted:
                self.operators.add(operator)
        else:
            self.operators.add(ParticipantFactory())


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
