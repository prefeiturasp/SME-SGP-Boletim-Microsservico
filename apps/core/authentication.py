"""Autenticação por API key ou token Bearer JWT."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import jwt
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

if TYPE_CHECKING:
    from rest_framework.request import Request


class _ApiAuth:
    """Representa o consumidor autenticado pela API key."""

    is_authenticated = True
    is_active = True
    is_staff = False
    is_anonymous = False

    def __str__(self) -> str:
        return "api-user"


class ApiKeyAuthentication(BaseAuthentication):
    """Valida requisições com a API key configurada no ambiente."""

    def authenticate(self, request: Request) -> tuple[_ApiAuth, None] | None:
        """Autentica a requisição ou rejeita uma chave inválida."""
        header_name = getattr(settings, "API_KEY_HEADER", "x-api-key")
        expected_key = getattr(settings, "API_KEY", "")
        meta_key = "HTTP_" + header_name.upper().replace("-", "_")
        provided_key = request.META.get(meta_key)
        if provided_key is None:
            return None
        if provided_key != expected_key:
            raise exceptions.AuthenticationFailed("API Key inválida.")
        return (_ApiAuth(), None)

    def authenticate_header(self, request: Request) -> str:
        """Retorna o nome do header esperado para autenticação."""
        return getattr(settings, "API_KEY_HEADER", "x-api-key")


class _BearerAuth:
    """Representa o consumidor autenticado pelas claims do JWT."""

    is_authenticated = True
    is_active = True
    is_staff = False
    is_anonymous = False

    def __init__(self, claims: dict[str, object]) -> None:
        self.claims = claims

    def __str__(self) -> str:
        subject = self.claims.get("sub")
        return str(subject) if subject is not None else "bearer-user"


class BearerTokenAuthentication(BaseAuthentication):
    """Valida tokens Bearer JWT emitidos pela aplicação autorizadora."""

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[_BearerAuth, str] | None:
        """Autentica um JWT com assinatura, expiração, emissor e audiência."""
        authorization = request.headers.get("Authorization")
        if authorization is None:
            return None

        parts = authorization.split()
        if not parts or parts[0].lower() != self.keyword.lower():
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed(
                "Header Authorization Bearer inválido."
            )

        signing_key = getattr(settings, "BEARER_TOKEN_SIGNING_KEY", "")
        issuer = getattr(settings, "BEARER_TOKEN_ISSUER", "")
        audience = getattr(settings, "BEARER_TOKEN_AUDIENCE", "")
        algorithms = getattr(settings, "BEARER_TOKEN_ALGORITHMS", ["HS256"])
        if not signing_key or not issuer or not audience:
            raise exceptions.AuthenticationFailed(
                "Autenticação Bearer não configurada."
            )

        try:
            claims = jwt.decode(
                parts[1],
                signing_key,
                algorithms=algorithms,
                audience=audience,
                issuer=issuer,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as error:
            raise exceptions.AuthenticationFailed(
                "Token Bearer inválido ou expirado."
            ) from error

        return (_BearerAuth(cast(dict[str, object], claims)), parts[1])

    def authenticate_header(self, request: Request) -> str:
        """Informa o esquema de autenticação usado pelo header."""
        return self.keyword


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Descreve a autenticação por API key no OpenAPI."""

    target_class = ApiKeyAuthentication
    name = "ApiKey"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        """Retorna a definição OpenAPI da API key configurada."""
        return {
            "type": "apiKey",
            "name": getattr(settings, "API_KEY_HEADER", "x-api-key"),
            "in": "header",
        }


class BearerTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """Descreve a autenticação por JWT no OpenAPI."""

    target_class = BearerTokenAuthentication
    name = "BearerAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        """Retorna a definição OpenAPI do token Bearer."""
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
