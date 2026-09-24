"""Renderiza os boletins escolares em PDF com WeasyPrint."""

import io
import multiprocessing
import os
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from typing import cast

from django.template.loader import render_to_string
from django_weasyprint.utils import DjangoURLFetcher
from pypdf import PdfWriter
from weasyprint import HTML

from apps.boletim.relatorios.apresentador import montar_contexto_pdf

_PAGINAS_POR_LOTE = 20
_CONTEXTO_MULTIPROCESSO = multiprocessing.get_context("spawn")


class GeradorBoletinsPdf:
    """Gera o documento PDF dos boletins selecionados."""

    def gerar(
        self,
        boletins: list[dict[str, object]],
        boletins_por_pagina: int,
    ) -> bytes:
        """Renderiza boletins paginados e retorna os bytes do PDF.

        O layout do PDF roda em um único núcleo e seu custo cresce com o
        número de páginas; documentos com mais de um lote são renderizados
        em processos separados e depois mesclados em bytes, para aproveitar
        os núcleos disponíveis em relatórios grandes (por exemplo, quando
        nenhuma turma é informada no filtro).

        Args:
            boletins: Boletins consolidados retornados pelo serviço.
            boletins_por_pagina: Quantidade máxima de boletins por página.

        Returns:
            Bytes do documento PDF final.
        """
        contexto = montar_contexto_pdf(boletins, boletins_por_pagina)
        paginas = contexto["paginas"]
        if not paginas:
            return _renderizar_lote(contexto)

        lotes = [
            {
                **contexto,
                "paginas": paginas[inicio : inicio + _PAGINAS_POR_LOTE],
                "pagina_inicial": inicio,
            }
            for inicio in range(0, len(paginas), _PAGINAS_POR_LOTE)
        ]
        if len(lotes) == 1:
            return _renderizar_lote(lotes[0])

        pdfs_por_lote = self._renderizar_lotes_em_paralelo(lotes)
        return _mesclar_pdfs(pdfs_por_lote)

    @staticmethod
    def _renderizar_lotes_em_paralelo(
        lotes: Sequence[Mapping[str, object]],
    ) -> list[bytes]:
        """Distribui a renderização dos lotes entre processos filhos.

        Args:
            lotes: Contextos de cada lote, já divididos em páginas.

        Returns:
            Bytes do PDF de cada lote, na mesma ordem dos lotes recebidos.
        """
        trabalhadores = min(len(lotes), os.cpu_count() or 1)
        with ProcessPoolExecutor(
            max_workers=trabalhadores,
            mp_context=_CONTEXTO_MULTIPROCESSO,
            initializer=_inicializar_worker,
        ) as executor:
            return list(executor.map(_renderizar_lote, lotes))


def _inicializar_worker() -> None:
    """Configura o Django no processo filho antes de renderizar."""
    import django

    django.setup()


def _renderizar_lote(contexto: Mapping[str, object]) -> bytes:
    """Renderiza um lote pequeno para limitar o custo do layout HTML.

    Args:
        contexto: Contexto do template `boletins.html` para o lote.

    Returns:
        Bytes do PDF renderizado para o lote.
    """
    html = render_to_string("boletim/relatorios/boletins.html", contexto)
    documento = HTML(
        string=html,
        base_url="file:///",
        url_fetcher=DjangoURLFetcher(),
    ).render()
    return cast(bytes, documento.write_pdf())


def _mesclar_pdfs(pdfs: list[bytes]) -> bytes:
    """Concatena os PDFs renderizados por lote em um único documento.

    Args:
        pdfs: Bytes do PDF de cada lote, na ordem final desejada.

    Returns:
        Bytes do documento PDF único, com todos os lotes concatenados.
    """
    escritor = PdfWriter()
    for pdf in pdfs:
        escritor.append(io.BytesIO(pdf))
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()
