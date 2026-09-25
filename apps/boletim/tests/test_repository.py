"""Testes do repositório de boletim."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.boletim.constantes import CODIGO_SITUACAO_ALUNO_ATIVO
from apps.boletim.repository import BoletimRepository


class TestBoletimRepository(SimpleTestCase):
    """Valida a composição das consultas ORM de boletim."""

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
            considera_inativo=False,
            turma_codigo="1234567",
        )

        objects.filter.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade_codigo=5,
            turma_codigo="1234567",
            codigo_situacao_matricula__in=CODIGO_SITUACAO_ALUNO_ATIVO,
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
            considera_inativo=True,
        )

        objects.filter.assert_called_once_with(
            ano_letivo=2026,
            dre_codigo="108200",
            ue_codigo="094501",
            semestre=1,
            modalidade_codigo=5,
        )
        consulta.filter.assert_not_called()
