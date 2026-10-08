"""Testes do cache dos boletins."""

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

    def test_ausencia_de_valor_retorna_cache_vazio(self) -> None:
        """Representa a ausência de valor como cache miss."""
        cache_repository = MagicMock()
        cache_repository.obter.return_value = None

        resultado = BoletimCacheRepository(cache_repository).obter("chave")

        self.assertIsNone(resultado)

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
