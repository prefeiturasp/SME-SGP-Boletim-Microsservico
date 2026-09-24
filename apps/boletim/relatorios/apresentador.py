"""Prepara os dados dos boletins para o template PDF."""

from collections.abc import Mapping
from decimal import Decimal
from typing import TypedDict, cast

from django.utils import timezone

from apps.boletim.constantes import (
    BIMESTRES_ANUAIS,
    BIMESTRES_SEMESTRAIS,
    MODALIDADES_SEMESTRAIS,
)

_BIMESTRES_ANUAIS = (*BIMESTRES_ANUAIS, 0)
_BIMESTRES_SEMESTRAIS = (*BIMESTRES_SEMESTRAIS, 0)
_ABREVIACAO_MODALIDADE = {
    1: "EI",
    3: "EJA",
    4: "CIEJA",
    5: "EF",
    6: "EM",
    7: "CMCT",
    8: "MOVA",
    9: "ETEC",
    10: "CELP",
}


class LinhaBoletinsPdf(TypedDict):
    """Representa um boletim exibido em largura cheia na página."""

    boletins: list[dict[str, object]]


class PaginaBoletinsPdf(TypedDict):
    """Representa uma página física do relatório."""

    linhas: list[LinhaBoletinsPdf]


class ContextoBoletinsPdf(TypedDict):
    """Representa o contexto entregue ao template de PDF."""

    paginas: list[PaginaBoletinsPdf]
    boletins_por_pagina: int
    data_impressao: str
    total_paginas: int


def montar_contexto_pdf(
    boletins: list[dict[str, object]],
    boletins_por_pagina: int,
) -> ContextoBoletinsPdf:
    """Organiza boletins formatados em páginas, empilhados em largura cheia.

    Args:
        boletins: Boletins consolidados retornados pelo serviço.
        boletins_por_pagina: Quantidade máxima de boletins por página.

    Returns:
        Contexto pronto para o template `boletins.html`.
    """
    ordenados = sorted(boletins, key=_chave_ordenacao)
    formatados = [
        _formatar_boletim(boletim, boletins_por_pagina)
        for boletim in ordenados
    ]
    paginas: list[PaginaBoletinsPdf] = []
    for inicio in range(0, len(formatados), boletins_por_pagina):
        itens = formatados[inicio : inicio + boletins_por_pagina]
        linhas: list[LinhaBoletinsPdf] = [
            {"boletins": [item]} for item in itens
        ]
        paginas.append({"linhas": linhas})
    return {
        "paginas": paginas,
        "boletins_por_pagina": boletins_por_pagina,
        "data_impressao": timezone.localdate().strftime("%d/%m/%Y"),
        "total_paginas": len(paginas),
    }


def _formatar_boletim(
    boletim: dict[str, object],
    boletins_por_pagina: int,
) -> dict[str, object]:
    """Formata um boletim consolidado para exibição no PDF.

    Args:
        boletim: Boletim consolidado, com dados do aluno, componentes e
            regências.

    Returns:
        Boletim formatado, pronto para o template.
    """
    dados_brutos = _mapa(boletim.get("dados_aluno"))
    modalidade = _inteiro(dados_brutos.get("modalidade_codigo"))
    semestral = modalidade in MODALIDADES_SEMESTRAIS
    periodos_possiveis = (
        _BIMESTRES_SEMESTRAIS if semestral else _BIMESTRES_ANUAIS
    )

    componentes_brutos = _lista_mapas(boletim.get("componentes"))
    regencias_brutas = _lista_mapas(boletim.get("regencias"))

    possui_nota_final = _possui_nota_final(
        componentes_brutos, regencias_brutas
    )
    periodos = (
        periodos_possiveis
        if possui_nota_final
        else tuple(periodo for periodo in periodos_possiveis if periodo != 0)
    )

    grupos_por_codigo_regencia = {
        _inteiro(componente.get("componente_codigo")): _inteiro(
            regencia.get("grupo_matriz_id")
        )
        for regencia in regencias_brutas
        for componente in _lista_mapas(regencia.get("componentes"))
        if _inteiro(componente.get("componente_codigo")) > 0
    }
    grupos_normais = _agrupar_por_matriz(
        componentes_brutos,
        periodos,
        grupos_por_codigo_regencia,
    )
    grupos = _montar_grupos(
        grupos_normais,
        regencias_brutas,
        periodos,
        semestral,
    )

    todos_bimestres = [
        bimestre
        for componente in componentes_brutos
        for bimestre in _lista_mapas(componente.get("bimestres"))
    ]
    dados = dict(dados_brutos)
    dados["turma_relatorio"] = _turma_relatorio(dados_brutos)
    dados["ciclo"] = str(dados_brutos.get("ciclo") or "")
    usa_conceito = _usa_conceito(componentes_brutos, regencias_brutas)

    return {
        "dados": dados,
        "nome_aluno": dados.get("nome_social")
        or dados.get("aluno_nome")
        or "",
        "periodos": periodos,
        "possui_nota_final": possui_nota_final,
        "usa_conceito": usa_conceito,
        "exibe_legenda": usa_conceito
        or _tem_sintese(componentes_brutos, regencias_brutas),
        "grupos": grupos,
        "frequencia_global": _formatar_frequencia_global(todos_bimestres),
        "parecer_conclusivo": _primeiro_texto(
            todos_bimestres, "parecer_conclusivo"
        ),
        "recomendacoes_aluno": _primeiro_texto(
            todos_bimestres, "recomendacoes_aluno"
        ),
        "recomendacoes_familia": _primeiro_texto(
            todos_bimestres, "recomendacoes_familia"
        ),
        "exibe_recomendacoes": boletins_por_pagina == 1,
    }


def _primeiro_texto(
    bimestres: list[Mapping[str, object]],
    campo: str,
) -> str:
    """Localiza o primeiro valor não vazio de um campo entre os bimestres.

    Args:
        bimestres: Linhas de bimestre já formatadas do boletim.
        campo: Nome do campo textual buscado em cada bimestre.

    Returns:
        Primeiro valor não vazio encontrado, ou string vazia.
    """
    return str(
        next(
            (item.get(campo) for item in bimestres if item.get(campo)),
            "",
        )
    )


def _agrupar_por_matriz(
    componentes: list[Mapping[str, object]],
    periodos: tuple[int, ...],
    grupos_por_codigo_regencia: Mapping[int, int],
) -> list[dict[str, object]]:
    """Separa os componentes por grupo de matriz, na ordem recebida.

    Cada grupo vira uma tabela própria no PDF, com espaço entre elas.

    Args:
        componentes: Componentes curriculares na ordem oficial de exibição.
        periodos: Períodos exibidos no boletim.
        grupos_por_codigo_regencia: Grupo do pai para cada componente que
            integra uma regência.
    Returns:
        Grupos de matriz, cada um com seus componentes formatados.
    """
    matrizes = sorted({_chave_grupo(componente) for componente in componentes})
    grupos: list[dict[str, object]] = [
        {"grupo_matriz_id": matriz, "componentes": []} for matriz in matrizes
    ]
    grupos_por_matriz = {
        cast(int, grupo["grupo_matriz_id"]): grupo for grupo in grupos
    }
    ordenados = sorted(
        componentes,
        key=lambda componente: _chave_ordenacao_grupo_pdf(
            componente,
        ),
    )
    for componente in ordenados:
        codigo = _inteiro(componente.get("componente_codigo"))
        if codigo in grupos_por_codigo_regencia:
            continue
        grupo = grupos_por_matriz[_chave_grupo(componente)]
        linhas = cast(list[dict[str, object]], grupo["componentes"])
        linhas.append(_formatar_componente(componente, periodos))
    return grupos


def _chave_ordenacao_grupo_pdf(
    componente: Mapping[str, object],
) -> tuple[int, str]:
    """Ordene componentes dentro dos subgrupos como no relatório legado."""
    nome = componente.get("disciplina_nome_sgp") or ""
    return _chave_grupo(componente), str(nome)


def _montar_grupos(
    grupos_normais: list[dict[str, object]],
    regencias: list[Mapping[str, object]],
    periodos: tuple[int, ...],
    semestral: bool,
) -> list[dict[str, object]]:
    """Posiciona a regência no subgrupo usado pelo relatório detalhado.

    Turmas anuais mostram os componentes com frequência compartilhada ao
    final de cada grupo; turmas semestrais (EJA) mostram a regência antes de
    todos os grupos.

    Args:
        grupos_normais: Grupos de matriz formatados na ordem de exibição.
        regencias: Regências consolidadas do boletim.
        periodos: Períodos exibidos no boletim.
        semestral: Indica se a modalidade da turma é semestral (EJA).

    Returns:
        Grupos de matriz com as regências posicionadas corretamente.
    """
    if not regencias:
        return grupos_normais
    linhas_por_matriz: dict[int, list[dict[str, object]]] = {}
    for regencia in regencias:
        chave = _inteiro(regencia.get("grupo_matriz_id"))
        linhas_por_matriz.setdefault(chave, []).extend(
            _formatar_linhas_regencia(regencia, periodos)
        )

    if semestral:
        linhas = [
            linha for itens in linhas_por_matriz.values() for linha in itens
        ]
        return [
            {"grupo_matriz_id": 0, "componentes": linhas},
            *grupos_normais,
        ]

    if not grupos_normais:
        linhas = [
            linha for itens in linhas_por_matriz.values() for linha in itens
        ]
        grupos_normais.append({"grupo_matriz_id": 0, "componentes": linhas})
        return grupos_normais

    linhas = [linha for itens in linhas_por_matriz.values() for linha in itens]
    for grupo in grupos_normais:
        componentes = cast(list[dict[str, object]], grupo["componentes"])
        componentes.extend(linhas)
    return grupos_normais


def _chave_grupo(componente: Mapping[str, object]) -> int:
    """Produz a chave do grupo de matriz de um componente.

    Args:
        componente: Componente curricular consolidado.

    Returns:
        Identificador do grupo de matriz, ou zero quando ausente.
    """
    return _inteiro(componente.get("grupo_matriz_id"))


def _usa_conceito(
    componentes: list[Mapping[str, object]],
    regencias: list[Mapping[str, object]],
) -> bool:
    """Indica se o boletim usa conceito (P/S/NS) em vez de nota numérica.

    Args:
        componentes: Componentes curriculares normais do boletim.
        regencias: Regências do boletim.

    Returns:
        `True` quando algum bimestre registrou conceito.
    """
    if any(
        _algum_bimestre_tem_conceito(componente.get("bimestres"))
        for componente in componentes
    ):
        return True
    return any(
        _algum_bimestre_tem_conceito(sub.get("bimestres"))
        for regencia in regencias
        for sub in _lista_mapas(regencia.get("componentes"))
    )


def _algum_bimestre_tem_conceito(bimestres: object) -> bool:
    """Indica se algum bimestre da lista registrou conceito.

    Args:
        bimestres: Lista de bimestres de um componente.

    Returns:
        `True` quando algum bimestre tem conceito preenchido.
    """
    return any(item.get("conceito") for item in _lista_mapas(bimestres))


def _tem_sintese(
    componentes: list[Mapping[str, object]],
    regencias: list[Mapping[str, object]],
) -> bool:
    """Indica se algum componente é só frequência (síntese F/NF).

    Args:
        componentes: Componentes curriculares normais do boletim.
        regencias: Regências do boletim.

    Returns:
        `True` quando algum componente não lança nota.
    """
    if any(
        not componente.get("lanca_nota", True) for componente in componentes
    ):
        return True
    return any(
        not sub.get("lanca_nota", True)
        for regencia in regencias
        for sub in _lista_mapas(regencia.get("componentes"))
    )


def _possui_nota_final(
    componentes: list[Mapping[str, object]],
    regencias: list[Mapping[str, object]],
) -> bool:
    """Indica se algum componente lançou nota ou conceito no período final.

    Args:
        componentes: Componentes curriculares normais do boletim.
        regencias: Regências do boletim.

    Returns:
        `True` quando existe nota ou conceito no período final (bimestre 0).
    """
    if any(
        _tem_nota_final(componente.get("bimestres"))
        for componente in componentes
    ):
        return True
    return any(
        _tem_nota_final(sub.get("bimestres"))
        for regencia in regencias
        for sub in _lista_mapas(regencia.get("componentes"))
    )


def _tem_nota_final(bimestres: object) -> bool:
    """Indica se a lista de bimestres tem nota ou conceito no período final.

    Args:
        bimestres: Lista de bimestres de um componente.

    Returns:
        `True` quando o bimestre 0 (final) tem nota ou conceito.
    """
    for item in _lista_mapas(bimestres):
        if _inteiro(item.get("bimestre")) == 0 and (
            item.get("nota") is not None or item.get("conceito")
        ):
            return True
    return False


def _turma_relatorio(dados: Mapping[str, object]) -> str:
    """Compõe "MODALIDADE - TURMA" a partir dos dados já disponíveis.

    Args:
        dados: Dados do aluno, com modalidade e nome da turma.

    Returns:
        Nome da turma prefixado pela abreviação da modalidade, quando
        houver abreviação conhecida; o nome da turma sem alterações caso
        contrário.
    """
    turma_nome = str(dados.get("turma_nome") or "")
    abreviacao = _ABREVIACAO_MODALIDADE.get(
        _inteiro(dados.get("modalidade_codigo"))
    )
    if not abreviacao or not turma_nome:
        return turma_nome
    return f"{abreviacao} - {turma_nome}"


def _formatar_linhas_regencia(
    regencia: Mapping[str, object],
    periodos: tuple[int, ...],
) -> list[dict[str, object]]:
    """Formata as disciplinas de uma regência com frequência compartilhada.

    A frequência é a mesma para todas as disciplinas do professor regente;
    por isso só a primeira linha carrega os valores de frequência, para o
    template exibi-los em uma única célula com `rowspan`.

    Args:
        regencia: Regência consolidada, com suas disciplinas e frequência.
        periodos: Períodos exibidos no boletim.

    Returns:
        Linhas formatadas das disciplinas da regência.
    """
    frequencias = _periodos_por_numero(regencia.get("bimestres"))
    componentes = _lista_mapas(regencia.get("componentes"))
    linhas: list[dict[str, object]] = []
    for indice, componente in enumerate(componentes):
        por_numero = _periodos_por_numero(componente.get("bimestres"))
        linha: dict[str, object] = {
            "nome": componente.get("disciplina_nome_sgp")
            or componente.get("disciplina_nome")
            or "",
            "periodos": [
                {"nota": _formatar_nota(por_numero.get(periodo))}
                for periodo in periodos
            ],
            "eh_regencia": True,
        }
        if indice == 0:
            linha["primeira_linha_regencia"] = True
            linha["linhas_regencia"] = len(componentes)
            periodos_linha = cast(list[dict[str, object]], linha["periodos"])
            for indice_periodo, periodo in enumerate(periodos):
                periodos_linha[indice_periodo]["frequencia"] = (
                    _formatar_frequencia(frequencias.get(periodo))
                )
        linhas.append(linha)
    return linhas


def _formatar_componente(
    componente: Mapping[str, object],
    periodos: tuple[int, ...],
) -> dict[str, object]:
    """Formata um componente curricular normal para exibição no PDF.

    Args:
        componente: Componente curricular consolidado.
        periodos: Períodos exibidos no boletim.

    Returns:
        Nome do componente e nota/frequência formatadas por período.
    """
    por_numero = _periodos_por_numero(componente.get("bimestres"))
    return {
        "nome": componente.get("disciplina_nome_sgp")
        or componente.get("disciplina_nome")
        or "",
        "periodos": [
            {
                "nota": _formatar_nota(por_numero.get(periodo)),
                "frequencia": _formatar_frequencia(por_numero.get(periodo)),
            }
            for periodo in periodos
        ],
    }


def _periodos_por_numero(valor: object) -> dict[int, Mapping[str, object]]:
    """Indexa os bimestres de um componente pelo próprio número.

    Args:
        valor: Lista de bimestres de um componente.

    Returns:
        Bimestres indexados pelo número do período.
    """
    return {
        _inteiro(item.get("bimestre")): item for item in _lista_mapas(valor)
    }


def _formatar_nota(periodo: Mapping[str, object] | None) -> str:
    """Formata a nota, o conceito ou a síntese de um período.

    Args:
        periodo: Dados do bimestre, ou `None` quando não houver período.

    Returns:
        Conceito ou síntese quando presentes, nota com uma casa decimal
        quando numérica, ou string vazia quando não houver valor.
    """
    if not periodo:
        return ""
    conceito = periodo.get("conceito")
    if conceito:
        return str(conceito)
    sintese = periodo.get("sintese")
    if sintese:
        return str(sintese)
    nota = periodo.get("nota")
    if nota is None:
        return ""
    decimal = Decimal(str(nota))
    return f"{decimal:.1f}"


def _formatar_frequencia(periodo: Mapping[str, object] | None) -> str:
    """Formata o percentual de frequência de um período.

    Args:
        periodo: Dados do bimestre, ou `None` quando não houver período.

    Returns:
        Percentual de frequência formatado, ou string vazia quando não
        houver aulas registradas.
    """
    if not periodo:
        return ""
    percentual = _percentual(
        periodo.get("total_aulas"),
        periodo.get("total_ausencias"),
        periodo.get("total_compensacoes"),
    )
    return f"{percentual}%" if percentual else ""


def _formatar_frequencia_global(
    periodos: list[Mapping[str, object]],
) -> str:
    """Formata a frequência global do boletim a partir dos bimestres.

    Args:
        periodos: Bimestres do boletim, cada um com os totais globais.

    Returns:
        Percentual de frequência global com o símbolo `%`, ou string vazia
        quando nenhum bimestre tiver aulas registradas.
    """
    for periodo in periodos:
        percentual = _percentual(
            periodo.get("total_aulas_global"),
            periodo.get("total_ausencias_global"),
            periodo.get("total_compensacoes_global"),
        )
        if percentual:
            return f"{percentual}%"
    return ""


def _percentual(aulas: object, ausencias: object, compensacoes: object) -> str:
    """Calcula o percentual de frequência a partir dos totais de aula.

    Args:
        aulas: Total de aulas do período.
        ausencias: Total de ausências do período.
        compensacoes: Total de ausências compensadas do período.

    Returns:
        Percentual de frequência com duas casas decimais, ou string vazia
        quando o total de aulas não for positivo.
    """
    total = _inteiro(aulas)
    if total <= 0:
        return ""
    faltas = _inteiro(ausencias)
    compensadas = _inteiro(compensacoes)
    valor = (total - faltas + compensadas) * 100 / total
    return f"{valor:.2f}"


def _chave_ordenacao(boletim: dict[str, object]) -> tuple[str, str]:
    """Produz a chave de ordenação dos boletins por turma e aluno.

    Args:
        boletim: Boletim consolidado de um aluno.

    Returns:
        Chave composta pelo nome da turma e o nome de exibição do aluno.
    """
    dados = _mapa(boletim.get("dados_aluno"))
    nome = dados.get("nome_social") or dados.get("aluno_nome") or ""
    return str(dados.get("turma_nome") or ""), str(nome)


def _mapa(valor: object) -> Mapping[str, object]:
    """Normaliza um valor dinâmico para `Mapping`.

    Args:
        valor: Valor de origem dinâmica, possivelmente não mapeável.

    Returns:
        O próprio valor quando é um `Mapping`, ou um dicionário vazio.
    """
    return (
        cast(Mapping[str, object], valor) if isinstance(valor, Mapping) else {}
    )


def _lista_mapas(valor: object) -> list[Mapping[str, object]]:
    """Normaliza um valor dinâmico para uma lista de `Mapping`.

    Args:
        valor: Valor de origem dinâmica, possivelmente não iterável.

    Returns:
        Itens de `valor` que são `Mapping`, ou lista vazia quando `valor`
        não for uma lista.
    """
    if not isinstance(valor, list):
        return []
    return [item for item in valor if isinstance(item, Mapping)]


def _inteiro(valor: object) -> int:
    """Normaliza um valor dinâmico para `int`.

    Args:
        valor: Valor de origem dinâmica, possivelmente não inteiro.

    Returns:
        O próprio valor quando já é `int`, ou zero caso contrário.
    """
    return valor if isinstance(valor, int) else 0
