"""
TSL Generator Django App Configuration
"""

from django.apps import AppConfig


class TSLGeneratorConfig(AppConfig):
    """App configuration for TSL Generator"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tsl_generator"
    verbose_name = "TSL Generator"
