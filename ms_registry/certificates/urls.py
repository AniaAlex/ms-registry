from certificates.views import CnfPageView, CnfView
from django.urls import path

app_name = "certificates"

urlpatterns = [
    path("cnf/<uuid:entity_id>/", CnfView.as_view(), name="cnf"),
    path("cnf/<uuid:entity_id>/view/", CnfPageView.as_view(), name="cnf-page"),
]
