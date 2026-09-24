"""Views do domínio de boletim."""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.request import Request
from rest_framework.response import Response

from apps.boletim.relatorios.gerador_pdf import GeradorBoletinsPdf
from apps.boletim.serializers import (
    DESCRICAO_MODALIDADES,
    BoletimAlunoResponseSerializer,
    FiltrosBoletimSerializer,
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
            ano_letivo=filtros.validated_data["anoLetivo"],
            dre_codigo=filtros.validated_data["dreCodigo"],
            ue_codigo=filtros.validated_data["ueCodigo"],
            semestre=filtros.validated_data["semestre"],
            modalidade=filtros.validated_data["modalidade"],
            alunos_codigo=filtros.validated_data["alunosCodigo"],
            turma_codigo=filtros.validated_data.get("turmaCodigo"),
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
            ano_letivo=filtros.validated_data["anoLetivo"],
            dre_codigo=filtros.validated_data["dreCodigo"],
            ue_codigo=filtros.validated_data["ueCodigo"],
            semestre=filtros.validated_data["semestre"],
            modalidade=filtros.validated_data["modalidade"],
            alunos_codigo=filtros.validated_data["alunosCodigo"],
            turma_codigo=filtros.validated_data.get("turmaCodigo"),
            bimestre=filtros.validated_data.get("bimestre"),
        )
        pdf = GeradorBoletinsPdf().gerar(
            dados,
            boletins_por_pagina=filtros.validated_data["boletinsPorPagina"],
        )
        resposta = HttpResponse(pdf, content_type="application/pdf")
        resposta["Content-Disposition"] = (
            'inline; filename="boletins-escolares.pdf"'
        )
        return resposta


class BoletimAlunoView(BaseAPIView):
    """Lista o boletim consolidado de um aluno."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="anoLetivo",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Ano letivo consultado.",
            ),
            OpenApiParameter(
                name="bimestre",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Bimestre opcional.",
            ),
            OpenApiParameter(
                name="dreCodigo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Código da DRE.",
            ),
            OpenApiParameter(
                name="ueCodigo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Código da unidade escolar.",
            ),
            OpenApiParameter(
                name="semestre",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Semestre da turma, entre 0 e 2. Use 0 quando semestre "
                    "não se aplicar à modalidade."
                ),
            ),
            OpenApiParameter(
                name="turmaCodigo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Código da turma.",
            ),
            OpenApiParameter(
                name="modalidade",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=DESCRICAO_MODALIDADES,
                enum=[1, 3, 4, 5, 6, 7, 8, 9, 10],
            ),
        ],
        responses={200: BoletimAlunoResponseSerializer},
        operation_id="boletim_listar_por_aluno",
        tags=["Boletim"],
    )
    def get(self, request: Request, aluno_codigo: int) -> Response:
        """Retorna o boletim do aluno para o ano solicitado.

        Args:
            request: Requisição HTTP com os filtros da consulta.
            aluno_codigo: Código do aluno recebido na rota.

        Returns:
            Lista dos componentes e períodos consolidados do boletim.
        """
        filtros = FiltrosBoletimSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        dados = BoletimService().listar_por_aluno(
            aluno_codigo=aluno_codigo,
            ano_letivo=filtros.validated_data["anoLetivo"],
            bimestre=filtros.validated_data.get("bimestre"),
            dre_codigo=filtros.validated_data.get("dreCodigo"),
            ue_codigo=filtros.validated_data.get("ueCodigo"),
            semestre=filtros.validated_data.get("semestre"),
            turma_codigo=filtros.validated_data.get("turmaCodigo"),
            modalidade=filtros.validated_data.get("modalidade"),
        )
        return Response(BoletimAlunoResponseSerializer(dados).data)
