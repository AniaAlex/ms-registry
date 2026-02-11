"""
rp_register URL Configuration
"""

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/registry/", include("registry.urls", namespace="registry")),
    path("api/legal-entities/", include("legal_entities.urls", namespace="legal_entities")),
]

# OpenAPI docs
if os.getenv("ENV") in ("LOCAL", "DEV"):
    urlpatterns.extend(
        [
            path(
                "docs/",
                SpectacularSwaggerView.as_view(url_name="schema"),
                name="swagger",
            ),
            path(
                "docs/redoc/",
                SpectacularRedocView.as_view(url_name="schema"),
                name="redoc",
            ),
            path("docs/openapi/", SpectacularAPIView.as_view(), name="schema"),
        ]
    )

# Debug toolbar
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

# Media files for local dev
if os.getenv("ENV") == "LOCAL":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
