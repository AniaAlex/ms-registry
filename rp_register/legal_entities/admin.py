"""Admin configuration for Legal Entities app"""

from django.contrib import admin

from .models import (LegalEntity, LegalEntityIdentifier, LegalPerson,
                     NaturalPerson, PhysicalAddress)


class LegalEntityIdentifierInline(admin.TabularInline):
    model = LegalEntityIdentifier
    extra = 1
    autocomplete_fields = ["identifier"]


@admin.register(LegalPerson)
class LegalPersonAdmin(admin.ModelAdmin):
    list_display = ["legal_name", "legal_form", "registration_date", "governing_law"]
    list_filter = ["legal_form"]
    search_fields = ["legal_name"]
    autocomplete_fields = ["governing_law"]
    ordering = ["legal_name"]


@admin.register(NaturalPerson)
class NaturalPersonAdmin(admin.ModelAdmin):
    list_display = ["given_name", "family_name", "date_of_birth", "nationality"]
    list_filter = ["nationality"]
    search_fields = ["given_name", "family_name"]
    ordering = ["family_name", "given_name"]


@admin.register(PhysicalAddress)
class PhysicalAddressAdmin(admin.ModelAdmin):
    list_display = [
        "street_address",
        "locality",
        "postal_code",
        "country_code",
        "address_type",
    ]
    list_filter = ["country_code", "address_type"]
    search_fields = ["street_address", "locality", "postal_code"]
    ordering = ["country_code", "locality"]


@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ["display_name", "entity_type", "email", "phone"]
    list_filter = ["entity_type"]
    search_fields = [
        "legal_person__legal_name",
        "natural_person__given_name",
        "natural_person__family_name",
    ]
    autocomplete_fields = [
        "legal_person",
        "natural_person",
        "primary_identifier",
        "physical_address",
    ]
    inlines = [LegalEntityIdentifierInline]
    ordering = ["entity_type"]

    fieldsets = (
        (None, {"fields": ("entity_type",)}),
        (
            "Legal Person Details",
            {
                "fields": ("legal_person",),
                "classes": ("legal-person-fieldset",),
            },
        ),
        (
            "Natural Person Details",
            {
                "fields": ("natural_person",),
                "classes": ("natural-person-fieldset",),
            },
        ),
        (
            "Contact & Address",
            {"fields": ("physical_address", "email", "phone", "info_uri")},
        ),
        ("Identifiers", {"fields": ("primary_identifier",)}),
    )
