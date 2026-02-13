"""Admin configuration for Registry app"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (EntityEntitlement, EntityServiceDescription,
                     EntitySupportURI, EntityUsesIntermediary,
                     RegisteredEntity, RegisteredEntityPolicy,
                     SupervisoryAuthority)


class EntitySupportURIInline(admin.TabularInline):
    model = EntitySupportURI
    extra = 1


class EntityEntitlementInline(admin.TabularInline):
    model = EntityEntitlement
    extra = 1


class EntityServiceDescriptionInline(admin.TabularInline):
    model = EntityServiceDescription
    extra = 1


class RegisteredEntityPolicyInline(admin.TabularInline):
    model = RegisteredEntityPolicy
    extra = 1
    autocomplete_fields = ["policy"]


class EntityUsesIntermediaryInline(admin.TabularInline):
    model = EntityUsesIntermediary
    fk_name = "registered_entity"
    extra = 1
    autocomplete_fields = ["intermediary"]


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
    autocomplete_fields = ["legal_entity", "supervisory_authority"]
    readonly_fields = ["registered_at"]
    inlines = [
        EntitySupportURIInline,
        EntityEntitlementInline,
        EntityServiceDescriptionInline,
        RegisteredEntityPolicyInline,
        EntityUsesIntermediaryInline,
    ]
    fieldsets = (
        (None, {"fields": ("legal_entity", "entity_role", "trade_name")}),
        ("Entity Flags", {"fields": ("is_psb", "is_intermediary")}),
        (
            "Registration",
            {
                "fields": (
                    "registry_uri",
                    "supervisory_authority",
                    "registration_status",
                    "registered_at",
                )
            },
        ),
        ("Audit", {"fields": ("created_by", "updated_by"), "classes": ("collapse",)}),
    )
