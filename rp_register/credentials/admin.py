"""Admin configuration for Credentials app"""

from django.contrib import admin

from .models import (Claim, Credential, EntityProvidesAttestation, IntendedUse,
                     IntendedUseCredential, IntendedUsePrivacyPolicy,
                     IntendedUsePurpose)


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


@admin.register(EntityProvidesAttestation)
class EntityProvidesAttestationAdmin(admin.ModelAdmin):
    list_display = ["registered_entity", "credential"]
    search_fields = ["registered_entity__trade_name", "credential__attestation_type"]
    autocomplete_fields = ["registered_entity", "credential"]
