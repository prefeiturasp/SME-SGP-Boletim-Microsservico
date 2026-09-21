"""Rotas do domínio de boletim."""

from django.urls import path

from apps.boletim.api.views import BoletimAlunoView, BoletinsView

urlpatterns = [
    path("", BoletinsView.as_view(), name="boletins"),
    path(
        "alunos/<int:aluno_codigo>/",
        BoletimAlunoView.as_view(),
        name="boletim-aluno",
    ),
]
