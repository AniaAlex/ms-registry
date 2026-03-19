"""Admin configuration for Credentials app"""

import uuid

from django.contrib import admin

from .models import (
    Claim,
    Credential,
    EntityProvidesAttestation,
    IntendedUse,
    IntendedUseCredential,
    IntendedUsePrivacyPolicy,
    IntendedUsePurpose,
)


def generate_intended_use_identifier(registered_entity):
    """
    Generate a unique intended use identifier.

    Format: {ENTITY_SHORT}-IU-{SEQ}
    Example: BANK-AB-IU-001, SHOP-XY-IU-002

    Falls back to UUID if entity has no trade_name.
    """
    if (
        registered_entity
        and hasattr(registered_entity, "trade_name")
        and registered_entity.trade_name
    ):
        # Create short code from trade name (first 2 words, max 4 chars each)
        words = registered_entity.trade_name.upper().split()[:2]
        short_code = "-".join(w[:4] for w in words)

        # Count existing intended uses for this entity
        existing_count = IntendedUse.objects.filter(
            registered_entity=registered_entity
        ).count()
        seq = existing_count + 1

        return f"{short_code}-IU-{seq:03d}"
    else:
        # Fallback to UUID-based identifier
        return f"IU-{uuid.uuid4().hex[:12].upper()}"


class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 1


class IntendedUsePurposeInline(admin.TabularInline):
    model = IntendedUsePurpose
    extra = 1


class IntendedUsePrivacyPolicyInline(admin.TabularInline):
    model = IntendedUsePrivacyPolicy
    extra = 1
    autocomplete_fields = ["policy"]


class IntendedUseCredentialInline(admin.TabularInline):
    model = IntendedUseCredential
    extra = 1
    autocomplete_fields = ["credential"]


class EntityProvidesAttestationInline(admin.TabularInline):
    model = EntityProvidesAttestation
    extra = 1
    autocomplete_fields = ["credential"]


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ["format", "attestation_type", "catalogue_schema_uri"]
    list_filter = ["format"]
    search_fields = ["attestation_type", "catalogue_schema_uri"]
    inlines = [ClaimInline]
    ordering = ["format", "attestation_type"]


@admin.register(IntendedUse)
class IntendedUseAdmin(admin.ModelAdmin):
    list_display = [
        "intended_use_identifier",
        "registered_entity",
        "validity_start",
        "validity_end",
        "is_active",
    ]
    list_filter = ["validity_start", "validity_end"]
    search_fields = ["intended_use_identifier", "registered_entity__trade_name"]
    autocomplete_fields = ["registered_entity"]
    inlines = [
        IntendedUsePurposeInline,
        IntendedUsePrivacyPolicyInline,
        IntendedUseCredentialInline,
    ]
    ordering = ["-validity_start"]
    readonly_fields = ["intended_use_identifier_display"]

    def intended_use_identifier_display(self, obj):
        """Show how the identifier was generated."""
        if obj.pk:
            return obj.intended_use_identifier
        return "(will be auto-generated on save)"

    intended_use_identifier_display.short_description = "Intended Use Identifier"

    def get_fields(self, request, obj=None):
        """Show identifier as read-only for existing objects."""
        if obj:
            # Editing existing - show identifier but not editable
            return [
                "intended_use_identifier",
                "registered_entity",
                "validity_start",
                "validity_end",
            ]
        else:
            # Creating new - hide identifier field (auto-generated)
            return [
                "registered_entity",
                "validity_start",
                "validity_end",
            ]

    def get_readonly_fields(self, request, obj=None):
        """Make identifier read-only for existing objects."""
        if obj:
            return ["intended_use_identifier"]
        return []

    def save_model(self, request, obj, form, change):
        """Auto-generate intended_use_identifier on create."""
        if not change and not obj.intended_use_identifier:
            obj.intended_use_identifier = generate_intended_use_identifier(
                obj.registered_entity
            )
        super().save_model(request, obj, form, change)


@admin.register(EntityProvidesAttestation)
class EntityProvidesAttestationAdmin(admin.ModelAdmin):
    list_display = ["registered_entity", "credential"]
    search_fields = ["registered_entity__trade_name", "credential__attestation_type"]
    autocomplete_fields = ["registered_entity", "credential"]
