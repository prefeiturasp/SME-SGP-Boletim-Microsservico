"""Configuração do app de abrangência."""

from django.apps import AppConfig


class AbrangenciaConfig(AppConfig):
    """Configura o domínio de abrangência institucional."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.abrangencia"
