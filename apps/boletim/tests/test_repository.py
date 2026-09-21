"""Testes do repositório de boletim."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.boletim.repository import BoletimRepository


class TestBoletimRepository(SimpleTestCase):
    """Valida a composição das consultas ORM de boletim."""

    @patch("apps.boletim.repository.Boletim.objects")
    def test_lista_boletim_com_filtro_de_bimestre(
        self, objects: MagicMock
    ) -> None:
        """Aplica aluno, ano e bimestre à consulta ORM."""
        query = MagicMock()
        objects.filter.return_value = query
        query.only.return_value = query
        query.order_by.return_value = query

        resultado = BoletimRepository().listar_por_aluno(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=1,
        )

        objects.filter.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            bimestre=1,
        )
        query.only.assert_called_once()
        query.order_by.assert_called_once_with(
            "bimestre",
            "disciplina_nome_sgp",
            "componente_codigo",
        )
        self.assertIs(resultado, query)

    @patch("apps.boletim.repository.Boletim.objects")
    def test_lista_boletim_sem_filtro_de_bimestre(
        self, objects: MagicMock
    ) -> None:
        """Não adiciona o bimestre quando o filtro não é informado."""
        query = MagicMock()
        objects.filter.return_value = query
        query.only.return_value = query
        query.order_by.return_value = query

        BoletimRepository().listar_por_aluno(123, 2026)

        objects.filter.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
        )

    @patch("apps.boletim.repository.Boletim.objects")
    def test_lista_boletim_com_filtros_de_contexto(
        self, objects: MagicMock
    ) -> None:
        """Aplica os identificadores usados pelo servidor de relatórios."""
        query = MagicMock()
        objects.filter.return_value = query
        query.only.return_value = query
        query.order_by.return_value = query

        BoletimRepository().listar_por_aluno(
            aluno_codigo=123,
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            turma_codigo="1234567",
            modalidade=5,
        )

        objects.filter.assert_called_once_with(
            aluno_codigo=123,
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            turma_codigo="1234567",
            modalidade_codigo=5,
        )

    @patch("apps.boletim.repository.Boletim.objects")
    def test_lista_varios_alunos(self, objects: MagicMock) -> None:
        """Filtra os códigos dos alunos quando eles são informados."""
        consulta = MagicMock()
        objects.filter.return_value = consulta
        consulta.filter.return_value = consulta
        consulta.only.return_value = consulta
        consulta.order_by.return_value = consulta

        BoletimRepository().listar_boletins(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade=5,
            alunos_codigo=[123, 456],
            turma_codigo="1234567",
        )

        objects.filter.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade_codigo=5,
            turma_codigo="1234567",
        )
        consulta.filter.assert_called_once_with(aluno_codigo__in=[123, 456])

    @patch("apps.boletim.repository.Boletim.objects")
    def test_lista_todos_os_alunos_quando_lista_vazia(
        self, objects: MagicMock
    ) -> None:
        """Não restringe aluno quando nenhum código é informado."""
        consulta = MagicMock()
        objects.filter.return_value = consulta
        consulta.only.return_value = consulta
        consulta.order_by.return_value = consulta

        BoletimRepository().listar_boletins(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade=5,
            alunos_codigo=[],
        )

        consulta.filter.assert_not_called()
