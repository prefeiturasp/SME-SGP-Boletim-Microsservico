"""Testes da geração otimizada dos boletins em PDF."""

from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.boletim.relatorios.gerador_pdf import (
    GeradorBoletinsPdf,
    _mesclar_pdfs,
)


class TestGeradorBoletinsPdf(SimpleTestCase):
    """Valida a divisão em lotes e o despacho da renderização."""

    @patch("apps.boletim.relatorios.gerador_pdf.montar_contexto_pdf")
    @patch("apps.boletim.relatorios.gerador_pdf._renderizar_lote")
    def test_renderiza_lote_unico_sem_paralelismo(
        self,
        renderizar_lote_mock: MagicMock,
        montar_contexto_mock: MagicMock,
    ) -> None:
        """Evita o custo de processos filhos quando cabe em um lote só."""
        paginas = [{"linhas": []} for _ in range(20)]
        montar_contexto_mock.return_value = {
            "paginas": paginas,
            "boletins_por_pagina": 2,
            "data_impressao": "22/09/2026",
        }
        renderizar_lote_mock.return_value = b"%PDF-um-lote"

        pdf = GeradorBoletinsPdf().gerar([], 2)

        self.assertEqual(pdf, b"%PDF-um-lote")
        renderizar_lote_mock.assert_called_once()
        tamanho = len(renderizar_lote_mock.call_args.args[0]["paginas"])
        self.assertEqual(tamanho, 20)

    @patch("apps.boletim.relatorios.gerador_pdf.montar_contexto_pdf")
    @patch("apps.boletim.relatorios.gerador_pdf._mesclar_pdfs")
    @patch.object(GeradorBoletinsPdf, "_renderizar_lotes_em_paralelo")
    def test_renderiza_lotes_em_paralelo_para_documento_grande(
        self,
        paralelo_mock: MagicMock,
        mesclar_mock: MagicMock,
        montar_contexto_mock: MagicMock,
    ) -> None:
        """Divide documentos grandes em lotes de até 20 páginas.

        Turmas grandes ou consultas sem `turmaCodigo` geram muitas páginas;
        renderizar tudo em um processo só não aproveita os núcleos
        disponíveis, então lotes acima do primeiro são despachados para
        `_renderizar_lotes_em_paralelo` e depois mesclados em bytes.
        """
        paginas = [{"linhas": []} for _ in range(41)]
        montar_contexto_mock.return_value = {
            "paginas": paginas,
            "boletins_por_pagina": 2,
            "data_impressao": "22/09/2026",
        }
        paralelo_mock.return_value = [b"lote-1", b"lote-2", b"lote-3"]
        mesclar_mock.return_value = b"%PDF-mesclado"

        pdf = GeradorBoletinsPdf().gerar([], 2)

        self.assertEqual(pdf, b"%PDF-mesclado")
        lotes = paralelo_mock.call_args.args[0]
        tamanhos = [len(lote["paginas"]) for lote in lotes]
        self.assertEqual(tamanhos, [20, 20, 1])
        mesclar_mock.assert_called_once_with([b"lote-1", b"lote-2", b"lote-3"])

    @patch("apps.boletim.relatorios.gerador_pdf.montar_contexto_pdf")
    @patch("apps.boletim.relatorios.gerador_pdf._renderizar_lote")
    def test_renderiza_mensagem_quando_nao_existem_boletins(
        self,
        renderizar_lote_mock: MagicMock,
        montar_contexto_mock: MagicMock,
    ) -> None:
        """Mantém o PDF informativo quando a consulta não encontra dados."""
        contexto = {
            "paginas": [],
            "boletins_por_pagina": 2,
            "data_impressao": "22/09/2026",
        }
        montar_contexto_mock.return_value = contexto
        renderizar_lote_mock.return_value = b"%PDF-vazio"

        pdf = GeradorBoletinsPdf().gerar([], 2)

        self.assertEqual(pdf, b"%PDF-vazio")
        renderizar_lote_mock.assert_called_once_with(contexto)

    def test_template_alinha_colunas_e_nao_corta_conteudo(self) -> None:
        """Usa colunas fixas e permite crescimento vertical do boletim."""
        contexto = {
            "paginas": [
                {
                    "linhas": [
                        {
                            "boletins": [
                                {
                                    "dados": {
                                        "ano_letivo": 2026,
                                        "dre_nome": "DRE",
                                        "ue_nome": "UE",
                                        "aluno_codigo": 1,
                                        "turma_relatorio": "EF - 4A",
                                        "ciclo": "",
                                    },
                                    "nome_aluno": "Aluno",
                                    "frequencia_global": "100.00%",
                                    "periodos": (1, 2, 3, 4, 0),
                                    "usa_conceito": False,
                                    "grupos": [],
                                    "exibe_legenda": False,
                                    "parecer_conclusivo": "",
                                    "recomendacoes_aluno": "<p>Teste</p>",
                                    "recomendacoes_familia": "",
                                    "exibe_recomendacoes": True,
                                }
                            ]
                        }
                    ]
                }
            ],
            "boletins_por_pagina": 2,
        }

        html = render_to_string("boletim/relatorios/boletins.html", contexto)

        self.assertIn("table-layout: fixed", html)
        self.assertNotIn("overflow: hidden", html)
        self.assertIn("<p>Teste</p>", html)
        self.assertNotIn('<td width="10%"></td>', html)


class TestMesclarPdfs(SimpleTestCase):
    """Valida a composição final dos PDFs renderizados por lote."""

    @patch("apps.boletim.relatorios.gerador_pdf.PdfWriter")
    def test_mescla_um_lote_por_vez_e_escreve_o_resultado(
        self,
        writer_cls_mock: MagicMock,
    ) -> None:
        """Anexa cada lote ao escritor final, na ordem recebida."""
        escritor_mock = writer_cls_mock.return_value
        escritor_mock.write.side_effect = lambda saida: saida.write(
            b"%PDF-final"
        )

        resultado = _mesclar_pdfs([b"lote-1", b"lote-2"])

        self.assertEqual(resultado, b"%PDF-final")
        self.assertEqual(escritor_mock.append.call_count, 2)
