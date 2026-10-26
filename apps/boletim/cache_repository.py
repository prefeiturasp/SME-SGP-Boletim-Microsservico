"""Cache dos boletins consolidados."""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

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
            "alunos_codigo": alunos_codigo,
            "ano_letivo": ano_letivo,
            "bimestre": bimestre,
            "considera_inativo": considera_inativo,
            "dre_codigo": dre_codigo,
            "modalidade": modalidade,
            "semestre": semestre,
            "turma_codigo": turma_codigo,
            "ue_codigo": ue_codigo,
        }
        resumo = BoletimCacheRepository._gerar_resumo(filtros)
        return f"boletim:consulta:{resumo}"

    def obter(self, chave: str) -> list[dict[str, object]] | None:
        """Busca boletins sem interromper a consulta em falhas do cache."""
        resultado = self._cache_repository.obter(chave)
        return resultado if isinstance(resultado, list) else None

    @staticmethod
    def gerar_chave_ultima_atualizacao(
        filtros: dict[str, object],
    ) -> str:
        """Gera a chave da última atualização com filtros normalizados."""
        resumo = BoletimCacheRepository._gerar_resumo(filtros)
        return f"boletim:ultima-atualizacao:{resumo}"

    @staticmethod
    def _gerar_resumo(filtros: dict[str, object]) -> str:
        """Normaliza os filtros e gera seu resumo SHA-256."""
        filtros_normalizados = {
            nome: sorted(set(valor)) if isinstance(valor, list) else valor
            for nome, valor in filtros.items()
        }
        conteudo = json.dumps(
            filtros_normalizados,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    def obter_ultima_atualizacao(
        self,
        chave: str,
    ) -> tuple[bool, datetime | None]:
        """Busca a atualização e diferencia valor nulo de cache miss."""
        resultado = self._cache_repository.obter(chave)
        if not isinstance(resultado, dict):
            return False, None
        atualizacao = resultado.get("ultima_atualizacao")
        if atualizacao is not None and not isinstance(atualizacao, datetime):
            return False, None
        return True, atualizacao

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

    def armazenar_ultima_atualizacao(
        self,
        chave: str,
        ultima_atualizacao: datetime | None,
    ) -> None:
        """Armazena a atualização por dois minutos por padrão."""
        self._cache_repository.armazenar(
            chave,
            {"ultima_atualizacao": ultima_atualizacao},
            ttl=settings.CACHE_ULTIMA_ATUALIZACAO_TTL,
        )

    @staticmethod
    def gerar_chave_pdf(chave_consulta: str, boletins_por_pagina: int) -> str:
        """Gera a chave do PDF a partir da chave da consulta e do layout."""
        resumo = chave_consulta.rsplit(":", 1)[-1]
        return f"boletim:pdf:{resumo}:{boletins_por_pagina}"

    def obter_pdf(self, chave: str) -> bytes | None:
        """Busca o PDF renderizado sem interromper falhas do cache."""
        resultado = self._cache_repository.obter(chave)
        return resultado if isinstance(resultado, bytes) else None

    def armazenar_pdf(self, chave: str, pdf: bytes) -> None:
        """Armazena o PDF renderizado pelo TTL definido no ambiente."""
        self._cache_repository.armazenar(
            chave,
            pdf,
            ttl=settings.CACHE_PDF_TTL,
        )

    @contextmanager
    def bloquear_pdf(self, chave: str) -> Iterator[bool]:
        """Evita renderizações simultâneas do mesmo PDF."""
        with self._cache_repository.bloquear(
            chave,
            ttl=settings.CACHE_PDF_LOCK_TTL,
            espera=settings.CACHE_LOCK_WAIT_TIMEOUT,
        ) as adquirido:
            yield adquirido

    @contextmanager
    def bloquear(self, chave: str) -> Iterator[bool]:
        """Protege a criação de uma entrada contra processamento duplicado."""
        with self._cache_repository.bloquear(
            chave,
            ttl=settings.CACHE_LOCK_TTL,
            espera=settings.CACHE_LOCK_WAIT_TIMEOUT,
        ) as adquirido:
            yield adquirido
