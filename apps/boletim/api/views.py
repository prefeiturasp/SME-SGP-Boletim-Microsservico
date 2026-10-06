"""Views do domínio de boletim."""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from apps.boletim.api.renderers import PdfRenderer
from apps.boletim.constantes import MENSAGEM_ALUNOS_TURMA_NAO_ENCONTRADOS
from apps.boletim.relatorios.gerador_pdf import GeradorBoletinsPdf
from apps.boletim.serializers import (
    BoletimAlunoResponseSerializer,
    FiltrosBoletinsPdfSerializer,
    FiltrosBoletinsSerializer,
)
from apps.boletim.services import BoletimService
from apps.core.permissions import RequerAbrangenciaParaJwt
from apps.core.views import BaseAPIView

_CABECALHO_MENSAGEM_SEM_ALUNOS = OpenApiParameter(
    name="X-Mensagem",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    description="Informa que alunos da turma não foram encontrados.",
    response=[204],
)


class BoletinsView(BaseAPIView):
    """Lista boletins consolidados de vários alunos."""

    permission_classes = [RequerAbrangenciaParaJwt]
    campos_abrangencia = {
        "dre": "dre_codigo",
        "ue": "ue_codigo",
        "turma": "turma_codigo",
    }

    @extend_schema(
        parameters=[FiltrosBoletinsSerializer],
        responses={
            200: BoletimAlunoResponseSerializer(many=True),
            204: OpenApiResponse(description="Nenhum aluno encontrado."),
        },
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
        if not dados:
            return Response(
                status=HTTP_204_NO_CONTENT,
                headers={"X-Mensagem": MENSAGEM_ALUNOS_TURMA_NAO_ENCONTRADOS},
            )
        return Response(BoletimAlunoResponseSerializer(dados, many=True).data)


class BoletinsPdfView(BaseAPIView):
    """Gera boletins escolares de vários alunos em PDF."""

    permission_classes = [RequerAbrangenciaParaJwt]
    campos_abrangencia = BoletinsView.campos_abrangencia
    renderer_classes = [JSONRenderer, PdfRenderer]

    @extend_schema(
        parameters=[
            FiltrosBoletinsPdfSerializer,
            _CABECALHO_MENSAGEM_SEM_ALUNOS,
            OpenApiParameter(
                name="format",
                location=OpenApiParameter.QUERY,
                exclude=True,
            ),
        ],
        responses={
            (200, "application/pdf"): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Arquivo PDF com os boletins selecionados.",
            ),
            204: OpenApiResponse(
                description=(
                    "Nenhum aluno encontrado. A mensagem é retornada no "
                    "cabeçalho `X-Mensagem`."
                )
            ),
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
        if not dados:
            return Response(
                status=HTTP_204_NO_CONTENT,
                headers={"X-Mensagem": MENSAGEM_ALUNOS_TURMA_NAO_ENCONTRADOS},
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
