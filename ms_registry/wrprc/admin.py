"""
WRPRC Admin Configuration
"""

from django.contrib import admin

from .models import IssuedWRPRC, SigningKey, StatusList


@admin.register(StatusList)
class StatusListAdmin(admin.ModelAdmin):
    list_display = ["list_id", "purpose", "current_index", "capacity", "created_at"]
    list_filter = ["purpose"]
    search_fields = ["list_id"]
    readonly_fields = ["id", "bits", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("list_id", "purpose")}),
        ("Capacity", {"fields": ("current_index", "capacity")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(IssuedWRPRC)
class IssuedWRPRCAdmin(admin.ModelAdmin):
    list_display = [
        "jti",
        "registered_entity",
        "status",
        "issued_at",
        "expires_at",
        "is_valid_display",
    ]
    list_filter = ["status", "issued_at", "expires_at"]
    search_fields = ["jti", "registered_entity__legal_entity__legal_name"]
    readonly_fields = [
        "id",
        "jti",
        "jwt_hash",
        "status_list",
        "status_list_index",
        "issued_at",
        "revoked_at",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["registered_entity", "intended_use"]

    fieldsets = (
        (None, {"fields": ("registered_entity", "intended_use", "status")}),
        ("Status List", {"fields": ("status_list", "status_list_index")}),
        (
            "Lifecycle",
            {"fields": ("issued_at", "expires_at", "revoked_at", "revocation_reason")},
        ),
        ("Audit", {"fields": ("jti", "jwt_hash"), "classes": ("collapse",)}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def is_valid_display(self, obj):
        return obj.is_valid()

    is_valid_display.boolean = True
    is_valid_display.short_description = "Valid"

    actions = ["revoke_selected"]

    @admin.action(description="Revoke selected WRPRCs")
    def revoke_selected(self, request, queryset):
        count = 0
        for wrprc in queryset.filter(status=IssuedWRPRC.Status.ACTIVE):
            wrprc.revoke(reason=f"Bulk revocation by {request.user}")
            count += 1
        self.message_user(request, f"Revoked {count} WRPRC(s).")


@admin.register(SigningKey)
class SigningKeyAdmin(admin.ModelAdmin):
    list_display = ["kid", "algorithm", "status", "valid_from", "valid_until"]
    list_filter = ["status", "algorithm"]
    search_fields = ["kid"]
    readonly_fields = ["id", "public_key_jwk", "rotated_at", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("kid", "algorithm", "status")}),
        ("Keys", {"fields": ("public_key_jwk", "x5c", "external_key_reference")}),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        (
            "Rotation",
            {"fields": ("rotated_at", "replaced_by"), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
