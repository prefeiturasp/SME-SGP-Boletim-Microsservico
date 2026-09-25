"""Views do domínio de boletim."""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework.request import Request
from rest_framework.response import Response

from apps.boletim.relatorios.gerador_pdf import GeradorBoletinsPdf
from apps.boletim.serializers import (
    BoletimAlunoResponseSerializer,
    FiltrosBoletinsPdfSerializer,
    FiltrosBoletinsSerializer,
)
from apps.boletim.services import BoletimService
from apps.core.views import BaseAPIView


class BoletinsView(BaseAPIView):
    """Lista boletins consolidados de vários alunos."""

    @extend_schema(
        parameters=[FiltrosBoletinsSerializer],
        responses={200: BoletimAlunoResponseSerializer(many=True)},
        operation_id="boletim_listar_varios_alunos",
        tags=["Boletim"],
    )
    def get(self, request: Request) -> Response:
        """Retorna os boletins dos alunos selecionados.

        Args:
            request: Requisição HTTP com os filtros da consulta.

        Returns:
            Lista de boletins agrupados por aluno e turma.
        """
        filtros = FiltrosBoletinsSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        dados = BoletimService().listar_boletins(
            ano_letivo=filtros.validated_data["ano_letivo"],
            dre_codigo=filtros.validated_data["dre_codigo"],
            ue_codigo=filtros.validated_data["ue_codigo"],
            semestre=filtros.validated_data["semestre"],
            modalidade=filtros.validated_data["modalidade"],
            alunos_codigo=filtros.validated_data["alunos_codigo"],
            considera_inativo=filtros.validated_data["considera_inativo"],
            turma_codigo=filtros.validated_data.get("turma_codigo"),
            bimestre=filtros.validated_data.get("bimestre"),
        )
        return Response(BoletimAlunoResponseSerializer(dados, many=True).data)


class BoletinsPdfView(BaseAPIView):
    """Gera boletins escolares de vários alunos em PDF."""

    @extend_schema(
        parameters=[FiltrosBoletinsPdfSerializer],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Arquivo PDF com os boletins selecionados.",
            )
        },
        operation_id="boletim_gerar_pdf_varios_alunos",
        tags=["Boletim"],
    )
    def get(self, request: Request) -> HttpResponse:
        """Retorna os boletins selecionados como um arquivo PDF."""
        filtros = FiltrosBoletinsPdfSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        dados = BoletimService().listar_boletins(
            ano_letivo=filtros.validated_data["ano_letivo"],
            dre_codigo=filtros.validated_data["dre_codigo"],
            ue_codigo=filtros.validated_data["ue_codigo"],
            semestre=filtros.validated_data["semestre"],
            modalidade=filtros.validated_data["modalidade"],
            alunos_codigo=filtros.validated_data["alunos_codigo"],
            considera_inativo=filtros.validated_data["considera_inativo"],
            turma_codigo=filtros.validated_data.get("turma_codigo"),
            bimestre=filtros.validated_data.get("bimestre"),
        )
        pdf = GeradorBoletinsPdf().gerar(
            dados,
            boletins_por_pagina=filtros.validated_data["boletins_por_pagina"],
        )
        resposta = HttpResponse(pdf, content_type="application/pdf")
        resposta["Content-Disposition"] = (
            'inline; filename="boletins-escolares.pdf"'
        )
        return resposta
