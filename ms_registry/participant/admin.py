from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from . import models


@admin.register(models.Participant)
class ParticipantAdmin(DjangoUserAdmin):
    fieldsets = (
        ("Participant", {"fields": ("email", "password")}),
        (
            _("Personal"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )

    exclude = ("username",)
    list_display = ("email", "first_name", "last_name", "created_at")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if (
            not request.user.is_superuser
            and obj is not None
            and obj.is_staff
            and obj != request.user
        ):
            return (
                readonly_fields
                + tuple(field.name for field in obj._meta.fields)
                + ("groups", "user_permissions")
            )

        if not request.user.is_superuser:
            readonly_fields += (
                "is_superuser",
                "is_staff",
                "groups",
                "user_permissions",
            )

        return readonly_fields

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_staff:
            return False

        return super().has_delete_permission(request, obj)
