"""Renderizadores HTTP compartilhados."""

from collections.abc import Mapping
from typing import Any, cast

import orjson
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.renderers import BaseRenderer

_DJANGO_JSON_ENCODER = DjangoJSONEncoder()


class OrjsonRenderer(BaseRenderer):
    """Serializa respostas JSON diretamente em bytes com orjson."""

    media_type = "application/json"
    format = "json"
    charset = None

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        """Converte o payload diretamente para bytes UTF-8."""
        if data is None:
            return b""
        return cast(
            bytes,
            orjson.dumps(data, default=_DJANGO_JSON_ENCODER.default),
        )
