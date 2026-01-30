"""
EUDI Wallet Relying Party Registration - Django Admin Configuration
Provides comprehensive admin interface for managing Wallet Relying Parties
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AuditLog,
    Claim,
    Credential,
    Identifier,
    IntendedUse,
    IntendedUseCredential,
    IntendedUsePrivacyPolicy,
    IntendedUsePurpose,
    Law,
    LegalEntity,
    LegalEntityIdentifier,
    LegalPerson,
    NaturalPerson,
    PhysicalAddress,
    Policy,
    SupervisoryAuthority,
    WalletRelyingParty,
    WRPAccessCertificate,
    WRPEntitlement,
    WRPPolicy,
    WRPProvidesAttestation,
    WRPRegistrationCertificate,
    WRPServiceDescription,
    WRPSupportURI,
    WRPUsesIntermediary,
)

# ============================================================================
# INLINE ADMINS
# ============================================================================


class LegalEntityIdentifierInline(admin.TabularInline):
    model = LegalEntityIdentifier
    extra = 1
    autocomplete_fields = ["identifier"]


class WRPSupportURIInline(admin.TabularInline):
    model = WRPSupportURI
    extra = 1


class WRPEntitlementInline(admin.TabularInline):
    model = WRPEntitlement
    extra = 1


class WRPServiceDescriptionInline(admin.TabularInline):
    model = WRPServiceDescription
    extra = 1


class WRPPolicyInline(admin.TabularInline):
    model = WRPPolicy
    extra = 1
    autocomplete_fields = ["policy"]


class WRPProvidesAttestationInline(admin.TabularInline):
    model = WRPProvidesAttestation
    extra = 1
    autocomplete_fields = ["credential"]


class WRPUsesIntermediaryInline(admin.TabularInline):
    model = WRPUsesIntermediary
    fk_name = "wallet_relying_party"
    extra = 1
    autocomplete_fields = ["intermediary"]
    readonly_fields = [
        "intermediary_identifier",
        "intermediary_trade_name",
        "intermediary_registry_uri",
    ]


class WRPAccessCertificateInline(admin.TabularInline):
    model = WRPAccessCertificate
    extra = 0
    readonly_fields = [
        "certificate_serial",
        "certificate_fingerprint_sha256",
        "not_before",
        "not_after",
        "is_current",
    ]
    fields = [
        "certificate_serial",
        "certificate_fingerprint_sha256",
        "not_before",
        "not_after",
        "is_current",
    ]


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


# ============================================================================
# MODEL ADMINS
# ============================================================================


@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ["law_name", "law_country_code", "law_uri"]
    list_filter = ["law_country_code"]
    search_fields = ["law_name", "law_uri"]
    ordering = ["law_name"]


@admin.register(Identifier)
class IdentifierAdmin(admin.ModelAdmin):
    list_display = ["identifier_type", "identifier_value", "country_code", "is_primary"]
    list_filter = ["identifier_type", "country_code", "is_primary"]
    search_fields = ["identifier_value", "issuing_authority"]
    ordering = ["identifier_type", "identifier_value"]


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["policy_type", "policy_uri", "locale", "version", "effective_date"]
    list_filter = ["policy_type", "locale"]
    search_fields = ["policy_uri"]
    ordering = ["policy_type", "effective_date"]


@admin.register(LegalPerson)
class LegalPersonAdmin(admin.ModelAdmin):
    list_display = ["legal_name", "legal_form", "registration_date", "governing_law"]
    list_filter = ["legal_form"]
    search_fields = ["legal_name"]
    autocomplete_fields = ["governing_law"]
    ordering = ["legal_name"]


@admin.register(NaturalPerson)
class NaturalPersonAdmin(admin.ModelAdmin):
    list_display = ["given_name", "family_name", "nationality", "date_of_birth"]
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
    list_display = ["display_name", "entity_type", "primary_identifier", "email"]
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
        ("Entity Type", {"fields": ("entity_type",)}),
        (
            "Legal Person Details",
            {"fields": ("legal_person",), "classes": ("collapse",)},
        ),
        (
            "Natural Person Details",
            {"fields": ("natural_person",), "classes": ("collapse",)},
        ),
        ("Identifiers", {"fields": ("primary_identifier",)}),
        (
            "Contact Information",
            {"fields": ("physical_address", "email", "phone", "info_uri")},
        ),
    )


@admin.register(SupervisoryAuthority)
class SupervisoryAuthorityAdmin(admin.ModelAdmin):
    list_display = ["authority_name", "country_code", "email", "info_uri"]
    list_filter = ["country_code"]
    search_fields = ["authority_name", "email"]
    autocomplete_fields = ["legal_entity"]
    ordering = ["country_code", "authority_name"]


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ["format", "attestation_type", "catalogue_schema_uri", "created_at"]
    list_filter = ["format"]
    search_fields = ["attestation_type", "catalogue_schema_uri"]
    inlines = [ClaimInline]
    ordering = ["-created_at"]

    fieldsets = (
        ("Format", {"fields": ("format", "meta")}),
        (
            "Attestation Type",
            {
                "fields": (
                    "attestation_type",
                    "catalogue_schema_uri",
                    "attestation_rulebook_uri",
                )
            },
        ),
    )


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ["credential", "path_display", "values"]
    list_filter = ["credential__format"]
    search_fields = ["credential__attestation_type"]
    autocomplete_fields = ["credential"]
    ordering = ["credential"]

    def path_display(self, obj):
        if isinstance(obj.path, list):
            return ".".join(str(p) for p in obj.path)
        return str(obj.path)

    path_display.short_description = "Path"


@admin.register(IntendedUse)
class IntendedUseAdmin(admin.ModelAdmin):
    list_display = [
        "intended_use_identifier",
        "wallet_relying_party",
        "validity_start",
        "validity_end",
        "is_active_display",
    ]
    list_filter = ["wallet_relying_party", "validity_start"]
    search_fields = ["intended_use_identifier", "wallet_relying_party__trade_name"]
    autocomplete_fields = ["wallet_relying_party"]
    inlines = [
        IntendedUsePurposeInline,
        IntendedUsePrivacyPolicyInline,
        IntendedUseCredentialInline,
    ]
    ordering = ["-validity_start"]

    fieldsets = (
        (
            "Identification",
            {"fields": ("wallet_relying_party", "intended_use_identifier")},
        ),
        ("Validity Period", {"fields": ("validity_start", "validity_end")}),
    )

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')

    is_active_display.short_description = "Status"


@admin.register(WRPRegistrationCertificate)
class WRPRegistrationCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_identifier",
        "intended_use",
        "issued_at",
        "expires_at",
        "is_active",
    ]
    list_filter = ["is_active", "issued_at"]
    search_fields = ["certificate_identifier", "intended_use__intended_use_identifier"]
    autocomplete_fields = ["intended_use"]
    ordering = ["-issued_at"]

    fieldsets = (
        ("Intended Use", {"fields": ("intended_use",)}),
        (
            "Certificate Details",
            {
                "fields": (
                    "certificate_identifier",
                    "certificate_serial",
                    "issuer_dn",
                    "subject_dn",
                )
            },
        ),
        ("Validity", {"fields": ("issued_at", "expires_at", "is_active")}),
        (
            "Revocation",
            {"fields": ("revoked_at", "revocation_reason"), "classes": ("collapse",)},
        ),
        (
            "Certificate Content",
            {"fields": ("certificate_pem",), "classes": ("collapse",)},
        ),
    )


@admin.register(WRPAccessCertificate)
class WRPAccessCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_serial",
        "wallet_relying_party",
        "not_before",
        "not_after",
        "is_current",
    ]
    list_filter = ["is_current", "wallet_relying_party"]
    search_fields = ["certificate_serial", "wallet_relying_party__trade_name"]
    autocomplete_fields = ["wallet_relying_party"]
    ordering = ["-not_before"]

    fieldsets = (
        ("Wallet Relying Party", {"fields": ("wallet_relying_party",)}),
        (
            "Certificate Details",
            {
                "fields": (
                    "certificate_serial",
                    "certificate_fingerprint_sha256",
                    "issuer_dn",
                    "subject_dn",
                )
            },
        ),
        ("Validity Period", {"fields": ("not_before", "not_after", "is_current")}),
        (
            "Certificate Transparency",
            {
                "fields": ("ct_log_id", "ct_log_timestamp", "ct_sct"),
                "classes": ("collapse",),
            },
        ),
        (
            "Revocation",
            {"fields": ("revoked_at", "revocation_reason"), "classes": ("collapse",)},
        ),
        (
            "Certificate Content",
            {"fields": ("certificate_pem",), "classes": ("collapse",)},
        ),
    )


@admin.register(WalletRelyingParty)
class WalletRelyingPartyAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "legal_entity",
        "registration_status_display",
        "is_psb",
        "is_intermediary",
        "supervisory_authority",
        "registered_at",
    ]
    list_filter = [
        "registration_status",
        "is_psb",
        "is_intermediary",
        "supervisory_authority__country_code",
    ]
    search_fields = [
        "trade_name",
        "legal_entity__legal_person__legal_name",
        "legal_entity__natural_person__given_name",
        "legal_entity__natural_person__family_name",
    ]
    autocomplete_fields = ["legal_entity", "supervisory_authority"]
    inlines = [
        WRPServiceDescriptionInline,
        WRPSupportURIInline,
        WRPEntitlementInline,
        WRPPolicyInline,
        WRPProvidesAttestationInline,
        WRPUsesIntermediaryInline,
        WRPAccessCertificateInline,
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Legal Entity", {"fields": ("legal_entity",)}),
        ("Basic Information", {"fields": ("trade_name", "registry_uri")}),
        ("Classification", {"fields": ("is_psb", "is_intermediary")}),
        ("Supervisory Authority", {"fields": ("supervisory_authority",)}),
        ("Registration Status", {"fields": ("registration_status", "registered_at")}),
        (
            "Audit Information",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def registration_status_display(self, obj):
        colors = {
            "pending": "orange",
            "active": "green",
            "suspended": "yellow",
            "revoked": "red",
        }
        color = colors.get(obj.registration_status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_registration_status_display(),
        )

    registration_status_display.short_description = "Status"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "legal_entity",
                "legal_entity__legal_person",
                "legal_entity__natural_person",
                "supervisory_authority",
            )
        )


@admin.register(WRPSupportURI)
class WRPSupportURIAdmin(admin.ModelAdmin):
    list_display = ["wallet_relying_party", "support_type", "support_uri", "is_primary"]
    list_filter = ["support_type", "is_primary"]
    search_fields = ["support_uri", "wallet_relying_party__trade_name"]
    autocomplete_fields = ["wallet_relying_party"]
    ordering = ["wallet_relying_party", "-is_primary"]


@admin.register(WRPEntitlement)
class WRPEntitlementAdmin(admin.ModelAdmin):
    list_display = [
        "wallet_relying_party",
        "entitlement_type",
        "granted_at",
        "expires_at",
        "is_active",
    ]
    list_filter = ["entitlement_type", "is_active"]
    search_fields = ["wallet_relying_party__trade_name", "entitlement_uri"]
    autocomplete_fields = ["wallet_relying_party"]
    ordering = ["wallet_relying_party", "entitlement_type"]


@admin.register(WRPServiceDescription)
class WRPServiceDescriptionAdmin(admin.ModelAdmin):
    list_display = ["wallet_relying_party", "lang", "content_preview"]
    list_filter = ["lang"]
    search_fields = ["content", "wallet_relying_party__trade_name"]
    autocomplete_fields = ["wallet_relying_party"]
    ordering = ["wallet_relying_party", "lang"]

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content Preview"


@admin.register(WRPProvidesAttestation)
class WRPProvidesAttestationAdmin(admin.ModelAdmin):
    list_display = ["wallet_relying_party", "credential"]
    list_filter = ["credential__format"]
    search_fields = ["wallet_relying_party__trade_name", "credential__attestation_type"]
    autocomplete_fields = ["wallet_relying_party", "credential"]
    ordering = ["wallet_relying_party"]


@admin.register(WRPUsesIntermediary)
class WRPUsesIntermediaryAdmin(admin.ModelAdmin):
    list_display = [
        "wallet_relying_party",
        "intermediary",
        "relationship_start_date",
        "relationship_end_date",
    ]
    list_filter = ["relationship_start_date"]
    search_fields = [
        "wallet_relying_party__trade_name",
        "intermediary__trade_name",
        "intermediary_identifier",
    ]
    autocomplete_fields = ["wallet_relying_party", "intermediary"]
    readonly_fields = [
        "intermediary_identifier",
        "intermediary_trade_name",
        "intermediary_registry_uri",
    ]
    ordering = ["wallet_relying_party", "-relationship_start_date"]


@admin.register(IntendedUsePurpose)
class IntendedUsePurposeAdmin(admin.ModelAdmin):
    list_display = ["intended_use", "lang", "content_preview"]
    list_filter = ["lang"]
    search_fields = ["content", "intended_use__intended_use_identifier"]
    autocomplete_fields = ["intended_use"]
    ordering = ["intended_use", "lang"]

    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    content_preview.short_description = "Content Preview"


@admin.register(IntendedUsePrivacyPolicy)
class IntendedUsePrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ["intended_use", "policy", "locale", "is_primary"]
    list_filter = ["locale", "is_primary"]
    search_fields = ["intended_use__intended_use_identifier", "policy__policy_uri"]
    autocomplete_fields = ["intended_use", "policy"]
    ordering = ["intended_use", "-is_primary"]


@admin.register(IntendedUseCredential)
class IntendedUseCredentialAdmin(admin.ModelAdmin):
    list_display = ["intended_use", "credential", "is_mandatory", "request_order"]
    list_filter = ["is_mandatory", "credential__format"]
    search_fields = [
        "intended_use__intended_use_identifier",
        "credential__attestation_type",
    ]
    autocomplete_fields = ["intended_use", "credential"]
    ordering = ["intended_use", "request_order"]


@admin.register(LegalEntityIdentifier)
class LegalEntityIdentifierAdmin(admin.ModelAdmin):
    list_display = ["legal_entity", "identifier", "is_primary"]
    list_filter = ["is_primary", "identifier__identifier_type"]
    search_fields = [
        "legal_entity__legal_person__legal_name",
        "identifier__identifier_value",
    ]
    autocomplete_fields = ["legal_entity", "identifier"]
    ordering = ["legal_entity", "-is_primary"]


@admin.register(WRPPolicy)
class WRPPolicyAdmin(admin.ModelAdmin):
    list_display = ["wallet_relying_party", "policy"]
    search_fields = ["wallet_relying_party__trade_name", "policy__policy_uri"]
    autocomplete_fields = ["wallet_relying_party", "policy"]
    ordering = ["wallet_relying_party"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "table_name",
        "record_id",
        "action",
        "changed_by",
        "changed_at",
        "ip_address",
    ]
    list_filter = ["action", "table_name", "changed_at"]
    search_fields = ["table_name", "changed_by", "ip_address"]
    readonly_fields = [
        "table_name",
        "record_id",
        "action",
        "old_values",
        "new_values",
        "changed_by",
        "changed_at",
        "ip_address",
        "user_agent",
    ]
    ordering = ["-changed_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMIN SITE CONFIGURATION
# ============================================================================

admin.site.site_header = "EUDI Wallet RP Registration"
admin.site.site_title = "RP Registration Admin"
admin.site.index_title = "Wallet Relying Party Management"
