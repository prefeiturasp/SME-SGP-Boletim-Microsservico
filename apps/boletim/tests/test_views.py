"""Testes das views de boletim."""

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.boletim.serializers import MODALIDADES_CHOICES

_URL = "/api/v1/boletim/alunos/123/"
_URL_COLETIVA = "/api/v1/boletim/"


def _cliente_autenticado() -> APIClient:
    """Cria um cliente com a API key definida nas configurações."""
    client = APIClient()
    header = "HTTP_" + settings.API_KEY_HEADER.upper().replace("-", "_")
    client.credentials(**{header: settings.API_KEY})
    return client


class TestBoletimAlunoView(TestCase):
    """Valida o contrato HTTP da consulta por aluno."""

    def setUp(self) -> None:
        """Prepara um cliente autenticado para os testes."""
        self.client = _cliente_autenticado()

    def test_exige_ano_letivo(self) -> None:
        """Retorna HTTP 400 quando o ano letivo não é informado."""
        response = self.client.get(_URL)
        self.assertEqual(response.status_code, 400)
        self.assertIn("anoLetivo", response.json())

    def test_rejeita_bimestre_nao_positivo(self) -> None:
        """Retorna HTTP 400 quando o bimestre não é positivo."""
        response = self.client.get(_URL, {"anoLetivo": 2026, "bimestre": 0})
        self.assertEqual(response.status_code, 400)
        self.assertIn("bimestre", response.json())

    def test_rejeita_bimestre_maior_que_quatro(self) -> None:
        """Retorna HTTP 400 quando o bimestre excede o ano letivo."""
        response = self.client.get(_URL, {"anoLetivo": 2026, "bimestre": 5})
        self.assertEqual(response.status_code, 400)
        self.assertIn("bimestre", response.json())

    @patch("apps.boletim.api.views.BoletimService")
    def test_retorna_resultado_do_servico(self, service_class) -> None:
        """Retorna HTTP 200 e encaminha os filtros validados."""
        service = service_class.return_value
        service.listar_por_aluno.return_value = {
            "dados_aluno": None,
            "componentes": [],
            "regencias": [],
        }

        response = self.client.get(_URL, {"anoLetivo": 2026, "bimestre": 4})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"dadosAluno": None, "componentes": [], "regencias": []},
        )
        service.listar_por_aluno.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=4,
            dre_codigo=None,
            ue_codigo=None,
            semestre=None,
            turma_codigo=None,
            modalidade=None,
        )

    @patch("apps.boletim.api.views.BoletimService")
    def test_encaminha_parametros_do_servidor_de_relatorios(
        self, service_class
    ) -> None:
        """Encaminha os filtros de contexto do boletim ao serviço."""
        service = service_class.return_value
        service.listar_por_aluno.return_value = {
            "dados_aluno": None,
            "componentes": [],
            "regencias": [],
        }

        response = self.client.get(
            _URL,
            {
                "anoLetivo": 2026,
                "dreCodigo": "108200",
                "ueCodigo": "094501",
                "semestre": 1,
                "turmaCodigo": "1234567",
                "modalidade": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        service.listar_por_aluno.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=None,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            turma_codigo="1234567",
            modalidade=5,
        )

    def test_rejeita_modalidade_desconhecida(self) -> None:
        """Retorna HTTP 400 para modalidade não suportada."""
        response = self.client.get(
            _URL,
            {"anoLetivo": 2026, "modalidade": 2},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("modalidade", response.json())

    @patch("apps.boletim.api.views.BoletimService")
    def test_aceita_semestre_zero(self, service_class) -> None:
        """Aceita semestre zero quando não se aplica à modalidade."""
        service = service_class.return_value
        service.listar_por_aluno.return_value = {
            "dados_aluno": None,
            "componentes": [],
            "regencias": [],
        }

        response = self.client.get(
            _URL,
            {"anoLetivo": 2026, "semestre": 0},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            service.listar_por_aluno.call_args.kwargs["semestre"], 0
        )

    def test_exige_api_key(self) -> None:
        """Retorna HTTP 401 quando a API key não é enviada."""
        response = APIClient().get(_URL, {"anoLetivo": 2026})
        self.assertEqual(response.status_code, 401)


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
                "anoLetivo": 2026,
                "dreCodigo": "108200",
                "ueCodigo": "094501",
                "semestre": 1,
                "modalidade": 5,
                "turmaCodigo": "1234567",
                "alunosCodigo": [123, 456],
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
                "anoLetivo": 2026,
                "dreCodigo": "108200",
                "ueCodigo": "094501",
                "semestre": 1,
                "modalidade": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            service.listar_boletins.call_args.kwargs["alunos_codigo"], []
        )

    def test_exige_contexto_da_consulta(self) -> None:
        """Retorna HTTP 400 quando os filtros de contexto estão ausentes."""
        response = self.client.get(_URL_COLETIVA, {"anoLetivo": 2026})

        self.assertEqual(response.status_code, 400)
        self.assertIn("dreCodigo", response.json())
        self.assertIn("ueCodigo", response.json())
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
                "anoLetivo": 2026,
                "dreCodigo": "108200",
                "ueCodigo": "094501",
                "semestre": 0,
                "modalidade": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            service.listar_boletins.call_args.kwargs["semestre"], 0
        )


class TestDocumentacaoBoletim(TestCase):
    """Valida a documentação OpenAPI do boletim."""

    def test_descreve_enum_modalidade_nos_endpoints(self) -> None:
        """Documenta nomes e siglas de todas as modalidades aceitas."""
        response = APIClient().get(
            "/boletim/api/v1/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        for caminho in (
            "/api/v1/boletim/",
            "/api/v1/boletim/alunos/{aluno_codigo}/",
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
