"""Serializers dos contratos HTTP de boletim."""

from rest_framework import serializers

from apps.boletim.models import Boletim

MODALIDADES_CHOICES = (
    (1, "Educação Infantil (EI)"),
    (3, "Educação de Jovens e Adultos (EJA)"),
    (4, "CIEJA"),
    (5, "Ensino Fundamental (EF)"),
    (6, "Ensino Médio (EM)"),
    (7, "CMCT"),
    (8, "MOVA"),
    (9, "ETEC"),
    (10, "CELP"),
)
_DESCRICAO_CAMPO_MODALIDADE = "Código da modalidade de ensino."
DESCRICAO_MODALIDADES = (
    _DESCRICAO_CAMPO_MODALIDADE
    + "\n\n"
    + "\n".join(
        f"* `{codigo}` - {descricao}"
        for codigo, descricao in MODALIDADES_CHOICES
    )
)


class FiltrosBoletimSerializer(serializers.Serializer):
    """Valida os filtros aceitos pela consulta de boletim."""

    anoLetivo = serializers.IntegerField(min_value=2000)  # noqa: N815
    dreCodigo = serializers.CharField(required=False)  # noqa: N815
    ueCodigo = serializers.CharField(required=False)  # noqa: N815
    semestre = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=2,
    )
    turmaCodigo = serializers.CharField(required=False)  # noqa: N815
    modalidade = serializers.ChoiceField(
        required=False,
        choices=MODALIDADES_CHOICES,
        help_text=_DESCRICAO_CAMPO_MODALIDADE,
    )
    bimestre = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=4,
    )


class FiltrosBoletinsSerializer(serializers.Serializer):
    """Valida os filtros da consulta coletiva de boletins."""

    anoLetivo = serializers.IntegerField(min_value=2000)  # noqa: N815
    dreCodigo = serializers.CharField()  # noqa: N815
    ueCodigo = serializers.CharField()  # noqa: N815
    semestre = serializers.IntegerField(min_value=0, max_value=2)
    turmaCodigo = serializers.CharField(required=False)  # noqa: N815
    modalidade = serializers.ChoiceField(
        choices=MODALIDADES_CHOICES,
        help_text=_DESCRICAO_CAMPO_MODALIDADE,
    )
    alunosCodigo = serializers.ListField(  # noqa: N815
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )
    bimestre = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=4,
    )


class FiltrosBoletinsPdfSerializer(FiltrosBoletinsSerializer):
    """Valida os filtros da geração coletiva de boletins em PDF."""

    boletinsPorPagina = serializers.ChoiceField(  # noqa: N815
        choices=(1, 2, 6),
        default=2,
        help_text="Quantidade de boletins exibidos em cada página.",
    )


class DadosAlunoBoletimSerializer(serializers.Serializer):
    """Serializa a identificação do aluno e de sua turma."""

    anoLetivo = serializers.IntegerField(source="ano_letivo")  # noqa: N815
    modalidadeCodigo = serializers.IntegerField(  # noqa: N815
        source="modalidade_codigo"
    )
    semestre = serializers.IntegerField()
    dreCodigo = serializers.CharField(source="dre_codigo")  # noqa: N815
    dreNome = serializers.CharField(source="dre_nome")  # noqa: N815
    ueCodigo = serializers.CharField(source="ue_codigo")  # noqa: N815
    ueNome = serializers.CharField(source="ue_nome")  # noqa: N815
    turmaCodigo = serializers.CharField(source="turma_codigo")  # noqa: N815
    turmaNome = serializers.CharField(source="turma_nome")  # noqa: N815
    ciclo = serializers.CharField(allow_null=True)
    alunoCodigo = serializers.IntegerField(source="aluno_codigo")  # noqa: N815
    alunoNome = serializers.CharField(  # noqa: N815
        source="aluno_nome", allow_null=True
    )
    nomeSocial = serializers.CharField(  # noqa: N815
        source="nome_social", allow_null=True
    )


class BimestreComponenteSerializer(serializers.Serializer):
    """Serializa os dados acadêmicos de um componente no bimestre."""

    bimestre = serializers.IntegerField(allow_null=True)
    periodoEscolarId = serializers.IntegerField(  # noqa: N815
        source="periodo_escolar_id", allow_null=True
    )
    componenteExistiaNoPeriodo = serializers.BooleanField(  # noqa: N815
        source="componente_existia_no_periodo", allow_null=True
    )
    conselhoClasseCadastrado = serializers.BooleanField(  # noqa: N815
        source="conselho_classe_cadastrado"
    )
    nota = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )
    conceitoId = serializers.IntegerField(  # noqa: N815
        source="conceito_id", allow_null=True
    )
    conceito = serializers.CharField(allow_null=True)
    totalAulas = serializers.IntegerField(  # noqa: N815
        source="total_aulas", allow_null=True
    )
    totalPresencas = serializers.IntegerField(  # noqa: N815
        source="total_presencas", allow_null=True
    )
    totalAusencias = serializers.IntegerField(  # noqa: N815
        source="total_ausencias", allow_null=True
    )
    totalCompensacoes = serializers.IntegerField(  # noqa: N815
        source="total_compensacoes", allow_null=True
    )
    totalRemotos = serializers.IntegerField(  # noqa: N815
        source="total_remotos", allow_null=True
    )
    totalAulasGlobal = serializers.IntegerField(  # noqa: N815
        source="total_aulas_global", allow_null=True
    )
    totalPresencasGlobal = serializers.IntegerField(  # noqa: N815
        source="total_presencas_global", allow_null=True
    )
    totalAusenciasGlobal = serializers.IntegerField(  # noqa: N815
        source="total_ausencias_global", allow_null=True
    )
    totalCompensacoesGlobal = serializers.IntegerField(  # noqa: N815
        source="total_compensacoes_global", allow_null=True
    )
    totalRemotosGlobal = serializers.IntegerField(  # noqa: N815
        source="total_remotos_global", allow_null=True
    )
    mediaFrequencia = serializers.DecimalField(  # noqa: N815
        source="media_frequencia",
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )
    tipoNota = serializers.CharField(  # noqa: N815
        source="tipo_nota", allow_null=True
    )
    tipoNotaDescricao = serializers.CharField(  # noqa: N815
        source="tipo_nota_descricao", allow_null=True
    )
    sintese = serializers.CharField(allow_null=True)
    origemFrequencia = serializers.CharField(  # noqa: N815
        source="origem_frequencia", allow_null=True
    )
    parecerConclusivo = serializers.CharField(  # noqa: N815
        source="parecer_conclusivo", allow_null=True
    )
    recomendacoesAluno = serializers.CharField(  # noqa: N815
        source="recomendacoes_aluno", allow_null=True
    )
    recomendacoesFamilia = serializers.CharField(  # noqa: N815
        source="recomendacoes_familia", allow_null=True
    )
    anotacoesPedagogicas = serializers.CharField(  # noqa: N815
        source="anotacoes_pedagogicas", allow_null=True
    )


class ComponenteBoletimSerializer(serializers.Serializer):
    """Serializa um componente e seus dados por bimestre."""

    codigo = serializers.IntegerField(
        source="componente_codigo",
        allow_null=True,
    )
    nome = serializers.CharField(
        source="disciplina_nome",
        allow_null=True,
    )
    nomeSgp = serializers.CharField(  # noqa: N815
        source="disciplina_nome_sgp",
        allow_null=True,
    )
    componentePaiCodigo = serializers.IntegerField(  # noqa: N815
        source="componente_pai_codigo",
        allow_null=True,
    )
    componentePaiNome = serializers.CharField(  # noqa: N815
        source="componente_pai_nome", allow_null=True
    )
    lancaNota = serializers.BooleanField(source="lanca_nota")  # noqa: N815
    registraFrequencia = serializers.BooleanField(  # noqa: N815
        source="registra_frequencia"
    )
    baseNacional = serializers.BooleanField(  # noqa: N815
        source="base_nacional"
    )
    compartilhada = serializers.BooleanField()
    territorioSaber = serializers.BooleanField(  # noqa: N815
        source="territorio_saber"
    )
    componenteTerritorioCodigo = serializers.IntegerField(  # noqa: N815
        source="componente_territorio_codigo", allow_null=True
    )
    territorioCodigo = serializers.IntegerField(  # noqa: N815
        source="territorio_codigo", allow_null=True
    )
    experienciaPedagogicaCodigo = serializers.IntegerField(  # noqa: N815
        source="experiencia_pedagogica_codigo", allow_null=True
    )
    territorioNome = serializers.CharField(  # noqa: N815
        source="territorio_nome", allow_null=True
    )
    experienciaPedagogicaNome = serializers.CharField(  # noqa: N815
        source="experiencia_pedagogica_nome", allow_null=True
    )
    turmaRegularCodigo = serializers.CharField(  # noqa: N815
        source="turma_regular_codigo", allow_null=True
    )
    turmaComponenteCodigo = serializers.CharField(  # noqa: N815
        source="turma_componente_codigo", allow_null=True
    )
    grupoMatrizId = serializers.IntegerField(  # noqa: N815
        source="grupo_matriz_id", allow_null=True
    )
    grupoMatrizNome = serializers.CharField(  # noqa: N815
        source="grupo_matriz_nome", allow_null=True
    )
    areaConhecimentoId = serializers.IntegerField(  # noqa: N815
        source="area_conhecimento_id", allow_null=True
    )
    areaConhecimentoNome = serializers.CharField(  # noqa: N815
        source="area_conhecimento_nome", allow_null=True
    )
    ordemGrupoArea = serializers.IntegerField(  # noqa: N815
        source="ordem_grupo_area", allow_null=True
    )
    regencia = serializers.BooleanField()
    bimestres = BimestreComponenteSerializer(many=True)


class ComponenteRegenciaSerializer(serializers.Serializer):
    """Serializa uma disciplina filha da regÃªncia de classe."""

    codigo = serializers.IntegerField(
        source="componente_codigo",
        allow_null=True,
    )
    nome = serializers.CharField(
        source="disciplina_nome",
        allow_null=True,
    )
    nomeSgp = serializers.CharField(  # noqa: N815
        source="disciplina_nome_sgp",
        allow_null=True,
    )
    lancaNota = serializers.BooleanField(source="lanca_nota")  # noqa: N815
    bimestres = BimestreComponenteSerializer(many=True)


class RegenciaBoletimSerializer(serializers.Serializer):
    """Serializa a frequÃªncia comum e as disciplinas da regÃªncia."""

    codigo = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    registraFrequencia = serializers.BooleanField(  # noqa: N815
        source="registra_frequencia"
    )
    bimestres = BimestreComponenteSerializer(many=True)
    componentes = ComponenteRegenciaSerializer(many=True)


class BoletimAlunoResponseSerializer(serializers.Serializer):
    """Serializa o boletim hierárquico de um aluno."""

    dadosAluno = DadosAlunoBoletimSerializer(  # noqa: N815
        source="dados_aluno",
        allow_null=True,
    )
    componentes = ComponenteBoletimSerializer(many=True)
    regencias = RegenciaBoletimSerializer(many=True)


class RegistroBoletimSerializer(serializers.ModelSerializer):
    """Serializa uma linha consolidada do boletim escolar."""

    anoLetivo = serializers.IntegerField(source="ano_letivo")  # noqa: N815
    modalidadeCodigo = serializers.IntegerField(  # noqa: N815
        source="modalidade_codigo"
    )
    dreCodigo = serializers.CharField(source="dre_codigo")  # noqa: N815
    dreNome = serializers.CharField(source="dre_nome")  # noqa: N815
    ueCodigo = serializers.CharField(source="ue_codigo")  # noqa: N815
    ueNome = serializers.CharField(source="ue_nome")  # noqa: N815
    turmaCodigo = serializers.CharField(source="turma_codigo")  # noqa: N815
    turmaNome = serializers.CharField(source="turma_nome")  # noqa: N815
    ciclo = serializers.CharField(allow_null=True)
    alunoCodigo = serializers.IntegerField(source="aluno_codigo")  # noqa: N815
    alunoNome = serializers.CharField(  # noqa: N815
        source="aluno_nome", allow_null=True
    )
    nomeSocial = serializers.CharField(  # noqa: N815
        source="nome_social", allow_null=True
    )
    periodoEscolarId = serializers.IntegerField(  # noqa: N815
        source="periodo_escolar_id", allow_null=True
    )
    componenteCodigo = serializers.IntegerField(  # noqa: N815
        source="componente_codigo", allow_null=True
    )
    disciplinaNome = serializers.CharField(  # noqa: N815
        source="disciplina_nome", allow_null=True
    )
    disciplinaNomeSgp = serializers.CharField(  # noqa: N815
        source="disciplina_nome_sgp", allow_null=True
    )
    componenteExistiaNoPeriodo = serializers.BooleanField(  # noqa: N815
        source="componente_existia_no_periodo", allow_null=True
    )
    conceitoId = serializers.IntegerField(  # noqa: N815
        source="conceito_id", allow_null=True
    )
    totalAulas = serializers.IntegerField(  # noqa: N815
        source="total_aulas", allow_null=True
    )
    totalPresencas = serializers.IntegerField(  # noqa: N815
        source="total_presencas", allow_null=True
    )
    totalAusencias = serializers.IntegerField(  # noqa: N815
        source="total_ausencias", allow_null=True
    )
    totalCompensacoes = serializers.IntegerField(  # noqa: N815
        source="total_compensacoes", allow_null=True
    )
    totalRemotos = serializers.IntegerField(  # noqa: N815
        source="total_remotos", allow_null=True
    )
    origemFrequencia = serializers.CharField(  # noqa: N815
        source="origem_frequencia", allow_null=True
    )
    parecerConclusivo = serializers.CharField(  # noqa: N815
        source="parecer_conclusivo", allow_null=True
    )
    recomendacoesAluno = serializers.CharField(  # noqa: N815
        source="recomendacoes_aluno", allow_null=True
    )
    recomendacoesFamilia = serializers.CharField(  # noqa: N815
        source="recomendacoes_familia", allow_null=True
    )
    anotacoesPedagogicas = serializers.CharField(  # noqa: N815
        source="anotacoes_pedagogicas", allow_null=True
    )

    class Meta:
        model = Boletim
        fields = (
            "anoLetivo",
            "modalidadeCodigo",
            "semestre",
            "dreCodigo",
            "dreNome",
            "ueCodigo",
            "ueNome",
            "turmaCodigo",
            "turmaNome",
            "ciclo",
            "alunoCodigo",
            "alunoNome",
            "nomeSocial",
            "periodoEscolarId",
            "bimestre",
            "componenteCodigo",
            "disciplinaNome",
            "disciplinaNomeSgp",
            "componenteExistiaNoPeriodo",
            "nota",
            "conceitoId",
            "totalAulas",
            "totalPresencas",
            "totalAusencias",
            "totalCompensacoes",
            "totalRemotos",
            "origemFrequencia",
            "parecerConclusivo",
            "recomendacoesAluno",
            "recomendacoesFamilia",
            "anotacoesPedagogicas",
        )
