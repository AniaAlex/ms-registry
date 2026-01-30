from django.apps import AppConfig


class RPRegistrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rp_registration"
    verbose_name = "EUDI Wallet RP Registration"

    def ready(self):
        import rp_registration.signals  # noqa
