from django.urls import path

from . import views

app_name = "lote_source"

urlpatterns = [
    path("pid-providers/", views.LOTEPIDProvidersView.as_view(), name="pid-providers"),
    path(
        "pubeaa-providers/",
        views.LOTEPubEAAProvidersView.as_view(),
        name="pubeaa-providers",
    ),
]
