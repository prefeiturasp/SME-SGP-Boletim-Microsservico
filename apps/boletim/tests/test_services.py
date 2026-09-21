"""Testes dos serviços de boletim."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.boletim.models import Boletim
from apps.boletim.serializers import BoletimAlunoResponseSerializer
from apps.boletim.services import BoletimService


class TestBoletimService(SimpleTestCase):
    """Valida a orquestração das consultas de boletim."""

    def test_consulta_todos_os_bimestres_antes_de_aplicar_filtro(self) -> None:
        """Consulta o ano completo para preencher períodos vazios."""
        repository = MagicMock()
        repository.listar_por_aluno.return_value = []

        resultado = BoletimService(repository).listar_por_aluno(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=4,
        )

        repository.listar_por_aluno.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=None,
            dre_codigo=None,
            ue_codigo=None,
            semestre=None,
            turma_codigo=None,
            modalidade=None,
        )
        self.assertEqual(
            resultado,
            {"dados_aluno": None, "componentes": [], "regencias": []},
        )

    def test_encaminha_filtros_de_contexto_ao_repositorio(self) -> None:
        """Restringe a consulta ao contexto informado do boletim."""
        repository = MagicMock()
        repository.listar_por_aluno.return_value = []

        BoletimService(repository).listar_por_aluno(
            aluno_codigo=123,
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            turma_codigo="1234567",
            modalidade=5,
        )

        repository.listar_por_aluno.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=None,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            turma_codigo="1234567",
            modalidade=5,
        )

    def test_lista_boletins_agrupados_por_aluno(self) -> None:
        """Monta um boletim independente para cada aluno selecionado."""
        primeiro = self._registro(modalidade=5, bimestre=1)
        segundo = self._registro(modalidade=5, bimestre=1)
        segundo.aluno_codigo = 456
        segundo.aluno_nome = "Outro aluno"
        repository = MagicMock()
        repository.listar_boletins.return_value = [primeiro, segundo]

        resultado = BoletimService(repository).listar_boletins(
            ano_letivo=2026,
            dre_codigo="1",
            ue_codigo="2",
            semestre=1,
            modalidade=5,
            alunos_codigo=[123, 456],
        )

        self.assertEqual(len(resultado), 2)
        self.assertEqual(
            [item["dados_aluno"]["aluno_codigo"] for item in resultado],
            [123, 456],
        )
        repository.listar_boletins.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="1",
            ue_codigo="2",
            semestre=1,
            modalidade=5,
            alunos_codigo=[123, 456],
            turma_codigo=None,
        )

    def test_lista_boletins_retorna_vazio_sem_registros(self) -> None:
        """Retorna uma lista vazia quando não existem alunos no contexto."""
        repository = MagicMock()
        repository.listar_boletins.return_value = []

        resultado = BoletimService(repository).listar_boletins(
            ano_letivo=2026,
            dre_codigo="1",
            ue_codigo="2",
            semestre=1,
            modalidade=5,
            alunos_codigo=[],
        )

        self.assertEqual(resultado, [])

    def test_completa_quatro_bimestres_para_modalidade_anual(self) -> None:
        """Inclui períodos vazios para uma modalidade anual."""
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [
            self._registro(modalidade=5, bimestre=1)
        ]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        componentes = resultado["componentes"]
        self.assertIsInstance(componentes, list)
        bimestres = componentes[0]["bimestres"]
        self.assertEqual(
            [periodo["bimestre"] for periodo in bimestres],
            [1, 2, 3, 4],
        )
        self.assertEqual(bimestres[0]["nota"], 8)
        self.assertTrue(componentes[0]["lanca_nota"])
        self.assertTrue(componentes[0]["registra_frequencia"])
        self.assertEqual(componentes[0]["componente_territorio_codigo"], 4)
        self.assertEqual(componentes[0]["turma_regular_codigo"], "30")
        self.assertEqual(componentes[0]["turma_componente_codigo"], "3")
        self.assertEqual(componentes[0]["componente_pai_codigo"], 2)
        self.assertFalse(componentes[0]["regencia"])
        self.assertTrue(bimestres[0]["conselho_classe_cadastrado"])
        self.assertEqual(bimestres[0]["total_aulas_global"], 100)
        self.assertIsNone(bimestres[1]["nota"])
        self.assertIsNone(bimestres[1]["periodo_escolar_id"])
        self.assertFalse(bimestres[1]["conselho_classe_cadastrado"])

        resposta = BoletimAlunoResponseSerializer(resultado).data
        self.assertEqual(resposta["componentes"][0]["componentePaiCodigo"], 2)
        self.assertFalse(resposta["componentes"][0]["regencia"])
        self.assertEqual(
            resposta["componentes"][0]["bimestres"][0]["totalAulasGlobal"],
            100,
        )
        self.assertEqual(
            resposta["componentes"][0]["bimestres"][0]["tipoNota"],
            "N",
        )

    def test_completa_dois_bimestres_para_modalidade_semestral(self) -> None:
        """Limita EJA e CELP aos dois bimestres exibidos no boletim."""
        for modalidade in (3, 10):
            with self.subTest(modalidade=modalidade):
                repository = MagicMock()
                repository.listar_por_aluno.return_value = [
                    self._registro(modalidade=modalidade, bimestre=1)
                ]

                resultado = BoletimService(repository).listar_por_aluno(
                    123,
                    2026,
                )

                componentes = resultado["componentes"]
                self.assertIsInstance(componentes, list)
                self.assertEqual(
                    [
                        periodo["bimestre"]
                        for periodo in componentes[0]["bimestres"]
                    ],
                    [1, 2],
                )

    def test_oculta_nota_e_frequencia_sem_conselho_de_classe(self) -> None:
        """Replica a exibição vazia do relatório sem conselho."""
        registro = self._registro(modalidade=5, bimestre=1)
        registro.conselho_classe_cadastrado = False
        registro.nota = 7
        registro.conceito_id = 1
        registro.conceito = "S"
        registro.total_aulas = 20
        registro.total_presencas = 18
        registro.total_ausencias = 2
        registro.total_compensacoes = 1
        registro.total_remotos = 3
        registro.origem_frequencia = "COMPONENTE"
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [registro]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        bimestre = resultado["componentes"][0]["bimestres"][0]
        self.assertFalse(bimestre["conselho_classe_cadastrado"])
        for campo in (
            "nota",
            "conceito_id",
            "conceito",
            "total_aulas",
            "total_presencas",
            "total_ausencias",
            "total_compensacoes",
            "total_remotos",
            "origem_frequencia",
        ):
            with self.subTest(campo=campo):
                self.assertIsNone(bimestre[campo])

    def test_nao_exibe_terceiro_bimestre_para_modalidade_semestral(
        self,
    ) -> None:
        """Remove períodos que não são exibidos no boletim semestral."""
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [
            self._registro(modalidade=3, bimestre=3)
        ]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        componentes = resultado["componentes"]
        self.assertIsInstance(componentes, list)
        self.assertEqual(
            [periodo["bimestre"] for periodo in componentes[0]["bimestres"]],
            [1, 2],
        )

    def test_filtra_apos_completar_bimestre_sem_dados(self) -> None:
        """Retorna o bimestre solicitado mesmo quando não havia dados."""
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [
            self._registro(modalidade=5, bimestre=1)
        ]

        resultado = BoletimService(repository).listar_por_aluno(
            123,
            2026,
            bimestre=3,
        )

        componentes = resultado["componentes"]
        self.assertIsInstance(componentes, list)
        bimestres = componentes[0]["bimestres"]
        self.assertEqual(len(bimestres), 1)
        self.assertEqual(bimestres[0]["bimestre"], 3)
        self.assertIsNone(bimestres[0]["nota"])

    def test_agrupa_regencia_com_frequencia_no_pai_e_notas_nos_filhos(
        self,
    ) -> None:
        """Separa frequÃªncia comum das notas das disciplinas de regÃªncia."""
        primeiro = self._registro(modalidade=5, bimestre=1)
        primeiro.regencia = True
        primeiro.componente_pai_codigo = 99
        primeiro.componente_codigo = 4
        primeiro.total_aulas = 20
        segundo = self._registro(modalidade=5, bimestre=1)
        segundo.regencia = True
        segundo.componente_pai_codigo = 99
        segundo.componente_codigo = 5
        segundo.disciplina_nome = "CiÃªncias"
        segundo.disciplina_nome_sgp = "CiÃªncias"
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [primeiro, segundo]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        self.assertEqual(resultado["componentes"], [])
        regencia = resultado["regencias"][0]
        self.assertEqual(regencia["codigo"], 99)
        self.assertEqual(regencia["bimestres"][0]["total_aulas"], 20)
        self.assertIsNone(
            regencia["componentes"][0]["bimestres"][0]["total_aulas"]
        )
        self.assertEqual(
            regencia["componentes"][0]["bimestres"][0]["nota"],
            8,
        )

    def test_aplica_flags_de_exibicao_do_componente(self) -> None:
        """Oculta nota e frequÃªncia quando o componente nÃ£o as registra."""
        registro = self._registro(modalidade=5, bimestre=1)
        registro.lanca_nota = False
        registro.registra_frequencia = False
        registro.total_aulas = 20
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [registro]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        bimestre = resultado["componentes"][0]["bimestres"][0]
        self.assertIsNone(bimestre["nota"])
        self.assertIsNone(bimestre["total_aulas"])
        self.assertIsNone(bimestre["origem_frequencia"])

    def test_calcula_sintese_final_para_componente_sem_nota(self) -> None:
        """Calcula F ou NF com o parÃ¢metro anual no fechamento final."""
        registro = self._registro(modalidade=5, bimestre=0)
        registro.lanca_nota = False
        registro.total_aulas = 100
        registro.total_ausencias = 30
        registro.total_compensacoes = 0
        registro.media_frequencia = 75
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [registro]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        final = resultado["componentes"][0]["bimestres"][0]
        self.assertEqual(final["bimestre"], 0)
        self.assertEqual(final["sintese"], "NF")

    def test_calcula_sintese_final_quando_bimestre_for_nulo(self) -> None:
        """Reconhece bimestre nulo como fechamento final."""
        registro = self._registro(modalidade=5, bimestre=1)
        registro.bimestre = None
        registro.lanca_nota = False
        registro.total_aulas = 100
        registro.total_ausencias = 20
        registro.total_compensacoes = 0
        registro.media_frequencia = 75
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [registro]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        final = resultado["componentes"][0]["bimestres"][0]
        self.assertIsNone(final["bimestre"])
        self.assertEqual(final["sintese"], "F")

    def test_considera_frequente_sem_lancamentos_no_fechamento(self) -> None:
        """Replica a síntese F do relatório na ausência de frequência."""
        registro = self._registro(modalidade=5, bimestre=0)
        registro.lanca_nota = False
        registro.total_aulas = None
        registro.total_ausencias = None
        registro.media_frequencia = 75
        repository = MagicMock()
        repository.listar_por_aluno.return_value = [registro]

        resultado = BoletimService(repository).listar_por_aluno(123, 2026)

        final = resultado["componentes"][0]["bimestres"][0]
        self.assertEqual(final["sintese"], "F")

    @staticmethod
    def _registro(modalidade: int, bimestre: int) -> Boletim:
        """Crie uma linha mínima do boletim para os testes.

        Args:
            modalidade: Código da modalidade da turma.
            bimestre: Período associado ao registro.

        Returns:
            Instância não persistida usada pelos cenários de serviço.
        """
        return Boletim(
            aluno_codigo=123,
            ano_letivo=2026,
            modalidade_codigo=modalidade,
            semestre=1,
            dre_codigo="1",
            dre_nome="DRE",
            ue_codigo="2",
            ue_nome="UE",
            turma_codigo="3",
            turma_componente_codigo="3",
            turma_regular_codigo="30",
            turma_nome="Turma",
            bimestre=bimestre,
            periodo_escolar_id=10,
            componente_codigo=4,
            componente_territorio_codigo=4,
            componente_pai_codigo=2,
            lanca_nota=True,
            registra_frequencia=True,
            regencia=False,
            disciplina_nome="Matemática",
            disciplina_nome_sgp="Matemática",
            componente_existia_no_periodo=True,
            conselho_classe_cadastrado=True,
            nota=8,
            tipo_nota="N",
            tipo_nota_descricao="Nota",
            total_aulas_global=100,
        )
