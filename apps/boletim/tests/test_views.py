"""Testes das views de boletim."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.abrangencia.exceptions import (
    ServicoAbrangenciaIndisponivel,
)
from apps.abrangencia.models import Abrangencia, TipoAbrangencia
from apps.boletim.apresentador import montar_contexto_exibicao
from apps.boletim.serializers import MODALIDADES_CHOICES

_URL_COLETIVA = "/api/boletim/"
_URL_ULTIMA_ATUALIZACAO = "/api/boletim/ultima-atualizacao/"


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


def _contexto(
    boletins: list[dict[str, object]] | None = None,
    boletins_por_pagina: int = 2,
) -> dict[str, object]:
    """Cria um contexto de exibição válido para os testes da view."""
    return dict(
        montar_contexto_exibicao(
            boletins if boletins is not None else [_boletim()],
            boletins_por_pagina,
        )
    )


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

    def test_permite_preflight_sem_autenticacao(self) -> None:
        """Responde ao preflight antes de exigir autenticação."""
        client = APIClient()

        response = client.options(
            _URL_COLETIVA,
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, accept",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "http://localhost:3000",
        )
        self.assertIn("GET", response["Access-Control-Allow-Methods"])
        self.assertIn(
            "authorization", response["Access-Control-Allow-Headers"]
        )
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        self.assertIn("origin", response["Vary"].lower())

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_contexto_de_exibicao_de_varios_alunos(
        self, service_class
    ) -> None:
        """Aceita vários alunos e retorna o contexto pronto para exibição."""
        service = service_class.return_value
        service.obter_contexto_exibicao.return_value = _contexto()

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
        payload = response.json()
        self.assertEqual(payload["boletins_por_pagina"], 2)
        self.assertEqual(payload["total_paginas"], 1)
        self.assertEqual(
            payload["paginas"][0]["linhas"][0]["boletins"][0]["nome_aluno"],
            "Estudante",
        )
        service.obter_contexto_exibicao.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade=5,
            alunos_codigo=[123, 456],
            considera_inativo=False,
            turma_codigo="1234567",
            bimestre=None,
            boletins_por_pagina=2,
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_aplica_quantidade_de_boletins_por_pagina(
        self, service_class
    ) -> None:
        """Organiza o contexto conforme a densidade solicitada."""
        service_class.return_value.obter_contexto_exibicao.return_value = (
            _contexto([_boletim(), _boletim()], 1)
        )

        response = self.client.get(
            _URL_COLETIVA,
            {
                "ano_letivo": 2026,
                "dre_codigo": "108200",
                "ue_codigo": "094501",
                "semestre": 1,
                "modalidade": 5,
                "boletins_por_pagina": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_paginas"], 2)

    @patch("apps.boletim.api.views.BoletimService")
    def test_sem_alunos_codigo_solicita_todos(self, service_class) -> None:
        """Usa uma lista vazia para selecionar todos os alunos."""
        service = service_class.return_value
        service.obter_contexto_exibicao.return_value = _contexto()

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
            service.obter_contexto_exibicao.call_args.kwargs["alunos_codigo"],
            [],
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_permite_incluir_estudantes_inativos(self, service_class) -> None:
        """Encaminha a opção de imprimir estudantes inativos."""
        service = service_class.return_value
        service.obter_contexto_exibicao.return_value = _contexto()

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
            service.obter_contexto_exibicao.call_args.kwargs[
                "considera_inativo"
            ]
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
    @patch("apps.abrangencia.service.AbrangenciaClient.obter_vigente")
    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_token_bearer_em_alternativa_a_api_key(
        self, service_class, obter_abrangencia
    ) -> None:
        """Autoriza a consulta com JWT sem exigir API key."""
        service_class.return_value.obter_contexto_exibicao.return_value = (
            _contexto()
        )
        obter_abrangencia.return_value = Abrangencia(
            tipo=TipoAbrangencia.UE,
            dres=frozenset(),
            ues=frozenset({"094501"}),
            turmas=frozenset(),
        )
        token = jwt.encode(
            {
                "sub": "aplicacao-consumidora",
                "login": "1234567",
                "perfil": "0d81666c-27c8-4e43-a41c-0c9d2764de91",
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
        obter_abrangencia.assert_called_once_with(
            "1234567", "0d81666c-27c8-4e43-a41c-0c9d2764de91"
        )

    @override_settings(
        BEARER_TOKEN_SIGNING_KEY="segredo-de-integracao-com-32-chars",
        BEARER_TOKEN_ISSUER="aplicacao-dotnet",
        BEARER_TOKEN_AUDIENCE="boletim-api",
        BEARER_TOKEN_ALGORITHMS=["HS256"],
    )
    @patch("apps.abrangencia.service.AbrangenciaClient.obter_vigente")
    def test_rejeita_jwt_sem_abrangencia_na_ue(
        self, obter_abrangencia
    ) -> None:
        """Retorna HTTP 403 quando a UE não pertence ao usuário."""
        obter_abrangencia.return_value = Abrangencia(
            tipo=TipoAbrangencia.UE,
            dres=frozenset(),
            ues=frozenset({"outra-ue"}),
            turmas=frozenset(),
        )
        token = jwt.encode(
            {
                "login": "1234567",
                "perfil": "0d81666c-27c8-4e43-a41c-0c9d2764de91",
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

        self.assertEqual(response.status_code, 403)

    @override_settings(
        BEARER_TOKEN_SIGNING_KEY="segredo-de-integracao-com-32-chars",
        BEARER_TOKEN_ISSUER="aplicacao-dotnet",
        BEARER_TOKEN_AUDIENCE="boletim-api",
        BEARER_TOKEN_ALGORITHMS=["HS256"],
    )
    @patch("apps.abrangencia.service.AbrangenciaClient.obter_vigente")
    @patch("apps.boletim.api.views.BoletimService")
    def test_rejeita_consulta_quando_turma_esta_fora_da_abrangencia(
        self, service_class, obter_abrangencia
    ) -> None:
        """Rejeita a consulta se uma turma repetida não for permitida."""
        obter_abrangencia.return_value = Abrangencia(
            tipo=TipoAbrangencia.PROFESSOR,
            dres=frozenset(),
            ues=frozenset(),
            turmas=frozenset({"3026635"}),
        )
        token = jwt.encode(
            {
                "login": "1234567",
                "perfil": "0d81666c-27c8-4e43-a41c-0c9d2764de91",
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
            _URL_COLETIVA
            + "?ano_letivo=2026&dre_codigo=108100&ue_codigo=019715"
            "&semestre=0&modalidade=5&boletins_por_pagina=2"
            "&turma_codigo=2853538&turma_codigo=3026635"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            "A turma 2853538 não está na abrangência do usuário.",
        )
        service_class.assert_not_called()

    @override_settings(
        BEARER_TOKEN_SIGNING_KEY="segredo-de-integracao-com-32-chars",
        BEARER_TOKEN_ISSUER="aplicacao-dotnet",
        BEARER_TOKEN_AUDIENCE="boletim-api",
        BEARER_TOKEN_ALGORITHMS=["HS256"],
    )
    @patch("apps.abrangencia.permissions.AbrangenciaService.obter_vigente")
    def test_retorna_indisponibilidade_como_string_json(
        self, obter_abrangencia
    ) -> None:
        """Retorna HTTP 503 com a mensagem sem o envelope `detail`."""
        obter_abrangencia.side_effect = ServicoAbrangenciaIndisponivel()
        token = jwt.encode(
            {
                "login": "1234567",
                "perfil": "0d81666c-27c8-4e43-a41c-0c9d2764de91",
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

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            "Serviço de abrangência temporariamente indisponível.",
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_semestre_zero(self, service_class) -> None:
        """Encaminha semestre zero na consulta coletiva."""
        service = service_class.return_value
        service.obter_contexto_exibicao.return_value = _contexto()

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
            service.obter_contexto_exibicao.call_args.kwargs["semestre"],
            0,
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_sem_conteudo_quando_nao_ha_dados(
        self, service_class
    ) -> None:
        """Retorna HTTP 204 sem corpo quando a consulta está vazia."""
        service_class.return_value.obter_contexto_exibicao.return_value = None

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


class TestUltimaAtualizacaoBoletimView(TestCase):
    """Valida o contrato HTTP da última atualização do boletim."""

    def setUp(self) -> None:
        """Prepara um cliente autenticado para os testes."""
        self.client = _cliente_autenticado()

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_atualizacao_global_sem_filtros(
        self, service_class
    ) -> None:
        """Retorna a maior atualização global sem exigir parâmetros."""
        service_class.return_value.obter_ultima_atualizacao.return_value = (
            datetime(2026, 10, 13, 12, 30, tzinfo=UTC)
        )

        response = self.client.get(_URL_ULTIMA_ATUALIZACAO)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"ultimaAtualizacao": "2026-10-13T09:30:00-03:00"},
        )
        service_class.return_value.obter_ultima_atualizacao.assert_called_once_with(
            {}
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_encaminha_filtros_opcionais(self, service_class) -> None:
        """Valida e encaminha somente os filtros enviados pelo cliente."""
        service_class.return_value.obter_ultima_atualizacao.return_value = None

        response = self.client.get(
            _URL_ULTIMA_ATUALIZACAO,
            {
                "ano_letivo": 2026,
                "modalidade": 5,
                "alunos_codigo": [123, 456],
                "considera_inativo": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ultimaAtualizacao": None})
        service_class.return_value.obter_ultima_atualizacao.assert_called_once_with(
            {
                "ano_letivo": 2026,
                "modalidade": 5,
                "alunos_codigo": [123, 456],
                "considera_inativo": False,
            }
        )


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
                "boletins_por_pagina",
            },
            "/api/boletim/ultima-atualizacao/": {
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
            "/api/boletim/ultima-atualizacao/",
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


class TestEndpointsRemovidos(TestCase):
    """Valida as rotas que não pertencem mais ao microsserviço."""

    def test_rota_individual_nao_existe(self) -> None:
        """Retorna HTTP 404 para o endpoint individual removido."""
        response = _cliente_autenticado().get(
            "/api/boletim/alunos/123/",
            {"ano_letivo": 2026},
        )

        self.assertEqual(response.status_code, 404)

    def test_rota_pdf_nao_existe(self) -> None:
        """Retorna HTTP 404 para a antiga geração de PDF."""
        response = _cliente_autenticado().get("/api/boletim/pdf/")

        self.assertEqual(response.status_code, 404)
