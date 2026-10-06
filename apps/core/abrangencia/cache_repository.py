"""Cache compartilhado das abrangências vigentes."""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager

from django.conf import settings

from apps.core.abrangencia.models import Abrangencia
from apps.core.cache import CacheRepository


class AbrangenciaCacheRepository:
    """Armazena abrangências por login e perfil no cache compartilhado."""

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
    def gerar_chave(login: str, perfil: str) -> str:
        """Gera uma chave sem expor login e perfil no backend de cache.

        Args:
            login: Login autenticado presente no JWT.
            perfil: UUID normalizado do perfil selecionado.

        Returns:
            Chave determinística identificada pelo domínio de abrangência.
        """
        identidade = json.dumps(
            {"login": login.strip().lower(), "perfil": perfil},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        resumo = hashlib.sha256(identidade.encode("utf-8")).hexdigest()
        return f"abrangencia:vigente:{resumo}"

    def obter(self, chave: str) -> Abrangencia | None:
        """Busca uma abrangência válida no cache.

        Args:
            chave: Chave gerada para o login e o perfil.

        Returns:
            Abrangência armazenada ou `None` quando não houver valor válido.
        """
        resultado = self._cache_repository.obter(chave)
        return resultado if isinstance(resultado, Abrangencia) else None

    def armazenar(self, chave: str, abrangencia: Abrangencia) -> None:
        """Armazena uma abrangência pelo TTL configurado.

        Args:
            chave: Chave gerada para o login e o perfil.
            abrangencia: Resposta válida obtida da API Pedagógica.
        """
        self._cache_repository.armazenar(
            chave,
            abrangencia,
            ttl=settings.CACHE_ABRANGENCIA_TTL,
        )

    @contextmanager
    def bloquear(self, chave: str) -> Iterator[bool]:
        """Protege o preenchimento contra chamadas externas duplicadas.

        Args:
            chave: Chave da abrangência que será preenchida.

        Yields:
            `True` quando o lock foi adquirido; caso contrário, `False`.
        """
        with self._cache_repository.bloquear(
            chave,
            ttl=settings.CACHE_LOCK_TTL,
            espera=settings.CACHE_LOCK_WAIT_TIMEOUT,
        ) as adquirido:
            yield adquirido
