"""Casos de uso do domínio de boletim."""

from apps.boletim.models import Boletim
from apps.boletim.repository import BoletimRepository

_MODALIDADES_SEMESTRAIS = frozenset({3, 10})
_BIMESTRES_ANUAIS = (1, 2, 3, 4)
_BIMESTRES_SEMESTRAIS = (1, 2)
_CAMPOS_SEM_DADOS = (
    "periodo_escolar_id",
    "componente_existia_no_periodo",
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
    "origem_frequencia",
    "parecer_conclusivo",
    "recomendacoes_aluno",
    "recomendacoes_familia",
    "anotacoes_pedagogicas",
)


class BoletimService:
    """Orquestra consultas ao boletim consolidado."""

    def __init__(self, repository: BoletimRepository | None = None) -> None:
        """Inicializa o serviço com seu repositório.

        Args:
            repository: Repositório opcional para consulta dos dados.
        """
        self._repository = repository or BoletimRepository()

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
    ) -> dict[str, object]:
        """Lista o boletim de um aluno no ano letivo informado.

        Args:
            aluno_codigo: Código do aluno no EOL.
            ano_letivo: Ano letivo consultado.
            bimestre: Bimestre opcional usado como filtro.
            dre_codigo: Código opcional da DRE.
            ue_codigo: Código opcional da unidade escolar.
            semestre: Semestre opcional da turma.
            turma_codigo: Código opcional da turma.
            modalidade: Código opcional da modalidade.

        Returns:
            Registros consolidados do boletim.
        """
        registros = list(
            self._repository.listar_por_aluno(
                aluno_codigo=aluno_codigo,
                ano_letivo=ano_letivo,
                bimestre=None,
                dre_codigo=dre_codigo,
                ue_codigo=ue_codigo,
                semestre=semestre,
                turma_codigo=turma_codigo,
                modalidade=modalidade,
            )
        )
        if not registros:
            return {"dados_aluno": None, "componentes": [], "regencias": []}

        modelo_aluno = registros[0]
        registros = self._completar_bimestres(registros)
        if bimestre is not None:
            registros = [
                registro
                for registro in registros
                if registro.bimestre == bimestre
            ]
        return self._agrupar_resposta(modelo_aluno, registros)

    def listar_boletins(
        self,
        ano_letivo: int,
        dre_codigo: str,
        ue_codigo: str,
        semestre: int,
        modalidade: int,
        alunos_codigo: list[int],
        turma_codigo: str | None = None,
        bimestre: int | None = None,
    ) -> list[dict[str, object]]:
        """Lista boletins de vários alunos no contexto informado.

        Args:
            ano_letivo: Ano letivo consultado.
            dre_codigo: Código da DRE.
            ue_codigo: Código da unidade escolar.
            semestre: Semestre da turma.
            modalidade: Código da modalidade.
            alunos_codigo: Códigos dos alunos; vazio seleciona todos.
            turma_codigo: Código opcional da turma.
            bimestre: Bimestre opcional usado como filtro de exibição.

        Returns:
            Boletins agrupados por aluno e turma.
        """
        registros = self._repository.listar_boletins(
            ano_letivo=ano_letivo,
            dre_codigo=dre_codigo,
            ue_codigo=ue_codigo,
            semestre=semestre,
            modalidade=modalidade,
            alunos_codigo=alunos_codigo,
            turma_codigo=turma_codigo,
        )
        grupos: dict[tuple[int, str], list[Boletim]] = {}
        for registro in registros:
            chave = (registro.aluno_codigo, registro.turma_codigo)
            grupos.setdefault(chave, []).append(registro)

        boletins: list[dict[str, object]] = []
        for registros_aluno in grupos.values():
            modelo_aluno = registros_aluno[0]
            registros_completos = self._completar_bimestres(registros_aluno)
            if bimestre is not None:
                registros_completos = [
                    registro
                    for registro in registros_completos
                    if registro.bimestre == bimestre
                ]
            boletins.append(
                self._agrupar_resposta(modelo_aluno, registros_completos)
            )
        return boletins

    @staticmethod
    def _agrupar_resposta(
        modelo_aluno: Boletim,
        registros: list[Boletim],
    ) -> dict[str, object]:
        """Agrupa os dados do aluno, componentes e bimestres.

        Args:
            modelo_aluno: Registro usado como fonte da identificação.
            registros: Linhas do boletim já complementadas e filtradas.

        Returns:
            Estrutura hierárquica do boletim do aluno.
        """
        dados_aluno = {
            "ano_letivo": modelo_aluno.ano_letivo,
            "modalidade_codigo": modelo_aluno.modalidade_codigo,
            "semestre": modelo_aluno.semestre,
            "dre_codigo": modelo_aluno.dre_codigo,
            "dre_nome": modelo_aluno.dre_nome,
            "ue_codigo": modelo_aluno.ue_codigo,
            "ue_nome": modelo_aluno.ue_nome,
            "turma_codigo": modelo_aluno.turma_codigo,
            "turma_nome": modelo_aluno.turma_nome,
            "aluno_codigo": modelo_aluno.aluno_codigo,
            "aluno_nome": modelo_aluno.aluno_nome,
            "nome_social": modelo_aluno.nome_social,
        }
        componentes_por_chave: dict[
            tuple[str, int | None, str | None], dict[str, object]
        ] = {}
        regencias_por_codigo: dict[
            tuple[str, int | None], dict[str, object]
        ] = {}
        for registro in registros:
            if registro.regencia:
                BoletimService._agrupar_regencia(
                    regencias_por_codigo,
                    registro,
                )
                continue
            chave = (
                registro.turma_componente_codigo or registro.turma_codigo,
                registro.componente_codigo,
                registro.disciplina_nome_sgp,
            )
            componente = componentes_por_chave.setdefault(
                chave,
                {
                    "componente_codigo": registro.componente_codigo,
                    "disciplina_nome": registro.disciplina_nome,
                    "disciplina_nome_sgp": registro.disciplina_nome_sgp,
                    "componente_pai_codigo": (registro.componente_pai_codigo),
                    "componente_pai_nome": registro.componente_pai_nome,
                    "lanca_nota": registro.lanca_nota,
                    "registra_frequencia": registro.registra_frequencia,
                    "base_nacional": registro.base_nacional,
                    "compartilhada": registro.compartilhada,
                    "territorio_saber": registro.territorio_saber,
                    "componente_territorio_codigo": (
                        registro.componente_territorio_codigo
                    ),
                    "territorio_codigo": registro.territorio_codigo,
                    "experiencia_pedagogica_codigo": (
                        registro.experiencia_pedagogica_codigo
                    ),
                    "territorio_nome": registro.territorio_nome,
                    "experiencia_pedagogica_nome": (
                        registro.experiencia_pedagogica_nome
                    ),
                    "turma_regular_codigo": registro.turma_regular_codigo,
                    "turma_componente_codigo": (
                        registro.turma_componente_codigo
                        or registro.turma_codigo
                    ),
                    "grupo_matriz_id": registro.grupo_matriz_id,
                    "grupo_matriz_nome": registro.grupo_matriz_nome,
                    "area_conhecimento_id": registro.area_conhecimento_id,
                    "area_conhecimento_nome": (
                        registro.area_conhecimento_nome
                    ),
                    "ordem_grupo_area": registro.ordem_grupo_area,
                    "regencia": registro.regencia,
                    "bimestres": [],
                },
            )
            bimestres = componente["bimestres"]
            if isinstance(bimestres, list):
                bimestres.append(
                    BoletimService._dados_bimestre(
                        registro,
                        incluir_nota=registro.lanca_nota,
                        incluir_frequencia=registro.registra_frequencia,
                        incluir_sintese=not registro.lanca_nota,
                    )
                )

        return {
            "dados_aluno": dados_aluno,
            "componentes": sorted(
                componentes_por_chave.values(),
                key=BoletimService._chave_ordenacao_componente,
            ),
            "regencias": BoletimService._finalizar_regencias(
                regencias_por_codigo
            ),
        }

    @staticmethod
    def _dados_bimestre(
        registro: Boletim,
        incluir_nota: bool = True,
        incluir_frequencia: bool = True,
        incluir_sintese: bool = False,
    ) -> dict[str, object]:
        """Mapeie os dados acadêmicos de um bimestre.

        Args:
            registro: Linha consolidada usada na resposta.
            incluir_nota: Indica se nota e conceito devem ser exibidos.
            incluir_frequencia: Indica se a frequência deve ser exibida.
            incluir_sintese: Indica se a síntese `F` ou `NF` deve ser gerada.

        Returns:
            Dados do período com as regras de exibição aplicadas.
        """
        possui_conselho = bool(registro.conselho_classe_cadastrado)
        exibir_nota = incluir_nota and possui_conselho
        exibir_frequencia = incluir_frequencia and possui_conselho

        return {
            "bimestre": registro.bimestre,
            "periodo_escolar_id": registro.periodo_escolar_id,
            "componente_existia_no_periodo": (
                registro.componente_existia_no_periodo
            ),
            "conselho_classe_cadastrado": (
                registro.conselho_classe_cadastrado
            ),
            "nota": registro.nota if exibir_nota else None,
            "conceito_id": registro.conceito_id if exibir_nota else None,
            "conceito": registro.conceito if exibir_nota else None,
            "total_aulas": (
                registro.total_aulas if exibir_frequencia else None
            ),
            "total_presencas": (
                registro.total_presencas if exibir_frequencia else None
            ),
            "total_ausencias": (
                registro.total_ausencias if exibir_frequencia else None
            ),
            "total_compensacoes": (
                registro.total_compensacoes if exibir_frequencia else None
            ),
            "total_remotos": (
                registro.total_remotos if exibir_frequencia else None
            ),
            "total_aulas_global": registro.total_aulas_global,
            "total_presencas_global": registro.total_presencas_global,
            "total_ausencias_global": registro.total_ausencias_global,
            "total_compensacoes_global": (registro.total_compensacoes_global),
            "total_remotos_global": registro.total_remotos_global,
            "media_frequencia": registro.media_frequencia,
            "tipo_nota": registro.tipo_nota,
            "tipo_nota_descricao": registro.tipo_nota_descricao,
            "sintese": (
                BoletimService._obter_sintese_frequencia(registro)
                if incluir_sintese
                else None
            ),
            "origem_frequencia": (
                registro.origem_frequencia if exibir_frequencia else None
            ),
            "parecer_conclusivo": registro.parecer_conclusivo,
            "recomendacoes_aluno": registro.recomendacoes_aluno,
            "recomendacoes_familia": registro.recomendacoes_familia,
            "anotacoes_pedagogicas": registro.anotacoes_pedagogicas,
        }

    @staticmethod
    def _agrupar_regencia(
        regencias: dict[tuple[str, int | None], dict[str, object]],
        registro: Boletim,
    ) -> None:
        """Agrupe frequência no pai e notas nas disciplinas de regência.

        Args:
            regencias: Agrupamentos indexados pelo componente pai.
            registro: Linha da disciplina filha incorporada ao agrupamento.
        """
        codigo_pai = registro.componente_pai_codigo
        chave_regencia = (
            registro.turma_componente_codigo or registro.turma_codigo,
            codigo_pai,
        )
        regencia = regencias.setdefault(
            chave_regencia,
            {
                "codigo": codigo_pai,
                "nome": registro.componente_pai_nome,
                "registra_frequencia": registro.registra_frequencia,
                "bimestres": {},
                "componentes": {},
            },
        )
        bimestres = regencia["bimestres"]
        if isinstance(bimestres, dict):
            dados_frequencia = BoletimService._dados_bimestre(
                registro,
                incluir_nota=False,
                incluir_frequencia=registro.registra_frequencia,
                incluir_sintese=False,
            )
            existente = bimestres.get(registro.bimestre)
            if existente is None or (
                isinstance(existente, dict)
                and existente["total_aulas"] is None
                and dados_frequencia["total_aulas"] is not None
            ):
                bimestres[registro.bimestre] = dados_frequencia

        componentes = regencia["componentes"]
        if not isinstance(componentes, dict):
            return
        componente = componentes.setdefault(
            registro.componente_codigo,
            {
                "componente_codigo": registro.componente_codigo,
                "disciplina_nome": registro.disciplina_nome,
                "disciplina_nome_sgp": registro.disciplina_nome_sgp,
                "lanca_nota": registro.lanca_nota,
                "bimestres": [],
            },
        )
        bimestres_componente = componente["bimestres"]
        if isinstance(bimestres_componente, list):
            bimestres_componente.append(
                BoletimService._dados_bimestre(
                    registro,
                    incluir_nota=registro.lanca_nota,
                    incluir_frequencia=False,
                    incluir_sintese=False,
                )
            )

    @staticmethod
    def _finalizar_regencias(
        regencias: dict[tuple[str, int | None], dict[str, object]],
    ) -> list[dict[str, object]]:
        """Converta agrupamentos internos no contrato ordenado da resposta.

        Args:
            regencias: Agrupamentos internos indexados em dicionários.

        Returns:
            Regências com bimestres e componentes representados em listas.
        """
        resultado: list[dict[str, object]] = []
        for regencia in regencias.values():
            bimestres = regencia["bimestres"]
            componentes = regencia["componentes"]
            if isinstance(bimestres, dict):
                regencia["bimestres"] = list(bimestres.values())
            if isinstance(componentes, dict):
                regencia["componentes"] = sorted(
                    componentes.values(),
                    key=lambda item: str(item["disciplina_nome_sgp"] or ""),
                )
            resultado.append(regencia)
        return resultado

    @staticmethod
    def _chave_ordenacao_componente(
        componente: dict[str, object],
    ) -> tuple[int, int, str]:
        """Produza a chave oficial de ordenação do componente.

        Args:
            componente: Componente com ordem, grupo matriz e nome.

        Returns:
            Chave composta usada na ordenação da resposta.
        """
        return (
            BoletimService._inteiro_ordenacao(componente["ordem_grupo_area"]),
            BoletimService._inteiro_ordenacao(componente["grupo_matriz_id"]),
            str(componente["disciplina_nome_sgp"] or ""),
        )

    @staticmethod
    def _inteiro_ordenacao(valor: object) -> int:
        """Normalize identificadores numéricos usados na ordenação.

        Args:
            valor: Identificador possivelmente nulo ou não numérico.

        Returns:
            Identificador inteiro ou zero quando o valor não for inteiro.
        """
        return valor if isinstance(valor, int) else 0

    @staticmethod
    def _obter_sintese_frequencia(registro: Boletim) -> str | None:
        """Produza `F` ou `NF` para o fechamento final sem nota.

        Args:
            registro: Linha final contendo totais e média de frequência.

        Returns:
            Síntese de frequência ou `None` quando ela não for aplicável.
        """
        if (
            registro.bimestre not in (0, None)
            or not registro.conselho_classe_cadastrado
            or registro.media_frequencia is None
        ):
            return None
        if not registro.total_aulas or registro.total_ausencias is None:
            return "F"
        compensacoes = registro.total_compensacoes or 0
        presencas = registro.total_aulas - registro.total_ausencias
        percentual = (presencas + compensacoes) * 100 / registro.total_aulas
        return "F" if percentual >= float(registro.media_frequencia) else "NF"

    @staticmethod
    def _completar_bimestres(registros: list[Boletim]) -> list[Boletim]:
        """Cria registros vazios para os bimestres sem dados.

        Args:
            registros: Linhas existentes do boletim do aluno.

        Returns:
            Linhas originais e complementares ordenadas por bimestre.
        """
        modalidade = registros[0].modalidade_codigo
        bimestres = (
            _BIMESTRES_SEMESTRAIS
            if modalidade in _MODALIDADES_SEMESTRAIS
            else _BIMESTRES_ANUAIS
        )
        grupos: dict[tuple[str, int | None, str | None], list[Boletim]] = {}
        for registro in registros:
            chave = (
                registro.turma_componente_codigo or registro.turma_codigo,
                registro.componente_codigo,
                registro.disciplina_nome_sgp,
            )
            grupos.setdefault(chave, []).append(registro)

        resultado = [
            registro
            for registro in registros
            if registro.bimestre in (*bimestres, 0, None)
        ]
        for registros_componente in grupos.values():
            bimestres_existentes = {
                registro.bimestre for registro in registros_componente
            }
            modelo = registros_componente[0]
            for numero in bimestres:
                if numero not in bimestres_existentes:
                    resultado.append(
                        BoletimService._criar_registro_vazio(modelo, numero)
                    )

        return sorted(resultado, key=BoletimService._chave_ordenacao)

    @staticmethod
    def _criar_registro_vazio(modelo: Boletim, bimestre: int) -> Boletim:
        """Produza uma cópia do componente sem dados acadêmicos.

        Args:
            modelo: Linha usada como origem dos metadados do componente.
            bimestre: Número do período complementar criado.

        Returns:
            Linha transitória com os dados acadêmicos vazios.
        """
        valores = {
            campo.attname: getattr(modelo, campo.attname)
            for campo in Boletim._meta.concrete_fields
        }
        valores["bimestre"] = bimestre
        for campo in _CAMPOS_SEM_DADOS:
            valores[campo] = None
        valores["conselho_classe_cadastrado"] = False
        return Boletim(**valores)

    @staticmethod
    def _chave_ordenacao(registro: Boletim) -> tuple[int, str, int]:
        """Produza a chave de ordenação das linhas do boletim.

        Args:
            registro: Linha consolidada do boletim.

        Returns:
            Chave composta por bimestre, disciplina e componente.
        """
        return (
            registro.bimestre or 0,
            registro.disciplina_nome_sgp or "",
            registro.componente_codigo or 0,
        )
