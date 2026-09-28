"""Views técnicas compartilhadas pelo microsserviço."""

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import HealthSerializer


class BaseAPIView(APIView):
    """Base autenticada para as views de negócio do microsserviço."""


class HealthView(APIView):
    """Expõe o estado básico do processo sem consultar dependências."""

    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        responses={200: HealthSerializer},
        operation_id="boletim_health",
        tags=["Infraestrutura"],
        auth=[],
    )
    def get(self, _request: Request) -> Response:
        """Retorna sucesso quando o processo está apto a responder HTTP."""
        return Response({"status": "ok", "servico": "sme_sgp_boletim_ms"})
