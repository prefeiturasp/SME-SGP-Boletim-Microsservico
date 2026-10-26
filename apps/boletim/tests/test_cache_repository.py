"""Testes do cache dos boletins."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings

from apps.boletim.cache_repository import BoletimCacheRepository


class TestBoletimCacheRepository(SimpleTestCase):
    """Valida chaves, TTL e tolerância a falhas do cache."""

    def test_gera_mesma_chave_para_alunos_em_ordens_diferentes(self) -> None:
        """Normaliza a ordem e as duplicidades dos códigos de alunos."""
        primeira = self._gerar_chave([30, 10, 20, 10])
        segunda = self._gerar_chave([10, 20, 30])

        self.assertEqual(primeira, segunda)
        self.assertTrue(primeira.startswith("boletim:consulta:"))

    def test_gera_chaves_distintas_para_filtros_diferentes(self) -> None:
        """Mantém filtros funcionais distintos em entradas separadas."""
        primeira = self._gerar_chave([10], turma_codigo="100")
        segunda = self._gerar_chave([10], turma_codigo="200")

        self.assertNotEqual(primeira, segunda)

    @override_settings(CACHE_BOLETIM_TTL=900)
    def test_armazena_com_ttl_configurado(self) -> None:
        """Usa a validade definida pelas configurações da aplicação."""
        cache_repository = MagicMock()
        repository = BoletimCacheRepository(cache_repository)
        boletins = [{"dados_aluno": {"aluno_codigo": 10}}]

        repository.armazenar("chave", boletins)

        cache_repository.armazenar.assert_called_once_with(
            "chave",
            boletins,
            ttl=900,
        )

    def test_chave_do_pdf_diferencia_boletins_por_pagina(self) -> None:
        """Separa PDFs da mesma consulta com layouts distintos."""
        chave_consulta = self._gerar_chave([10])

        um = BoletimCacheRepository.gerar_chave_pdf(chave_consulta, 1)
        dois = BoletimCacheRepository.gerar_chave_pdf(chave_consulta, 2)

        self.assertNotEqual(um, dois)
        self.assertTrue(um.startswith("boletim:pdf:"))
        self.assertTrue(um.endswith(":1"))

    @override_settings(CACHE_PDF_TTL=600)
    def test_armazena_pdf_com_ttl_configurado(self) -> None:
        """Usa a validade específica dos PDFs renderizados."""
        cache_repository = MagicMock()

        BoletimCacheRepository(cache_repository).armazenar_pdf(
            "chave",
            b"%PDF",
        )

        cache_repository.armazenar.assert_called_once_with(
            "chave",
            b"%PDF",
            ttl=600,
        )

    def test_descarta_pdf_com_tipo_inesperado(self) -> None:
        """Trata valores que não são bytes como cache miss."""
        cache_repository = MagicMock()
        cache_repository.obter.return_value = "texto"

        resultado = BoletimCacheRepository(cache_repository).obter_pdf("chave")

        self.assertIsNone(resultado)

    @override_settings(CACHE_PDF_LOCK_TTL=300, CACHE_LOCK_WAIT_TIMEOUT=2)
    def test_bloqueia_pdf_pelo_tempo_da_renderizacao(self) -> None:
        """Mantém o lock do PDF por mais tempo que o lock da consulta."""
        cache_repository = MagicMock()
        cache_repository.bloquear.return_value.__enter__.return_value = True

        with BoletimCacheRepository(cache_repository).bloquear_pdf(
            "chave"
        ) as adquirido:
            self.assertTrue(adquirido)

        cache_repository.bloquear.assert_called_once_with(
            "chave",
            ttl=300,
            espera=2,
        )

    def test_ausencia_de_valor_retorna_cache_vazio(self) -> None:
        """Representa a ausência de valor como cache miss."""
        cache_repository = MagicMock()
        cache_repository.obter.return_value = None

        resultado = BoletimCacheRepository(cache_repository).obter("chave")

        self.assertIsNone(resultado)

    def test_normaliza_filtros_da_chave_de_ultima_atualizacao(self) -> None:
        """Ignora a ordem dos alunos na chave da última atualização."""
        primeira = BoletimCacheRepository.gerar_chave_ultima_atualizacao(
            {"ano_letivo": 2026, "alunos_codigo": [30, 10, 30]}
        )
        segunda = BoletimCacheRepository.gerar_chave_ultima_atualizacao(
            {"alunos_codigo": [10, 30], "ano_letivo": 2026}
        )

        self.assertEqual(primeira, segunda)
        self.assertTrue(primeira.startswith("boletim:ultima-atualizacao:"))

    def test_diferencia_atualizacao_nula_de_cache_miss(self) -> None:
        """Reconhece como cache hit uma atualização armazenada como nula."""
        cache_repository = MagicMock()
        cache_repository.obter.return_value = {"ultima_atualizacao": None}

        resultado = BoletimCacheRepository(
            cache_repository
        ).obter_ultima_atualizacao("chave")

        self.assertEqual(resultado, (True, None))

    @override_settings(CACHE_ULTIMA_ATUALIZACAO_TTL=120)
    def test_armazena_ultima_atualizacao_por_dois_minutos(self) -> None:
        """Usa o TTL exclusivo de 120 segundos para a atualização."""
        cache_repository = MagicMock()
        atualizacao = datetime(2026, 10, 13, 12, 30, tzinfo=UTC)

        BoletimCacheRepository(cache_repository).armazenar_ultima_atualizacao(
            "chave", atualizacao
        )

        cache_repository.armazenar.assert_called_once_with(
            "chave",
            {"ultima_atualizacao": atualizacao},
            ttl=120,
        )

    @staticmethod
    def _gerar_chave(
        alunos_codigo: list[int],
        turma_codigo: str | None = "100",
    ) -> str:
        """Gera uma chave com o contexto padrão dos testes."""
        return BoletimCacheRepository.gerar_chave(
            ano_letivo=2026,
            dre_codigo="1",
            ue_codigo="2",
            semestre=1,
            modalidade=5,
            alunos_codigo=alunos_codigo,
            considera_inativo=False,
            turma_codigo=turma_codigo,
            bimestre=None,
        )
