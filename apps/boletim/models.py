"""Models de leitura do domínio de boletim."""

from django.db import models

from apps.core.models import ModeloBase


class Boletim(ModeloBase):
    """Representa uma linha consolidada da view materializada de boletim.

    `aluno_codigo` é usado como chave técnica somente para impedir que o
    Django procure uma coluna `id`. A granularidade real da view também inclui
    ano, período escolar e componente. O model é estritamente de leitura.
    """

    aluno_codigo = models.BigIntegerField(primary_key=True)
    codigo_situacao_matricula = models.IntegerField()
    numero_chamada = models.TextField(null=True)
    ano_letivo = models.IntegerField()
    modalidade_codigo = models.IntegerField()
    semestre = models.IntegerField()
    dre_codigo = models.TextField()
    dre_nome = models.TextField()
    ue_codigo = models.TextField()
    ue_nome = models.TextField()
    turma_codigo = models.TextField()
    turma_componente_codigo = models.TextField(null=True)
    turma_regular_codigo = models.TextField(null=True)
    turma_nome = models.TextField()
    ciclo = models.TextField(null=True)
    aluno_nome = models.TextField(null=True)
    nome_social = models.TextField(null=True)
    periodo_escolar_id = models.BigIntegerField(null=True)
    bimestre = models.IntegerField(null=True)
    componente_codigo = models.BigIntegerField(null=True)
    disciplina_nome = models.TextField(null=True)
    disciplina_nome_sgp = models.TextField(null=True)
    componente_pai_codigo = models.BigIntegerField(null=True)
    componente_pai_nome = models.TextField(null=True)
    lanca_nota = models.BooleanField(default=True)
    registra_frequencia = models.BooleanField(default=True)
    base_nacional = models.BooleanField(default=False)
    compartilhada = models.BooleanField(default=False)
    territorio_saber = models.BooleanField(default=False)
    componente_territorio_codigo = models.BigIntegerField(null=True)
    territorio_codigo = models.BigIntegerField(null=True)
    experiencia_pedagogica_codigo = models.BigIntegerField(null=True)
    territorio_nome = models.TextField(null=True)
    experiencia_pedagogica_nome = models.TextField(null=True)
    grupo_matriz_id = models.BigIntegerField(null=True)
    grupo_matriz_nome = models.TextField(null=True)
    area_conhecimento_id = models.BigIntegerField(null=True)
    area_conhecimento_nome = models.TextField(null=True)
    ordem_grupo_area = models.IntegerField(null=True)
    regencia = models.BooleanField(default=False)
    componentes_regencia = models.JSONField(default=list)
    componente_existia_no_periodo = models.BooleanField(null=True)
    conselho_classe_cadastrado = models.BooleanField(default=False)
    nota = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    conceito_id = models.BigIntegerField(null=True)
    conceito = models.TextField(null=True)
    total_aulas = models.IntegerField(null=True)
    total_presencas = models.IntegerField(null=True)
    total_ausencias = models.IntegerField(null=True)
    total_compensacoes = models.IntegerField(null=True)
    total_remotos = models.IntegerField(null=True)
    total_aulas_global = models.IntegerField(null=True)
    total_presencas_global = models.IntegerField(null=True)
    total_ausencias_global = models.IntegerField(null=True)
    total_compensacoes_global = models.IntegerField(null=True)
    total_remotos_global = models.IntegerField(null=True)
    media_frequencia = models.DecimalField(
        max_digits=10, decimal_places=2, null=True
    )
    tipo_nota = models.TextField(null=True)
    tipo_nota_descricao = models.TextField(null=True)
    origem_frequencia = models.TextField(null=True)
    parecer_conclusivo = models.TextField(null=True)
    recomendacoes_aluno = models.TextField(null=True)
    recomendacoes_familia = models.TextField(null=True)
    anotacoes_pedagogicas = models.TextField(null=True)

    class Meta:
        db_table = "mv_boletim"
        managed = False
