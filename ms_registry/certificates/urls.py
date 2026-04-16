from certificates.views import (
    AccessCertificateDetailPageView,
    AccessCertificateUploadPageView,
    AccessCertificateUploadView,
    CnfPageView,
    CnfView,
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
        "detail/<uuid:entity_id>/view/",
        AccessCertificateDetailPageView.as_view(),
        name="detail-page",
    ),
]
