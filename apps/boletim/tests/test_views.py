"""Testes das views de boletim."""

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.boletim.serializers import MODALIDADES_CHOICES

_URL_COLETIVA = "/api/boletim/"
_URL_PDF = "/api/boletim/pdf/"


def _cliente_autenticado() -> APIClient:
    """Cria um cliente com a API key definida nas configurações."""
    client = APIClient()
    header = "HTTP_" + settings.API_KEY_HEADER.upper().replace("-", "_")
    client.credentials(**{header: settings.API_KEY})
    return client


class TestBoletinsView(TestCase):
    """Valida o contrato HTTP da consulta coletiva."""

    def setUp(self) -> None:
        """Prepara um cliente autenticado para os testes."""
        self.client = _cliente_autenticado()

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_boletins_de_varios_alunos(self, service_class) -> None:
        """Aceita vários códigos de aluno e retorna uma lista."""
        service = service_class.return_value
        service.listar_boletins.return_value = []

        response = self.client.get(
            _URL_COLETIVA,
            {
                "ano_letivo": 2026,
                "dre_codigo": "108200",
                "ue_codigo": "094501",
                "semestre": 1,
                "modalidade": 5,
                "turma_codigo": "1234567",
                "alunos_codigo": [123, 456],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        service.listar_boletins.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade=5,
            alunos_codigo=[123, 456],
            considera_inativo=False,
            turma_codigo="1234567",
            bimestre=None,
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_sem_alunos_codigo_solicita_todos(self, service_class) -> None:
        """Usa uma lista vazia para selecionar todos os alunos."""
        service = service_class.return_value
        service.listar_boletins.return_value = []

        response = self.client.get(
            _URL_COLETIVA,
            {
                "ano_letivo": 2026,
                "dre_codigo": "108200",
                "ue_codigo": "094501",
                "semestre": 1,
                "modalidade": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            service.listar_boletins.call_args.kwargs["alunos_codigo"], []
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_permite_incluir_estudantes_inativos(self, service_class) -> None:
        """Encaminha a opção de imprimir estudantes inativos."""
        service = service_class.return_value
        service.listar_boletins.return_value = []

        response = self.client.get(
            _URL_COLETIVA,
            {
                "ano_letivo": 2026,
                "dre_codigo": "108200",
                "ue_codigo": "094501",
                "semestre": 1,
                "modalidade": 5,
                "considera_inativo": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            service.listar_boletins.call_args.kwargs["considera_inativo"]
        )

    def test_exige_contexto_da_consulta(self) -> None:
        """Retorna HTTP 400 quando os filtros de contexto estão ausentes."""
        response = self.client.get(_URL_COLETIVA, {"ano_letivo": 2026})

        self.assertEqual(response.status_code, 400)
        self.assertIn("dre_codigo", response.json())
        self.assertIn("ue_codigo", response.json())
        self.assertIn("semestre", response.json())
        self.assertIn("modalidade", response.json())

    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_semestre_zero(self, service_class) -> None:
        """Encaminha semestre zero na consulta coletiva."""
        service = service_class.return_value
        service.listar_boletins.return_value = []

        response = self.client.get(
            _URL_COLETIVA,
            {
                "ano_letivo": 2026,
                "dre_codigo": "108200",
                "ue_codigo": "094501",
                "semestre": 0,
                "modalidade": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            service.listar_boletins.call_args.kwargs["semestre"], 0
        )


class TestBoletinsPdfView(TestCase):
    """Valida o contrato HTTP da geração coletiva em PDF."""

    def setUp(self) -> None:
        """Prepara um cliente autenticado para os testes."""
        self.client = _cliente_autenticado()

    @patch("apps.boletim.api.views.GeradorBoletinsPdf")
    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_pdf_com_dois_boletins_por_padrao(
        self, service_class, gerador_class
    ) -> None:
        """Gera PDF inline e usa duas vias por página como no relatório."""
        boletins: list[dict[str, object]] = []
        service_class.return_value.listar_boletins.return_value = boletins
        gerador_class.return_value.gerar.return_value = b"%PDF-teste"

        response = self.client.get(_URL_PDF, self._filtros())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            'inline; filename="boletins-escolares.pdf"',
        )
        gerador_class.return_value.gerar.assert_called_once_with(
            boletins,
            boletins_por_pagina=2,
        )

    def test_rejeita_quantidade_de_boletins_nao_suportada(self) -> None:
        """Retorna HTTP 400 quando a paginação não é 1, 2 ou 6."""
        filtros = self._filtros()
        filtros["boletins_por_pagina"] = 4

        response = self.client.get(_URL_PDF, filtros)

        self.assertEqual(response.status_code, 400)
        self.assertIn("boletins_por_pagina", response.json())

    @patch("apps.boletim.api.views.GeradorBoletinsPdf")
    @patch("apps.boletim.api.views.BoletimService")
    def test_pdf_permite_incluir_estudantes_inativos(
        self, service_class, gerador_class
    ) -> None:
        """Encaminha estudantes inativos para a consulta do PDF."""
        service_class.return_value.listar_boletins.return_value = []
        gerador_class.return_value.gerar.return_value = b"%PDF-teste"
        filtros = self._filtros()
        filtros["considera_inativo"] = True

        response = self.client.get(_URL_PDF, filtros)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            service_class.return_value.listar_boletins.call_args.kwargs[
                "considera_inativo"
            ]
        )

    @staticmethod
    def _filtros() -> dict[str, int | str]:
        """Retorna os filtros mínimos aceitos pelo endpoint PDF."""
        return {
            "ano_letivo": 2026,
            "dre_codigo": "108200",
            "ue_codigo": "094501",
            "semestre": 1,
            "modalidade": 5,
        }


class TestDocumentacaoBoletim(TestCase):
    """Valida a documentação OpenAPI do boletim."""

    def test_documenta_query_parameters_em_snake_case(self) -> None:
        """Publica somente nomes em snake case nos filtros dos endpoints."""
        response = APIClient().get(
            "/boletim/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        esperados_por_caminho = {
            "/api/boletim/": {
                "ano_letivo",
                "dre_codigo",
                "ue_codigo",
                "semestre",
                "turma_codigo",
                "modalidade",
                "alunos_codigo",
                "considera_inativo",
                "bimestre",
            },
            "/api/boletim/pdf/": {
                "ano_letivo",
                "dre_codigo",
                "ue_codigo",
                "semestre",
                "turma_codigo",
                "modalidade",
                "alunos_codigo",
                "considera_inativo",
                "bimestre",
                "boletins_por_pagina",
            },
        }
        for caminho, esperados in esperados_por_caminho.items():
            parametros = schema["paths"][caminho]["get"]["parameters"]
            nomes = {parametro["name"] for parametro in parametros}

            self.assertEqual(nomes, esperados)

    def test_descreve_enum_modalidade_nos_endpoints(self) -> None:
        """Documenta nomes e siglas de todas as modalidades aceitas."""
        response = APIClient().get(
            "/boletim/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        for caminho in (
            "/api/boletim/",
            "/api/boletim/pdf/",
        ):
            parametros = schema["paths"][caminho]["get"]["parameters"]
            modalidade = next(
                parametro
                for parametro in parametros
                if parametro["name"] == "modalidade"
            )
            for codigo, descricao in MODALIDADES_CHOICES:
                self.assertIn(
                    f"`{codigo}` - {descricao}",
                    modalidade["description"],
                )


class TestEndpointAlunoRemovido(TestCase):
    """Valida a remoção da consulta individual de boletim."""

    def test_rota_individual_nao_existe(self) -> None:
        """Retorna HTTP 404 para o endpoint individual removido."""
        response = _cliente_autenticado().get(
            "/api/boletim/alunos/123/",
            {"ano_letivo": 2026},
        )

        self.assertEqual(response.status_code, 404)
