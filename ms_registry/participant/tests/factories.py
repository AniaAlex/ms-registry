import factory

from .. import models


class ParticipantFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: "%03d@example.com" % n)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "test1234")

    class Meta:
        model = models.Participant
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        if create and results:
            instance.save()

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted is not None:
            obj.groups.set(extracted)
