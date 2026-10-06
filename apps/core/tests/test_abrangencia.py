"""Testes das regras compartilhadas de abrangência."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.core.abrangencia.cache_repository import (
    AbrangenciaCacheRepository,
)
from apps.core.abrangencia.client import AbrangenciaClient
from apps.core.abrangencia.exceptions import (
    ServicoAbrangenciaIndisponivel,
)
from apps.core.abrangencia.models import (
    Abrangencia,
    RecursoAbrangencia,
    TipoAbrangencia,
)
from apps.core.abrangencia.service import AbrangenciaService


class TestAbrangenciaClient(SimpleTestCase):
    """Valida o mapeamento do contrato do Pedagógico."""

    def test_mapeia_resposta_camel_case(self) -> None:
        """Converte códigos e tipo da resposta camelCase."""
        resultado = AbrangenciaClient._mapear(
            {
                "abrangencia": {"abrangencia": 2},
                "idDres": ["108200"],
                "idUes": ["094501"],
                "idTurmas": [1234567],
            }
        )

        self.assertEqual(resultado.tipo, TipoAbrangencia.PROFESSOR)
        self.assertEqual(resultado.turmas, frozenset({"1234567"}))

    def test_mapeia_colecoes_nulas(self) -> None:
        """Interpreta coleções nulas como conjuntos vazios."""
        resultado = AbrangenciaClient._mapear(
            {
                "Abrangencia": {"Abrangencia": 4},
                "IdDres": ["108200"],
                "IdUes": None,
                "IdTurmas": None,
            }
        )

        self.assertEqual(resultado.tipo, TipoAbrangencia.DRE)
        self.assertEqual(resultado.ues, frozenset())

    @override_settings(
        PEDAGOGICO_API_URL="https://pedagogico.test",
        PEDAGOGICO_API_KEY="chave-interna",
        PEDAGOGICO_API_KEY_HEADER="x-api-eol-key",
    )
    @patch("apps.core.abrangencia.client.build_http_client")
    def test_consulta_com_cliente_http_do_sdk(self, construir_cliente) -> None:
        """Usa o cliente do SDK com contexto e configurações institucionais."""
        cliente = MagicMock()
        cliente.get.return_value.json.return_value = {
            "abrangencia": {"abrangencia": 1},
            "idDres": [],
            "idUes": ["094501"],
            "idTurmas": None,
        }
        construir_cliente.return_value.__enter__.return_value = cliente

        resultado = AbrangenciaClient().obter_vigente(
            "1234567",
            "0d81666c-27c8-4e43-a41c-0c9d2764de91",
        )

        construir_cliente.assert_called_once_with(
            "sme-pedagogico-api",
            base_url="https://pedagogico.test",
        )
        cliente.get.assert_called_once_with(
            "/api/abrangencia/compacta-vigente/1234567/perfil/"
            "0d81666c-27c8-4e43-a41c-0c9d2764de91",
            headers={"x-api-eol-key": "chave-interna"},
        )
        self.assertEqual(resultado.tipo, TipoAbrangencia.UE)


class TestAbrangenciaCacheRepository(SimpleTestCase):
    """Valida o cache compartilhado das abrangências vigentes."""

    def test_chave_normaliza_login_e_nao_expoe_identidade(self) -> None:
        """Gera a mesma chave sem armazenar login e perfil em texto aberto."""
        primeira = AbrangenciaCacheRepository.gerar_chave(
            " Usuario.Teste ",
            "0d81666c-27c8-4e43-a41c-0c9d2764de91",
        )
        segunda = AbrangenciaCacheRepository.gerar_chave(
            "usuario.teste",
            "0d81666c-27c8-4e43-a41c-0c9d2764de91",
        )

        self.assertEqual(primeira, segunda)
        self.assertTrue(primeira.startswith("abrangencia:vigente:"))
        self.assertNotIn("usuario.teste", primeira)

    @override_settings(CACHE_ABRANGENCIA_TTL=300)
    def test_armazena_somente_pelo_ttl_configurado(self) -> None:
        """Encaminha a abrangência válida com o TTL institucional."""
        cache = MagicMock()
        repository = AbrangenciaCacheRepository(cache)
        abrangencia = Abrangencia(
            TipoAbrangencia.UE,
            frozenset(),
            frozenset({"094501"}),
            frozenset(),
        )

        repository.armazenar("chave", abrangencia)

        cache.armazenar.assert_called_once_with(
            "chave",
            abrangencia,
            ttl=300,
        )


class TestAbrangenciaService(SimpleTestCase):
    """Valida decisões de acesso por granularidade institucional."""

    def setUp(self) -> None:
        """Prepara o serviço usado nos cenários."""
        self.service = AbrangenciaService()
        self.recurso = RecursoAbrangencia(
            dre_codigo="108200",
            ue_codigo="094501",
            turma_codigo="1234567",
        )

    def test_reutiliza_abrangencia_encontrada_no_cache(self) -> None:
        """Não chama o Pedagógico quando existe uma resposta válida."""
        abrangencia = Abrangencia(
            TipoAbrangencia.UE,
            frozenset(),
            frozenset({"094501"}),
            frozenset(),
        )
        client = MagicMock()
        cache = MagicMock()
        cache.gerar_chave.return_value = "chave"
        cache.obter.return_value = abrangencia
        service = AbrangenciaService(client, cache)

        resultado = service.obter_vigente("1234567", "perfil")

        self.assertEqual(resultado, abrangencia)
        client.obter_vigente.assert_not_called()

    def test_armazena_resposta_valida_apos_adquirir_lock(self) -> None:
        """Preenche o cache uma vez quando não existe valor armazenado."""
        abrangencia = Abrangencia(
            TipoAbrangencia.DRE,
            frozenset({"108200"}),
            frozenset(),
            frozenset(),
        )
        client = MagicMock()
        client.obter_vigente.return_value = abrangencia
        cache = MagicMock()
        cache.gerar_chave.return_value = "chave"
        cache.obter.side_effect = [None, None]
        cache.bloquear.return_value.__enter__.return_value = True
        service = AbrangenciaService(client, cache)

        resultado = service.obter_vigente("1234567", "perfil")

        self.assertEqual(resultado, abrangencia)
        client.obter_vigente.assert_called_once_with("1234567", "perfil")
        cache.armazenar.assert_called_once_with("chave", abrangencia)

    def test_nao_armazena_falha_da_api_pedagogica(self) -> None:
        """Propaga indisponibilidade sem contaminar o cache."""
        client = MagicMock()
        client.obter_vigente.side_effect = ServicoAbrangenciaIndisponivel()
        cache = MagicMock()
        cache.gerar_chave.return_value = "chave"
        cache.obter.side_effect = [None, None]
        cache.bloquear.return_value.__enter__.return_value = True
        service = AbrangenciaService(client, cache)

        with self.assertRaises(ServicoAbrangenciaIndisponivel):
            service.obter_vigente("1234567", "perfil")

        cache.armazenar.assert_not_called()

    def test_professor_exige_turma_atribuida(self) -> None:
        """Autoriza professor somente em turma retornada pelo Pedagógico."""
        abrangencia = Abrangencia(
            TipoAbrangencia.PROFESSOR,
            frozenset(),
            frozenset(),
            frozenset({"1234567"}),
        )

        self.assertTrue(self.service.pode_acessar(abrangencia, self.recurso))

    def test_ue_exige_unidade_atribuida(self) -> None:
        """Nega uma UE que não pertence ao perfil."""
        abrangencia = Abrangencia(
            TipoAbrangencia.UE,
            frozenset(),
            frozenset({"outra-ue"}),
            frozenset(),
        )

        self.assertFalse(self.service.pode_acessar(abrangencia, self.recurso))

    def test_tipo_sem_regra_e_negado(self) -> None:
        """Falha de modo fechado para abrangência ainda não suportada."""
        abrangencia = Abrangencia(
            TipoAbrangencia.DRE_ESCOLAS_ATRIBUIDAS,
            frozenset({"108200"}),
            frozenset({"094501"}),
            frozenset(),
        )

        self.assertFalse(self.service.pode_acessar(abrangencia, self.recurso))
