from django.conf import settings
from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = "registry"

urlpatterns = [
    path(
        "entities/register/",
        views.RegisterEntityFormView.as_view(),
        name="entity-register-form",
    ),
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
    # path(
    #     "entities/<int:pk>/",
    #     views.RegisteredEntityRetrieveUpdateDestroyView.as_view(),
    #     name="entity-detail",
    # ),
    # path(
    #     "entities/<int:pk>/entitlements/",
    #     views.EntityEntitlementListCreateView.as_view(),
    #     name="entity-entitlements",
    # ),
    # path(
    #     "entities/<int:pk>/service-descriptions/",
    #     views.EntityServiceDescriptionListCreateView.as_view(),
    #     name="entity-service-descriptions",
    # ),
    # path(
    #     "entities/<int:pk>/support-uris/",
    #     views.EntitySupportURIListCreateView.as_view(),
    #     name="entity-support-uris",
    # ),
    # path(
    #     "entities/<int:pk>/uses-intermediaries/",
    #     views.EntityUsesIntermediaryListCreateView.as_view(),
    #     name="entity-uses-intermediaries",
    # ),
    # path(
    #     "entities/<int:pk>/policies/",
    #     views.RegisteredEntityPolicyListCreateView.as_view(),
    #     name="entity-policies",
    # ),
    # path(
    #     "supervisory-authorities/",
    #     views.SupervisoryAuthorityListCreateView.as_view(),
    #     name="supervisory-authority-list-create",
    # ),
    # path(
    #     "supervisory-authorities/<int:pk>/",
    #     views.SupervisoryAuthorityRetrieveUpdateDestroyView.as_view(),
    #     name="supervisory-authority-detail",
    # ),
]
