"""Testes do acesso compartilhado ao cache."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.cache import CacheRepository, preservar_chave_cache


class TestCacheRepository(SimpleTestCase):
    """Valida o acesso genérico e tolerante a falhas ao cache."""

    def test_preserva_chave_sem_versao_do_backend(self) -> None:
        """Evita que o Django acrescente versão ou prefixo à chave."""
        resultado = preservar_chave_cache("dominio:recurso:abc", "sme", 1)

        self.assertEqual(resultado, "dominio:recurso:abc")

    def test_armazena_valor_com_ttl_informado(self) -> None:
        """Permite que cada caso de uso defina seu tempo de vida."""
        cache = MagicMock()
        repository = CacheRepository(cache)

        repository.armazenar("chave", {"valor": 1}, ttl=300)

        cache.set.assert_called_once_with(
            "chave",
            {"valor": 1},
            timeout=300,
        )

    def test_falha_de_leitura_retorna_cache_vazio(self) -> None:
        """Permite continuar o caso de uso quando o cache falha."""
        cache = MagicMock()
        cache.get.side_effect = ConnectionError("KeyDB indisponível")

        with self.assertLogs("apps.core.cache", level="ERROR"):
            resultado = CacheRepository(cache).obter("chave")

        self.assertIsNone(resultado)

    def test_falha_de_escrita_nao_interrompe_fluxo(self) -> None:
        """Ignora a indisponibilidade durante a escrita no cache."""
        cache = MagicMock()
        cache.set.side_effect = ConnectionError("KeyDB indisponível")

        with self.assertLogs("apps.core.cache", level="ERROR"):
            CacheRepository(cache).armazenar("chave", "valor", ttl=300)

    def test_lock_adquirido_e_liberado(self) -> None:
        """Mantém o lock apenas durante o bloco protegido."""
        cache = MagicMock()
        cliente_redis = MagicMock()
        lock = cliente_redis.lock.return_value
        lock.acquire.return_value = True
        repository = CacheRepository(cache, cliente_redis)

        with repository.bloquear("recurso:1", ttl=30, espera=2) as adquirido:
            self.assertTrue(adquirido)
            lock.release.assert_not_called()

        cliente_redis.lock.assert_called_once_with(
            "lock:recurso:1",
            timeout=30,
            blocking_timeout=2,
        )
        lock.acquire.assert_called_once_with(blocking=True)
        lock.release.assert_called_once_with()

    def test_lock_ocupado_nao_e_liberado(self) -> None:
        """Não libera um lock pertencente a outro processamento."""
        cache = MagicMock()
        cliente_redis = MagicMock()
        lock = cliente_redis.lock.return_value
        lock.acquire.return_value = False
        repository = CacheRepository(cache, cliente_redis)

        with repository.bloquear("recurso:1", ttl=30, espera=2) as adquirido:
            self.assertFalse(adquirido)

        lock.release.assert_not_called()
