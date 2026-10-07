"""Tipos usados na autorização institucional por abrangência."""

from dataclasses import dataclass
from enum import IntEnum


class TipoAbrangencia(IntEnum):
    """Representa os tipos publicados pela API Pedagógica."""

    UE = 1
    PROFESSOR = 2
    UE_TURMAS_DISCIPLINAS = 3
    DRE = 4
    DRE_ESCOLAS_ATRIBUIDAS = 5
    SME = 6


@dataclass(frozen=True)
class Abrangencia:
    """Contém os códigos autorizados para um usuário e perfil."""

    tipo: TipoAbrangencia
    dres: frozenset[str]
    ues: frozenset[str]
    turmas: frozenset[str]


@dataclass(frozen=True)
class RecursoAbrangencia:
    """Identifica o recurso institucional que será consultado."""

    dre_codigo: str | None = None
    ue_codigo: str | None = None
    turma_codigo: str | None = None
