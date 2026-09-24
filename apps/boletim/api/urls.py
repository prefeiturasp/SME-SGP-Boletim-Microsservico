"""Rotas do domínio de boletim."""

from django.urls import path

from apps.boletim.api.views import (
    BoletimAlunoView,
    BoletinsPdfView,
    BoletinsView,
)

urlpatterns = [
    path("", BoletinsView.as_view(), name="boletins"),
    path("pdf/", BoletinsPdfView.as_view(), name="boletins-pdf"),
    path(
        "alunos/<int:aluno_codigo>/",
        BoletimAlunoView.as_view(),
        name="boletim-aluno",
    ),
]
