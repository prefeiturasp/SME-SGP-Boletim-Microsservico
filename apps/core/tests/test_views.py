"""Testes das views técnicas do microsserviço."""

from uuid import UUID

from django.test import TestCase
from rest_framework.test import APIClient
from sme_sidecar_sdk import runtime


class TestHealthView(TestCase):
    """Valida o endpoint de saúde da aplicação."""

    def test_health_e_publico_e_retorna_identificacao(self) -> None:
        """Retorna HTTP 200 sem exigir API key."""
        response = APIClient().get("/api/boletim/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "servico": "sme_sgp_boletim_ms"},
        )

    def test_health_gera_identificador_de_correlacao(self) -> None:
        """Gera e devolve um identificador quando o cliente não o envia."""
        response = APIClient().get("/api/boletim/health/")

        request_id = response["X-Request-ID"]
        self.assertEqual(str(UUID(request_id)), request_id)

    def test_health_preserva_identificador_de_correlacao(self) -> None:
        """Preserva na resposta o identificador enviado pelo cliente."""
        request_id = "requisicao-boletim-123"

        response = APIClient().get(
            "/api/boletim/health/",
            HTTP_X_REQUEST_ID=request_id,
        )

        self.assertEqual(response["X-Request-ID"], request_id)


class TestSidecarSdk(TestCase):
    """Valida a inicialização do runtime compartilhado."""

    def test_runtime_esta_configurado_no_boot_do_django(self) -> None:
        """Mantém o runtime configurado pelo `CoreConfig`."""
        self.assertIsNotNone(runtime.state())
