"""Rotas principais do microsserviço de boletim."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny

from apps.core.views import HealthView

urlpatterns = [
    path("api/boletim/health/", HealthView.as_view(), name="health"),
    path("api/boletim/", include("apps.boletim.api.urls")),
    path(
        "boletim/api/schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="schema",
    ),
    path(
        "boletim/api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
]
