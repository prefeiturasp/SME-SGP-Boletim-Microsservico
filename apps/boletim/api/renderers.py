"""Renderers HTTP do domínio de boletim."""

from collections.abc import Mapping
from typing import Any, cast

from rest_framework.renderers import BaseRenderer, JSONRenderer


class PdfRenderer(BaseRenderer):
    """Permite negociar arquivos PDF e mantém erros em JSON."""

    media_type = "application/pdf"
    format = "pdf"
    charset = None
    render_style = "binary"

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        """Renderiza bytes de PDF ou delega respostas de erro ao JSON."""
        if isinstance(data, bytes):
            return data

        if renderer_context is not None:
            response = renderer_context.get("response")
            if response is not None:
                response["Content-Type"] = "application/json"
        return cast(bytes, JSONRenderer().render(data))
