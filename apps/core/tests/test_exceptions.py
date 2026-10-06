"""Testes do tratamento compartilhado de exceções HTTP."""

from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.test import APISimpleTestCase

from apps.core.exceptions import exception_handler


class TestExceptionHandler(APISimpleTestCase):
    """Valida a normalização dos erros produzidos pelo DRF."""

    def test_remove_envelope_detail_de_erro_simples(self) -> None:
        """Retorna diretamente a mensagem de uma exceção simples."""
        response = exception_handler(
            NotAuthenticated("Credencial inválida."),
            {},
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.data, "Credencial inválida.")

    def test_preserva_erros_estruturados_de_validacao(self) -> None:
        """Mantém o mapeamento de campos inválidos sem perda de contexto."""
        response = exception_handler(
            ValidationError({"login": ["Campo obrigatório."]}),
            {},
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(
            response.data,
            {"login": ["Campo obrigatório."]},
        )
