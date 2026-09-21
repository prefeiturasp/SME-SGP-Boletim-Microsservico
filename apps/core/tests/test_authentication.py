"""Testes da autenticação por API key."""

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.core.authentication import ApiKeyAuthentication


@override_settings(API_KEY="chave-valida", API_KEY_HEADER="x-api-key")
class TestApiKeyAuthentication(SimpleTestCase):
    """Valida os cenários da autenticação por API key."""

    def setUp(self) -> None:
        """Prepara a fábrica de requisições e o autenticador."""
        self.factory = APIRequestFactory()
        self.authentication = ApiKeyAuthentication()

    def test_sem_chave_nao_autentica(self) -> None:
        """Retorna None quando o consumidor não informa a chave."""
        request = self.factory.get("/api/v1/boletim/recurso/")
        self.assertIsNone(self.authentication.authenticate(request))

    def test_chave_invalida_e_rejeitada(self) -> None:
        """Rejeita uma chave diferente da configuração."""
        request = self.factory.get(
            "/api/v1/boletim/recurso/", HTTP_X_API_KEY="incorreta"
        )
        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)

    def test_chave_valida_autentica(self) -> None:
        """Retorna o consumidor quando a chave coincide."""
        request = self.factory.get(
            "/api/v1/boletim/recurso/", HTTP_X_API_KEY="chave-valida"
        )
        result = self.authentication.authenticate(request)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(str(result[0]), "api-user")
