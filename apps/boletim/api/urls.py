"""Rotas do domínio de boletim."""

from django.urls import path

from apps.boletim.api.views import (
    BoletinsView,
    UltimaAtualizacaoBoletimView,
)

urlpatterns = [
    path("", BoletinsView.as_view(), name="boletins"),
    path(
        "ultima-atualizacao/",
        UltimaAtualizacaoBoletimView.as_view(),
        name="boletim-ultima-atualizacao",
    ),
]
