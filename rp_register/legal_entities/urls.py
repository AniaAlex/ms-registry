"""
URL configuration for legal_entities app
"""

from django.urls import path

from . import views

app_name = "legal_entities"

urlpatterns = [
    path(
        "add/",
        views.LegalEntityFormView.as_view(),
        name="legal-entity-add-form",
    ),
    path(
        "",
        views.LegalEntityListCreateView.as_view(),
        name="legal-entity-list-create",
    ),
    path(
        "<uuid:pk>/",
        views.LegalEntityDetailView.as_view(),
        name="legal-entity-detail",
    ),
]
