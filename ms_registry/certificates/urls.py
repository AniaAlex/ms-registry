from certificates.views import (
    AccessCertificateDetailPageView,
    AccessCertificateUploadPageView,
    AccessCertificateUploadView,
    CnfPageView,
    CnfView,
    IssueCertificateView,
    SigningCertificateDetailView,
    SigningCertificateListCreateView,
    SigningCertificatePageView,
)
from django.urls import path

app_name = "certificates"

urlpatterns = [
    path("cnf/<uuid:entity_id>/", CnfView.as_view(), name="cnf"),
    path("cnf/<uuid:entity_id>/view/", CnfPageView.as_view(), name="cnf-page"),
    path(
        "upload/<uuid:entity_id>/", AccessCertificateUploadView.as_view(), name="upload"
    ),
    path(
        "upload/<uuid:entity_id>/view/",
        AccessCertificateUploadPageView.as_view(),
        name="upload-page",
    ),
    path(
        "issue/<uuid:entity_id>/",
        IssueCertificateView.as_view(),
        name="issue",
    ),
    path(
        "detail/<uuid:entity_id>/view/",
        AccessCertificateDetailPageView.as_view(),
        name="detail-page",
    ),
    # Signing certificates
    path(
        "signing/<uuid:entity_id>/",
        SigningCertificateListCreateView.as_view(),
        name="signing",
    ),
    path(
        "signing/<uuid:entity_id>/<uuid:cert_id>/",
        SigningCertificateDetailView.as_view(),
        name="signing-detail",
    ),
    path(
        "signing/<uuid:entity_id>/view/",
        SigningCertificatePageView.as_view(),
        name="signing-page",
    ),
]
