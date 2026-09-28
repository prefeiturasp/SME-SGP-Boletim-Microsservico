"""Configuração do app compartilhado core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configura os recursos compartilhados do microsserviço."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self) -> None:
        """Inicializa observabilidade e resiliência no processo."""
        from sme_sidecar_sdk import runtime

        runtime.configure()
