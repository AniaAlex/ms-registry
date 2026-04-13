"""
URL configuration for legal_entities app
"""

from django.urls import path

from . import views

app_name = "legal_entities"

urlpatterns = [
    path(
        "legal-entity-create/",
        views.LegalEntityCreateView.as_view(),
        name="legal-entity-create",
    ),
    path(
        "<uuid:pk>/",
        views.LegalEntityDetailView.as_view(),
        name="legal-entity-detail",
    ),
]
