"""
WRPRC URL Configuration
"""

from django.urls import path

from .views import (
    EntityWRPRCListView,
    IssueWRPRCView,
    RevokeWRPRCView,
    SigningKeysView,
    StatusListDetailView,
    StatusListView,
    WRPRCDetailView,
)

app_name = "wrprc"

urlpatterns = [
    # Issuance
    path("issue/", IssueWRPRCView.as_view(), name="issue"),
    # WRPRC management
    path("entity/<uuid:entity_id>/", EntityWRPRCListView.as_view(), name="entity-list"),
    path("<str:jti>/", WRPRCDetailView.as_view(), name="detail"),
    path("<str:jti>/revoke/", RevokeWRPRCView.as_view(), name="revoke"),
    # Status lists (public)
    path("status/<str:list_id>/", StatusListView.as_view(), name="status-list"),
    path(
        "status/<str:list_id>/meta/",
        StatusListDetailView.as_view(),
        name="status-list-meta",
    ),
    # Keys (within wrprc namespace, not global .well-known)
    path("keys/", SigningKeysView.as_view(), name="keys"),
]
