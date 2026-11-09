"""Testes dos renderizadores HTTP compartilhados."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.core.renderers import OrjsonRenderer


class TestOrjsonRenderer(SimpleTestCase):
    """Valida a serialização JSON otimizada."""

    def test_serializa_diretamente_em_bytes(self) -> None:
        """Preserva caracteres e tipos suportados pelo codificador Django."""
        resultado = OrjsonRenderer().render(
            {
                "mensagem": "Geração concluída",
                "data": date(2026, 11, 3),
                "nota": Decimal("9.5"),
            }
        )

        self.assertEqual(
            resultado,
            b'{"mensagem":"Gera\xc3\xa7\xc3\xa3o conclu\xc3\xadda",'
            b'"data":"2026-11-03","nota":"9.5"}',
        )

    def test_nao_renderiza_corpo_para_valor_nulo(self) -> None:
        """Retorna bytes vazios quando a resposta não possui conteúdo."""
        self.assertEqual(OrjsonRenderer().render(None), b"")
