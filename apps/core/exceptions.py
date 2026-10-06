"""Tratamento compartilhado das exceções HTTP do microsserviço."""

from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """Remove o envelope `detail` dos erros simples do DRF.

    Respostas de validação com campos ou múltiplas propriedades permanecem
    estruturadas. Somente objetos cujo único campo seja `detail` são
    convertidos para o respectivo valor JSON.

    Args:
        exc: Exceção capturada durante o processamento da requisição.
        context: Contexto fornecido pelo Django REST Framework.

    Returns:
        Resposta HTTP tratada ou `None` para uma exceção desconhecida.
    """
    response = drf_exception_handler(exc, context)
    if (
        response is not None
        and isinstance(response.data, dict)
        and set(response.data) == {"detail"}
    ):
        response.data = response.data["detail"]
    return response
