"""Consultas ORM do domínio de boletim."""

from django.db.models import QuerySet

from apps.boletim.models import Boletim

_CAMPOS_BOLETIM = (
    "ano_letivo",
    "modalidade_codigo",
    "semestre",
    "dre_codigo",
    "dre_nome",
    "ue_codigo",
    "ue_nome",
    "turma_codigo",
    "turma_componente_codigo",
    "turma_regular_codigo",
    "turma_nome",
    "aluno_codigo",
    "aluno_nome",
    "nome_social",
    "periodo_escolar_id",
    "bimestre",
    "componente_codigo",
    "disciplina_nome",
    "disciplina_nome_sgp",
    "componente_pai_codigo",
    "componente_pai_nome",
    "lanca_nota",
    "registra_frequencia",
    "base_nacional",
    "compartilhada",
    "territorio_saber",
    "componente_territorio_codigo",
    "territorio_codigo",
    "experiencia_pedagogica_codigo",
    "territorio_nome",
    "experiencia_pedagogica_nome",
    "grupo_matriz_id",
    "grupo_matriz_nome",
    "area_conhecimento_id",
    "area_conhecimento_nome",
    "ordem_grupo_area",
    "regencia",
    "componente_existia_no_periodo",
    "conselho_classe_cadastrado",
    "nota",
    "conceito_id",
    "conceito",
    "total_aulas",
    "total_presencas",
    "total_ausencias",
    "total_compensacoes",
    "total_remotos",
    "total_aulas_global",
    "total_presencas_global",
    "total_ausencias_global",
    "total_compensacoes_global",
    "total_remotos_global",
    "media_frequencia",
    "tipo_nota",
    "tipo_nota_descricao",
    "origem_frequencia",
    "parecer_conclusivo",
    "recomendacoes_aluno",
    "recomendacoes_familia",
    "anotacoes_pedagogicas",
)


class BoletimRepository:
    """Consulta a view materializada de boletim por meio do ORM."""

    def listar_por_aluno(
        self,
        aluno_codigo: int,
        ano_letivo: int,
        bimestre: int | None = None,
        dre_codigo: str | None = None,
        ue_codigo: str | None = None,
        semestre: int | None = None,
        turma_codigo: str | None = None,
        modalidade: int | None = None,
    ) -> QuerySet[Boletim]:
        """Lista o boletim consolidado de um aluno.

        Args:
            aluno_codigo: Código do aluno no EOL.
            ano_letivo: Ano letivo consultado.
            bimestre: Bimestre opcional usado para restringir o resultado.
            dre_codigo: Código opcional da DRE.
            ue_codigo: Código opcional da unidade escolar.
            semestre: Semestre opcional da turma.
            turma_codigo: Código opcional da turma.
            modalidade: Código opcional da modalidade.

        Returns:
            Consulta ordenada pelos períodos e componentes do boletim.
        """
        filtros: dict[str, int | str] = {
            "aluno_codigo": aluno_codigo,
            "ano_letivo": ano_letivo,
        }
        if bimestre is not None:
            filtros["bimestre"] = bimestre
        if dre_codigo is not None:
            filtros["dre_codigo"] = dre_codigo
        if ue_codigo is not None:
            filtros["ue_codigo"] = ue_codigo
        if semestre is not None:
            filtros["semestre"] = semestre
        if turma_codigo is not None:
            filtros["turma_codigo"] = turma_codigo
        if modalidade is not None:
            filtros["modalidade_codigo"] = modalidade

        return (
            Boletim.objects.filter(**filtros)
            .only(*_CAMPOS_BOLETIM)
            .order_by("bimestre", "disciplina_nome_sgp", "componente_codigo")
        )

    def listar_boletins(
        self,
        ano_letivo: int,
        dre_codigo: str,
        ue_codigo: str,
        semestre: int,
        modalidade: int,
        alunos_codigo: list[int],
        turma_codigo: str | None = None,
    ) -> QuerySet[Boletim]:
        """Lista boletins de vários alunos no contexto informado.

        Args:
            ano_letivo: Ano letivo consultado.
            dre_codigo: Código da DRE.
            ue_codigo: Código da unidade escolar.
            semestre: Semestre da turma.
            modalidade: Código da modalidade.
            alunos_codigo: Códigos dos alunos; vazio seleciona todos.
            turma_codigo: Código opcional da turma.

        Returns:
            Consulta ordenada por aluno, turma, período e componente.
        """
        filtros: dict[str, int | str] = {
            "ano_letivo": ano_letivo,
            "dre_codigo": dre_codigo,
            "ue_codigo": ue_codigo,
            "semestre": semestre,
            "modalidade_codigo": modalidade,
        }
        if turma_codigo is not None:
            filtros["turma_codigo"] = turma_codigo

        consulta = Boletim.objects.filter(**filtros)
        if alunos_codigo:
            consulta = consulta.filter(aluno_codigo__in=alunos_codigo)
        return consulta.only(*_CAMPOS_BOLETIM).order_by(
            "aluno_codigo",
            "turma_codigo",
            "bimestre",
            "disciplina_nome_sgp",
            "componente_codigo",
        )
