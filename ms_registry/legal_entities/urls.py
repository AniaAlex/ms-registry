"""
URL configuration for legal_entities app
"""

from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "legal_entities"

urlpatterns = [
    path(
        "add/",
        views.LegalEntityCreateView.as_view(),
        name="legal-entity-create",
    ),
    # pure django success replace no ddrf view
    path(
        "add/success/",
        TemplateView.as_view(template_name="add_legal_entity_success.html"),
        name="legal-entity-create-success",
    ),
    path(
        "<uuid:pk>/",
        views.LegalEntityDetailView.as_view(),
        name="legal-entity-detail",
    ),
]
