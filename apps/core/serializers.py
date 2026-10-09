"""Contratos HTTP compartilhados pelo microsserviço."""

from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    """Representa o estado básico da aplicação."""

    status = serializers.CharField()
    servico = serializers.CharField()
