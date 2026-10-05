"""Testes das views de boletim."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.boletim.serializers import MODALIDADES_CHOICES

_URL_COLETIVA = "/api/boletim/"
_URL_PDF = "/api/boletim/pdf/"


def _boletim() -> dict[str, object]:
    """Cria um boletim mínimo válido para os testes da view."""
    return {
        "dados_aluno": {
            "ano_letivo": 2026,
            "modalidade_codigo": 5,
            "semestre": 1,
            "dre_codigo": "108200",
            "dre_nome": "DRE",
            "ue_codigo": "094501",
            "ue_nome": "UE",
            "turma_codigo": "1234567",
            "turma_nome": "Turma",
            "ciclo": None,
            "aluno_codigo": 123,
            "numero_chamada": None,
            "aluno_nome": "Estudante",
            "nome_social": None,
        },
        "componentes": [],
        "regencias": [],
    }


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
        service.listar_boletins.return_value = [_boletim()]

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
        self.assertEqual(len(response.json()), 1)
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
        service.listar_boletins.return_value = [_boletim()]

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
        service.listar_boletins.return_value = [_boletim()]

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

    @override_settings(
        BEARER_TOKEN_SIGNING_KEY="segredo-de-integracao-com-32-chars",
        BEARER_TOKEN_ISSUER="aplicacao-dotnet",
        BEARER_TOKEN_AUDIENCE="boletim-api",
        BEARER_TOKEN_ALGORITHMS=["HS256"],
    )
    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_token_bearer_em_alternativa_a_api_key(
        self, service_class
    ) -> None:
        """Autoriza a consulta com JWT sem exigir API key."""
        service_class.return_value.listar_boletins.return_value = [_boletim()]
        token = jwt.encode(
            {
                "sub": "aplicacao-consumidora",
                "iss": "aplicacao-dotnet",
                "aud": "boletim-api",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            "segredo-de-integracao-com-32-chars",
            algorithm="HS256",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.get(
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

    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_semestre_zero(self, service_class) -> None:
        """Encaminha semestre zero na consulta coletiva."""
        service = service_class.return_value
        service.listar_boletins.return_value = [_boletim()]

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

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_sem_conteudo_quando_nao_ha_dados(
        self, service_class
    ) -> None:
        """Retorna HTTP 204 sem corpo quando a consulta está vazia."""
        service_class.return_value.listar_boletins.return_value = []

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

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(
            response["X-Mensagem"],
            "Alunos da turma não foram encontrados.",
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
        boletins = [_boletim()]
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
    def test_negocia_pdf_solicitado_pelo_swagger(
        self, service_class, gerador_class
    ) -> None:
        """Aceita o media type de PDF enviado pelo Swagger UI."""
        service_class.return_value.listar_boletins.return_value = [_boletim()]
        gerador_class.return_value.gerar.return_value = b"%PDF-teste"

        response = self.client.get(
            _URL_PDF,
            self._filtros(),
            HTTP_ACCEPT="application/pdf",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-teste")

    def test_mantem_erro_em_json_quando_swagger_solicita_pdf(self) -> None:
        """Retorna validação em JSON mesmo sob negociação de PDF."""
        response = self.client.get(
            _URL_PDF,
            {"ano_letivo": 2026},
            HTTP_ACCEPT="application/pdf",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("dre_codigo", response.json())

    @patch("apps.boletim.api.views.GeradorBoletinsPdf")
    @patch("apps.boletim.api.views.BoletimService")
    def test_pdf_permite_incluir_estudantes_inativos(
        self, service_class, gerador_class
    ) -> None:
        """Encaminha estudantes inativos para a consulta do PDF."""
        service_class.return_value.listar_boletins.return_value = [_boletim()]
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

    @patch("apps.boletim.api.views.GeradorBoletinsPdf")
    @patch("apps.boletim.api.views.BoletimService")
    def test_pdf_retorna_sem_conteudo_quando_nao_ha_dados(
        self, service_class, gerador_class
    ) -> None:
        """Retorna HTTP 204 sem corpo nem PDF quando a consulta está vazia."""
        service_class.return_value.listar_boletins.return_value = []

        response = self.client.get(_URL_PDF, self._filtros())

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(
            response["X-Mensagem"],
            "Alunos da turma não foram encontrados.",
        )
        gerador_class.return_value.gerar.assert_not_called()

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

    def test_documenta_respostas_do_endpoint_pdf(self) -> None:
        """Documenta o PDF e a resposta sem conteúdo com sua mensagem."""
        response = APIClient().get(
            "/boletim/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        respostas = response.json()["paths"]["/api/boletim/pdf/"]["get"][
            "responses"
        ]
        self.assertIn("application/pdf", respostas["200"]["content"])
        self.assertNotIn("content", respostas["204"])
        self.assertEqual(
            respostas["204"]["headers"]["X-Mensagem"]["schema"]["type"],
            "string",
        )

    def test_documenta_api_key_ou_bearer_como_alternativas(self) -> None:
        """Publica os dois esquemas de autenticação em relação OU."""
        response = APIClient().get(
            "/boletim/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        schema = response.json()
        self.assertEqual(
            schema["paths"]["/api/boletim/"]["get"]["security"],
            [{"ApiKey": []}, {"BearerAuth": []}],
        )
        self.assertEqual(
            schema["components"]["securitySchemes"]["BearerAuth"]["scheme"],
            "bearer",
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
