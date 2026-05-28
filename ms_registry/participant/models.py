from core.models import TimestampedModel, UUIDModel
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class ParticipantManager(BaseUserManager):
    def _create_participant(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set.")
        email = self.normalize_email(email)
        participant = self.model(email=email, **extra_fields)
        participant.set_password(password)
        participant.save()
        return participant

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_participant(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_participant(email, password, **extra_fields)

    def normalize_email(self, email):
        return email.lower()

    def get_by_natural_key(self, email):
        return self.get(**{self.model.USERNAME_FIELD: email.lower()})


class Participant(UUIDModel, TimestampedModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField()
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)

    is_staff = models.BooleanField(
        default=False,
        help_text=_("Grants access to the admin site."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Marks the participant as active. "
            "Deselect this instead of deleting the account."
        ),
    )

    USERNAME_FIELD = "email"
    objects = ParticipantManager()

    class Meta:
        constraints = [
            UniqueConstraint(
                Lower("email"),
                name="email_unique_case_insensitive",
            )
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name)
