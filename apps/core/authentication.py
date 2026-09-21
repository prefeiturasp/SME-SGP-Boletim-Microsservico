"""Autenticação por API key."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
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
