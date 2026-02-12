"""Admin configuration for Core app"""

from django.contrib import admin

from .models import Identifier, Law, Policy


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
    ordering = ["policy_type", "policy_uri"]
