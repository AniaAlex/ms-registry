"""Admin configuration for Certificates app"""

from django.contrib import admin

from .models import AuditLog, EntityAccessCertificate, EntityRegistrationCertificate

# Unregister ACME models from admin (not used for EUDI Wallet)
try:
    from django_ca.models import (
        AcmeAccount,
        AcmeAuthorization,
        AcmeCertificate,
        AcmeChallenge,
        AcmeOrder,
    )

    admin.site.unregister(AcmeAccount)
    admin.site.unregister(AcmeAuthorization)
    admin.site.unregister(AcmeCertificate)
    admin.site.unregister(AcmeChallenge)
    admin.site.unregister(AcmeOrder)
except (ImportError, admin.sites.NotRegistered):
    pass


class EntityAccessCertificateInline(admin.TabularInline):
    model = EntityAccessCertificate
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


@admin.register(EntityAccessCertificate)
class EntityAccessCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_serial",
        "registered_entity",
        "is_current",
        "not_before",
        "not_after",
        "revoked_at",
    ]
    list_filter = ["is_current", "not_before", "not_after"]
    search_fields = ["certificate_serial", "registered_entity__trade_name"]
    autocomplete_fields = ["registered_entity"]
    readonly_fields = ["certificate_fingerprint_sha256"]
    ordering = ["-not_before"]


@admin.register(EntityRegistrationCertificate)
class EntityRegistrationCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_identifier",
        "intended_use",
        "is_active",
        "issued_at",
        "expires_at",
        "revoked_at",
    ]
    list_filter = ["is_active", "issued_at", "expires_at"]
    search_fields = ["certificate_identifier", "intended_use__intended_use_identifier"]
    autocomplete_fields = ["intended_use"]
    ordering = ["-issued_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["table_name", "record_id", "action", "changed_by", "changed_at"]
    list_filter = ["table_name", "action", "changed_at"]
    search_fields = ["table_name", "changed_by"]
    readonly_fields = [
        "id",
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
