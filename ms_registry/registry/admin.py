"""Admin configuration for Registry app"""

from credentials.models import (
    EntityProvidesAttestation,
    IntendedUse,
)
from django.contrib import admin

from .models import (
    EntityEntitlement,
    EntityServiceDescription,
    EntitySupportURI,
    EntityUsesIntermediary,
    RegisteredEntity,
    RegisteredEntityPolicy,
    SupervisoryAuthority,
)


class EntitySupportURIInline(admin.TabularInline):
    model = EntitySupportURI
    extra = 0


class EntityEntitlementInline(admin.TabularInline):
    model = EntityEntitlement
    extra = 0


class EntityServiceDescriptionInline(admin.TabularInline):
    model = EntityServiceDescription
    extra = 0


class RegisteredEntityPolicyInline(admin.TabularInline):
    model = RegisteredEntityPolicy
    extra = 0
    autocomplete_fields = ["policy"]


class EntityUsesIntermediaryInline(admin.TabularInline):
    model = EntityUsesIntermediary
    fk_name = "registered_entity"
    extra = 0
    autocomplete_fields = ["intermediary"]


# =============================================================================
# Inlines from credentials app for RegisteredEntity
# =============================================================================


class IntendedUseInline(admin.TabularInline):
    model = IntendedUse
    extra = 0
    show_change_link = True


class ProvidesAttestationsInline(admin.TabularInline):
    """Inline for attestations provided by issuers"""

    model = EntityProvidesAttestation
    extra = 0
    autocomplete_fields = ["credential"]
    verbose_name = "Provided Attestation"
    verbose_name_plural = "Provided Attestations (for Issuers)"


@admin.register(SupervisoryAuthority)
class SupervisoryAuthorityAdmin(admin.ModelAdmin):
    list_display = ["authority_name", "country_code", "email", "phone"]
    list_filter = ["country_code"]
    search_fields = ["authority_name", "email"]
    autocomplete_fields = ["legal_entity"]
    ordering = ["country_code", "authority_name"]


@admin.register(RegisteredEntity)
class RegisteredEntityAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "entity_role",
        "registration_status",
        "is_psb",
        "is_intermediary",
        "registered_at",
    ]
    list_filter = ["entity_role", "registration_status", "is_psb", "is_intermediary"]
    search_fields = ["trade_name", "legal_entity__legal_person__legal_name"]
    autocomplete_fields = ["legal_entity", "supervisory_authority", "participant"]
    readonly_fields = ["registered_at"]
    inlines = [
        EntitySupportURIInline,
        EntityEntitlementInline,
        EntityServiceDescriptionInline,
        RegisteredEntityPolicyInline,
        EntityUsesIntermediaryInline,
        IntendedUseInline,
        ProvidesAttestationsInline,
    ]
    fieldsets = (
        (
            None,
            {"fields": ("legal_entity", "participant", "entity_role", "trade_name")},
        ),
        ("Entity Flags", {"fields": ("is_psb", "is_intermediary")}),
        (
            "Registration",
            {
                "fields": (
                    "domain_uri",
                    "instance_uri",
                    "registry_uri",
                    "supervisory_authority",
                    "registration_status",
                    "registered_at",
                )
            },
        ),
        ("Audit", {"fields": ("created_by", "updated_by"), "classes": ("collapse",)}),
    )
