"""
Django settings for ms_registry project.
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-this-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "debug_toolbar",
    "django_object_actions",  # Required by django-ca admin
    "django_ca",  # Access CA functionality
    # Local apps - new modular structure
    "core",
    "participant",
    "legal_entities",
    "registry",
    "credentials",
    "certificates",
    "tsl_generator",
    "lote_source",
]

AUTH_USER_MODEL = "participant.Participant"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "ms_registry.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ms_registry.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ms_registry"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "supersecret"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/var/www/static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = "/var/www/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "participant.authentication.JWTCookieAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "EUDI Wallet RP Registry API",
    "DESCRIPTION": "API for managing Registered Entities in the EUDI Wallet ecosystem",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    **({"SERVERS": [{"url": "/api"}]} if os.getenv("ENV") != "LOCAL" else {}),
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Debug toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]

# ──────────────────────────────────────────────────────────────────────────────
# django-ca settings (Access CA)
# https://django-ca.readthedocs.io/en/latest/settings.html
# ──────────────────────────────────────────────────────────────────────────────

# Directory for CA-related files (keys, CRLs)
CA_DIR = BASE_DIR / "ca"

# Default CA serial (hex string, set after creating the CA with init_ca command)
# Leave unset initially - the integration code will find the first usable CA
# After init_ca, you can set this to the CA's serial number (hex)
_ca_default = os.environ.get("CA_DEFAULT_CA", "")
if _ca_default and _ca_default.replace(" ", "").isalnum():
    # Only set if it looks like a hex serial (not a name)
    import re

    if re.match(r"^[A-Fa-f0-9]+$", _ca_default):
        CA_DEFAULT_CA = _ca_default.upper()

# Key storage backend - file system for dev, HSM for production
CA_KEY_BACKENDS = {
    "default": {
        "BACKEND": "django_ca.key_backends.storages.StoragesBackend",
        "OPTIONS": {
            "storage_alias": "django-ca",
        },
    },
}

# Storage for CA private keys
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "django-ca": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(CA_DIR / "keys"),
            "file_permissions_mode": 0o600,
            "directory_permissions_mode": 0o700,
        },
    },
}

# Default subject for certificates (django-ca format: list of dicts)
CA_DEFAULT_SUBJECT = [
    {"oid": "C", "value": os.environ.get("CA_COUNTRY", "SE")},
    {"oid": "O", "value": os.environ.get("CA_ORGANIZATION", "EUDI Wallet Registry")},
]

# Certificate validity (days)
CA_DEFAULT_EXPIRES = 365  # 1 year for entity certificates

# Signature hash algorithm for issued certificates.
# WP4 access certificate policy specifies ecdsa-with-SHA384 (django-ca
# defaults to SHA-512). Applies to EC/RSA CAs.
CA_DEFAULT_SIGNATURE_HASH_ALGORITHM = "SHA-384"

# Certificate Practice Statement (CPS) URI — included in certificate policies
# Per ETSI TS 119 411-8 GEN-6.6.1-06
CA_CPS_URI = os.environ.get("CA_CPS_URI", None)

# OCSP and CRL URLs hostname
# Django-ca uses this to build CRL/OCSP/CA Issuer URLs in certificates
CA_DEFAULT_HOSTNAME = os.environ.get("CA_HOSTNAME", "localhost:8000")

# Public base URL under which this service's django-ca revocation endpoints
# (CRL, OCSP, CA Issuers) are reachable by relying parties — including the
# scheme and any reverse-proxy path prefix (e.g. "/api" from the uWSGI mount).
#
# django-ca bakes the AIA/CRL Distribution Points URLs into the CA's stored
# config at creation time using a HARDCODED "http://" scheme and the path from
# reverse(); because init_ca runs as a management command (no WSGI script name),
# that path also lacks the "/api" prefix the proxy expects. The result is dead
# "http://host/ca/..." URLs on every issued certificate. We therefore build
# these extensions explicitly at issuance time from this setting instead of
# relying on the CA's stored URLs. See certificates.ca_integration.
CA_PUBLIC_BASE_URL = os.environ.get("CA_PUBLIC_BASE_URL", "http://localhost:8000")

# Certificate profiles for EUDI Wallet Access Certificates
# Note: basic_constraints is not configurable in profiles (set automatically)
CA_PROFILES = {
    "eudiwrp": {
        "description": "EUDI Wallet Relying Party Access Certificate (WRPAC)",
        "extensions": {
            "key_usage": {
                "critical": True,
                "value": ["digital_signature"],
            },
            # The access cert authenticates the relying party — CIR 2025/848 Art. 2 /
            # TS 119 411-8 Intro.
            # Authentication = the digitalSignature bit — RFC 5280 §4.2.1.3
            # ("entity authentication service").
            "extended_key_usage": {
                "critical": False,
                "value": ["clientAuth"],
            },
        },
        "subject": False,  # Use subject from CSR or issuance call
    },
}

# Default profile for certificate issuance
CA_DEFAULT_PROFILE = "eudiwrp"

# Run django-ca tasks (OCSP responder key generation, CRL caching) in-process
# instead of dispatching them to Celery. CA_USE_CELERY defaults to True whenever
# Celery is importable, but this project runs no Celery worker or broker, so the
# default makes `regenerate_ocsp_keys` (and other tasks) try to reach a broker on
# localhost and fail with "Connection refused". Synchronous execution is correct
# here.
CA_USE_CELERY = False

# Enable OCSP responder
CA_ENABLE_OCSP = True

# Disable ACME (not used for EUDI Wallet - we use CSR-based issuance)
CA_ENABLE_ACME = False
