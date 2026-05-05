from credentials.views import (
    CheckIntendedUseView,
    IntendedUseDetailView,
    IntendedUseListCreateView,
)
from django.urls import path

from . import views
from .views import EntityDetailView

app_name = "registry"

urlpatterns = [
    # TODO: remove — LOTESEView is commented out; replaced by lote_source app
    # path("lote-se/", views.LOTESEView.as_view(), name="lote-se"),
    # ==========================================================================
    # WalletRelyingParty API (TS5 Specification)
    # ==========================================================================
    # GET: List all WRPs, POST: Create new WRP, PUT: Update WRP, DELETE: Delete WRP
    path(
        "wrp/",
        views.WalletRelyingPartyView.as_view(),
        name="wrp",
    ),
    # GET: Check if a WRP has a registered intended use (TS5)
    path(
        "wrp/check-intended-use/",
        CheckIntendedUseView.as_view(),
        name="wrp-check-intended-use",
    ),
    # GET: Retrieve single WRP by ID
    path(
        "wrp/<uuid:pk>/",
        views.WalletRelyingPartyDetailView.as_view(),
        name="wrp-detail",
    ),
    # ==========================================================================
    # Intended Use API (nested under WRP)
    # ==========================================================================
    # GET: list, POST: create
    path(
        "wrp/<uuid:entity_pk>/intended-use/",
        IntendedUseListCreateView.as_view(),
        name="intended-use-list-create",
    ),
    # GET: retrieve, DELETE: revoke
    path(
        "wrp/<uuid:entity_pk>/intended-use/<uuid:iu_id>/",
        IntendedUseDetailView.as_view(),
        name="intended-use-detail",
    ),
    # ==========================================================================
    # Registered Entity URLs (internal/admin)
    # ==========================================================================
    path(
        "entities/",
        views.RegisteredEntityListCreateView.as_view(),
        name="entity-list-create",
    ),
    path(
        "entities/<uuid:pk>/",
        EntityDetailView.as_view(),
        name="entity-detail",
    ),
    # Supervisory Authority URLs
    path(
        "supervisory-authorities/add/",
        views.SupervisoryAuthorityFormView.as_view(),
        name="supervisory-authority-add-form",
    ),
    path(
        "supervisory-authorities/",
        views.SupervisoryAuthorityListCreateView.as_view(),
        name="supervisory-authority-list-create",
    ),
    path(
        "supervisory-authorities/<uuid:pk>/",
        views.SupervisoryAuthorityDetailView.as_view(),
        name="supervisory-authority-detail",
    ),
]
