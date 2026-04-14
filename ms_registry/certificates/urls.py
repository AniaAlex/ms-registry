from certificates.views import CnfView
from django.urls import path

app_name = "certificates"

urlpatterns = [
    path("cnf/<uuid:entity_id>/", CnfView.as_view(), name="cnf"),
]
