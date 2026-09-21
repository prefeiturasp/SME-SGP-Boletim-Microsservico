"""Configuração do app de boletim."""

from django.apps import AppConfig


class BoletimConfig(AppConfig):
    """Configura o domínio de boletim."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.boletim"
