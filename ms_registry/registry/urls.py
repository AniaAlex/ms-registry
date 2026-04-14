from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    # LoTE export
    path("lote-se/", views.LOTESEView.as_view(), name="lote-se"),
    # ==========================================================================
    # WalletRelyingParty API (TS5 Specification)
    # ==========================================================================
    # GET: List all WRPs, POST: Create new WRP, PUT: Update WRP, DELETE: Delete WRP
    path(
        "wrp/",
        views.WalletRelyingPartyView.as_view(),
        name="wrp",
    ),
    # GET: Retrieve single WRP by ID
    path(
        "wrp/<uuid:pk>/",
        views.WalletRelyingPartyDetailView.as_view(),
        name="wrp-detail",
    ),
    # ==========================================================================
    # Registered Entity URLs (internal/admin)
    # ==========================================================================
    path(
        "entities/",
        views.RegisteredEntityListCreateView.as_view(),
        name="entity-list-create",
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
