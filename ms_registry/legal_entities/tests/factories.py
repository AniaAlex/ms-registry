import factory
from legal_entities.models import LegalEntity, LegalPerson, PhysicalAddress


class PhysicalAddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PhysicalAddress

    country_code = "SE"


class LegalPersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalPerson

    legal_name = factory.Sequence(lambda n: f"Company {n}")


class LegalEntityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalEntity

    entity_type = "legal_person"
    legal_person = factory.SubFactory(LegalPersonFactory)
    physical_address = factory.SubFactory(PhysicalAddressFactory)
