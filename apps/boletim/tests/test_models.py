"""Testes dos models de leitura de boletim."""

from django.test import SimpleTestCase

from apps.boletim.models import Boletim


class TestBoletimModel(SimpleTestCase):
    """Valida o mapeamento ORM da view materializada."""

    def test_mapeia_view_como_nao_gerenciada(self) -> None:
        """Mantém a view fora do gerenciamento de schema do Django."""
        self.assertEqual(Boletim._meta.db_table, "mv_boletim")
        self.assertFalse(Boletim._meta.managed)

    def test_usa_aluno_como_chave_tecnica_do_orm(self) -> None:
        """Evita que o ORM tente consultar uma coluna `id` inexistente."""
        self.assertEqual(Boletim._meta.pk.name, "aluno_codigo")

    def test_mapeia_situacao_da_matricula(self) -> None:
        """Disponibiliza o código usado para filtrar alunos ativos."""
        campo = Boletim._meta.get_field("codigo_situacao_matricula")

        self.assertFalse(campo.null)

    def test_mapeia_numero_chamada(self) -> None:
        """Disponibiliza o número de chamada consolidado pela ETL."""
        campo = Boletim._meta.get_field("numero_chamada")

        self.assertTrue(campo.null)
