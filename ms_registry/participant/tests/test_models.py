import pytest

from .. import models


@pytest.mark.django_db
def test_create_participant(db):
    participant = models.Participant.objects.create_user(
        email="cAsIng@exaMple.com", password="Alohomora"
    )
    assert models.Participant.objects.filter(id=participant.id).exists()
    assert participant.email == "casing@example.com"
    assert not participant.is_staff
    assert not participant.is_superuser
    assert participant.check_password("Alohomora")


def test_create_participant_no_email():
    with pytest.raises(ValueError, match="The Email must be set."):
        models.Participant.objects.create_user(None)


@pytest.mark.django_db
def test_create_superuser(db):
    participant = models.Participant.objects.create_superuser(
        email="admin@example.com", password="Alohomora"
    )
    assert participant.is_staff
    assert participant.is_superuser


def test_create_superuser_requires_is_staff():
    with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
        models.Participant.objects.create_superuser(
            email="admin@example.com", password="Alohomora", is_staff=False
        )


def test_create_superuser_requires_is_superuser():
    with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
        models.Participant.objects.create_superuser(
            email="admin@example.com", password="Alohomora", is_superuser=False
        )


def test_normalize_email():
    assert (
        models.Participant.objects.normalize_email("cAsIng@exaMple.com")
        == "casing@example.com"
    )


@pytest.mark.django_db
def test_get_by_natural_key(db):
    participant = models.Participant.objects.create_user(
        email="cAsIng@exaMple.com", password="Alohomora"
    )
    assert (
        models.Participant.objects.get_by_natural_key("cAsIng@exaMple.com")
        == participant
    )


@pytest.mark.django_db
def test_str(db):
    participant = models.Participant.objects.create_user(email="brakebills@nyu.com")
    assert str(participant) == "brakebills@nyu.com"


@pytest.mark.django_db
def test_get_full_name(db):
    participant = models.Participant.objects.create_user(
        email="brakebills@nyu.com", first_name="Quentin", last_name="Coldwater"
    )
    assert participant.get_full_name() == "Quentin Coldwater"
