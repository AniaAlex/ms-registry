from .settings import *  # NOQA
from .settings import STORAGES  # noqa: F811 — explicit import to satisfy flake8 F405

TEST = True
DEBUG = False

# Keep django.contrib.admin - it's used in urls.py
# if "django.contrib.admin" in INSTALLED_APPS:
#     INSTALLED_APPS.remove("django.contrib.admin")
# if "ms_registry.apps.OTPAdminConfig" not in INSTALLED_APPS:
#     INSTALLED_APPS.append("ms_registry.apps.OTPAdminConfig")


MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

STORAGES = {
    **STORAGES,
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "django-ca": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}

CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CELERY_BACKEND = "memory"

# Run django-ca background tasks (CRL/OCSP key generation) synchronously in
# tests so CA creation doesn't try to reach a Celery broker.
CA_USE_CELERY = False

SILENCED_SYSTEM_CHECKS = [
    "debug_toolbar.W001",  # Debug toolbar excluded in tests
]
