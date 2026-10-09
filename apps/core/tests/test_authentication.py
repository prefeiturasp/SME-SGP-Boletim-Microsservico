"""Testes da autenticação por API key e token Bearer."""

from datetime import UTC, datetime, timedelta

import jwt
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.core.authentication import (
    ApiKeyAuthentication,
    BearerTokenAuthentication,
)


@override_settings(API_KEY="chave-valida", API_KEY_HEADER="x-api-key")
class TestApiKeyAuthentication(SimpleTestCase):
    """Valida os cenários da autenticação por API key."""

    def setUp(self) -> None:
        """Prepara a fábrica de requisições e o autenticador."""
        self.factory = APIRequestFactory()
        self.authentication = ApiKeyAuthentication()

    def test_sem_chave_nao_autentica(self) -> None:
        """Retorna None quando o consumidor não informa a chave."""
        request = self.factory.get("/api/boletim/recurso/")
        self.assertIsNone(self.authentication.authenticate(request))

    def test_chave_invalida_e_rejeitada(self) -> None:
        """Rejeita uma chave diferente da configuração."""
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_X_API_KEY="incorreta"
        )
        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)

    def test_chave_valida_autentica(self) -> None:
        """Retorna o consumidor quando a chave coincide."""
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_X_API_KEY="chave-valida"
        )
        result = self.authentication.authenticate(request)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(str(result[0]), "api-user")


@override_settings(
    BEARER_TOKEN_SIGNING_KEY="segredo-de-teste-com-32-caracteres",
    BEARER_TOKEN_ISSUER="aplicacao-dotnet",
    BEARER_TOKEN_AUDIENCE="boletim-api",
    BEARER_TOKEN_ALGORITHMS=["HS256"],
)
class TestBearerTokenAuthentication(SimpleTestCase):
    """Valida os cenários da autenticação por JWT."""

    def setUp(self) -> None:
        """Prepara a fábrica de requisições e o autenticador."""
        self.factory = APIRequestFactory()
        self.authentication = BearerTokenAuthentication()

    @staticmethod
    def _token(**claims: object) -> str:
        """Gera um JWT válido, permitindo sobrescrever suas claims."""
        payload = {
            "sub": "aplicacao-consumidora",
            "iss": "aplicacao-dotnet",
            "aud": "boletim-api",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        }
        payload.update(claims)
        return jwt.encode(
            payload,
            "segredo-de-teste-com-32-caracteres",
            algorithm="HS256",
        )

    def test_sem_authorization_nao_autentica(self) -> None:
        """Retorna None quando não há header Authorization."""
        request = self.factory.get("/api/boletim/recurso/")

        self.assertIsNone(self.authentication.authenticate(request))

    def test_token_valido_autentica_e_disponibiliza_claims(self) -> None:
        """Retorna o consumidor e suas claims para um JWT válido."""
        token = self._token()
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        result = self.authentication.authenticate(request)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(str(result[0]), "aplicacao-consumidora")
        self.assertEqual(result[0].claims["aud"], "boletim-api")

    def test_token_expirado_e_rejeitado(self) -> None:
        """Rejeita JWT cuja expiração já ocorreu."""
        token = self._token(exp=datetime.now(UTC) - timedelta(seconds=1))
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)

    def test_token_com_assinatura_invalida_e_rejeitado(self) -> None:
        """Rejeita JWT assinado por uma chave diferente."""
        token = jwt.encode(
            {
                "iss": "aplicacao-dotnet",
                "aud": "boletim-api",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            "outro-segredo-com-pelo-menos-32-chars",
            algorithm="HS256",
        )
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)

    def test_header_bearer_malformado_e_rejeitado(self) -> None:
        """Rejeita Bearer sem exatamente uma credencial."""
        request = self.factory.get(
            "/api/boletim/recurso/", HTTP_AUTHORIZATION="Bearer"
        )

        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)
