"""
Legal Entity Models for EUDI Wallet Registration System

Contains:
- LegalPerson: Company/organization data
- NaturalPerson: Individual person data
- PhysicalAddress: Address records
- LegalEntity: Unified entity wrapper
- LegalEntityIdentifier: M2M link to identifiers
"""

from core.models import BaseModel, EntityType, Identifier, Law
from django.core.exceptions import ValidationError
from django.db import models


class LegalPerson(BaseModel):
    """Legal Person (External class)"""

    legal_name = models.CharField(max_length=500, help_text="Official legal name")
    legal_form = models.CharField(
        max_length=200, blank=True, null=True, help_text="e.g., LLC, GmbH, AB, etc."
    )
    legal_form_uri = models.URLField(
        max_length=2048, blank=True, null=True, help_text="URI to legal form definition"
    )
    registration_date = models.DateField(blank=True, null=True)
    governing_law = models.ForeignKey(
        Law,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="legal_persons",
    )

    class Meta:
        db_table = "legal_entities_legal_person"
        verbose_name = "Legal Person"
        verbose_name_plural = "Legal Persons"
        indexes = [
            models.Index(fields=["legal_name"]),
        ]

    def __str__(self):
        return self.legal_name


class NaturalPerson(BaseModel):
    """Natural Person (External class - for RP that is a natural person)"""

    given_name = models.CharField(max_length=200)
    family_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(
        max_length=2, blank=True, null=True, help_text="ISO 3166-1 alpha-2"
    )

    class Meta:
        db_table = "legal_entities_natural_person"
        verbose_name = "Natural Person"
        verbose_name_plural = "Natural Persons"

    def __str__(self):
        return f"{self.given_name} {self.family_name}"


class PhysicalAddress(BaseModel):
    """Physical Address"""

    street_address = models.CharField(max_length=500, blank=True, null=True)
    locality = models.CharField(
        max_length=200, blank=True, null=True, help_text="City/Town"
    )
    region = models.CharField(
        max_length=200, blank=True, null=True, help_text="State/Province"
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    address_type = models.CharField(
        max_length=50, default="registered", help_text="registered, operational, etc."
    )

    class Meta:
        db_table = "legal_entities_physical_address"
        verbose_name = "Physical Address"
        verbose_name_plural = "Physical Addresses"

    def __str__(self):
        parts = [self.street_address, self.locality, self.country_code]
        return ", ".join(filter(None, parts))


class LegalEntity(BaseModel):
    """Legal Entity (Superclass)"""

    entity_type = models.CharField(
        max_length=20, choices=EntityType.choices, help_text="Type of legal entity"
    )
    legal_person = models.OneToOneField(
        LegalPerson,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="legal_entity",
    )
    natural_person = models.OneToOneField(
        NaturalPerson,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="legal_entity",
    )
    primary_identifier = models.ForeignKey(
        Identifier,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="primary_for_entities",
    )
    identifiers = models.ManyToManyField(
        Identifier, through="LegalEntityIdentifier", related_name="legal_entities"
    )
    physical_address = models.ForeignKey(
        PhysicalAddress,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="legal_entities",
    )
    email = models.EmailField(max_length=320, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    info_uri = models.URLField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = "legal_entities_legal_entity"
        verbose_name = "Legal Entity"
        verbose_name_plural = "Legal Entities"
        indexes = [
            models.Index(fields=["entity_type"]),
        ]

    def clean(self):
        """Validate entity type matches the related object"""
        if self.entity_type == EntityType.LEGAL_PERSON:
            if not self.legal_person or self.natural_person:
                raise ValidationError(
                    "Legal person entity type requires legal_person and no natural_person"
                )
        elif self.entity_type == EntityType.NATURAL_PERSON:
            if not self.natural_person or self.legal_person:
                raise ValidationError(
                    "Natural person entity type requires natural_person and no legal_person"
                )

    def __str__(self):
        if self.legal_person:
            return self.legal_person.legal_name
        elif self.natural_person:
            return str(self.natural_person)
        return f"Legal Entity {self.id}"

    @property
    def display_name(self):
        """Return the display name based on entity type"""
        if self.legal_person:
            return self.legal_person.legal_name
        elif self.natural_person:
            return f"{self.natural_person.given_name} {self.natural_person.family_name}"
        return str(self.id)


class LegalEntityIdentifier(BaseModel):
    """Link table for Legal Entity to multiple Identifiers"""

    legal_entity = models.ForeignKey(
        LegalEntity, on_delete=models.CASCADE, related_name="entity_identifiers"
    )
    identifier = models.ForeignKey(
        Identifier, on_delete=models.CASCADE, related_name="entity_links"
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "legal_entities_legal_entity_identifier"
        verbose_name = "Legal Entity Identifier"
        verbose_name_plural = "Legal Entity Identifiers"
        unique_together = ["legal_entity", "identifier"]
