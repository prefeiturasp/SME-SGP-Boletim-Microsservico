"""Infraestrutura compartilhada para autorização por abrangência."""

from apps.core.abrangencia.models import Abrangencia, RecursoAbrangencia
from apps.core.abrangencia.service import AbrangenciaService

__all__ = ["Abrangencia", "AbrangenciaService", "RecursoAbrangencia"]
