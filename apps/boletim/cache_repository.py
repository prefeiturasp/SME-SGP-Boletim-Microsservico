"""Cache dos boletins consolidados."""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager

from django.conf import settings

from apps.core.cache import CacheRepository


class BoletimCacheRepository:
    """Armazena boletins consolidados no cache compartilhado."""

    def __init__(
        self,
        cache_repository: CacheRepository | None = None,
    ) -> None:
        """Inicializa o repositório com o cache compartilhado.

        Args:
            cache_repository: Repositório genérico opcional para testes.
        """
        self._cache_repository = cache_repository or CacheRepository()

    @staticmethod
    def gerar_chave(
        ano_letivo: int,
        dre_codigo: str,
        ue_codigo: str,
        semestre: int,
        modalidade: int,
        alunos_codigo: list[int],
        considera_inativo: bool,
        turma_codigo: str | None,
        bimestre: int | None,
    ) -> str:
        """Gera uma chave determinística a partir dos filtros da consulta."""
        filtros = {
            "alunos_codigo": sorted(set(alunos_codigo)),
            "ano_letivo": ano_letivo,
            "bimestre": bimestre,
            "considera_inativo": considera_inativo,
            "dre_codigo": dre_codigo,
            "modalidade": modalidade,
            "semestre": semestre,
            "turma_codigo": turma_codigo,
            "ue_codigo": ue_codigo,
        }
        conteudo = json.dumps(
            filtros,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        resumo = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
        return f"boletim:consulta:{resumo}"

    def obter(self, chave: str) -> list[dict[str, object]] | None:
        """Busca boletins sem interromper a consulta em falhas do cache."""
        resultado = self._cache_repository.obter(chave)
        return resultado if isinstance(resultado, list) else None

    def armazenar(
        self,
        chave: str,
        boletins: list[dict[str, object]],
    ) -> None:
        """Armazena boletins pelo TTL definido no ambiente."""
        self._cache_repository.armazenar(
            chave,
            boletins,
            ttl=settings.CACHE_BOLETIM_TTL,
        )

    @contextmanager
    def bloquear(self, chave: str) -> Iterator[bool]:
        """Protege a criação de uma entrada contra processamento duplicado."""
        with self._cache_repository.bloquear(
            chave,
            ttl=settings.CACHE_LOCK_TTL,
            espera=settings.CACHE_LOCK_WAIT_TIMEOUT,
        ) as adquirido:
            yield adquirido
