"""
URL configuration for tsl_generator app
"""

from django.urls import path

from . import views

app_name = "tsl_generator"

urlpatterns = [
    # Trust Service URLs (main entry point)
    path(
        "services/add/",
        views.TrustServiceFormView.as_view(),
        name="service-add-form",
    ),
    path(
        "services/",
        views.TrustServiceListCreateView.as_view(),
        name="service-list-create",
    ),
    path(
        "services/<int:pk>/",
        views.TrustServiceDetailView.as_view(),
        name="service-detail",
    ),
    # Trust Service Provider URLs
    path(
        "providers/add/",
        views.TrustServiceProviderFormView.as_view(),
        name="tsp-add-form",
    ),
    path(
        "providers/",
        views.TrustServiceProviderListCreateView.as_view(),
        name="tsp-list-create",
    ),
    path(
        "providers/<int:pk>/",
        views.TrustServiceProviderDetailView.as_view(),
        name="tsp-detail",
    ),
    # TSL Scheme URLs
    path(
        "schemes/",
        views.TSLSchemeListView.as_view(),
        name="scheme-list",
    ),
    path(
        "schemes/<int:pk>/xml/",
        views.TSLSchemeXMLView.as_view(),
        name="scheme-xml",
    ),
]
