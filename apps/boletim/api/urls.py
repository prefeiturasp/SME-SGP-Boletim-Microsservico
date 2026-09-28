"""Rotas do domínio de boletim."""

from django.urls import path

from apps.boletim.api.views import (
    BoletinsPdfView,
    BoletinsView,
)

urlpatterns = [
    path("", BoletinsView.as_view(), name="boletins"),
    path("pdf/", BoletinsPdfView.as_view(), name="boletins-pdf"),
]
