"""Testes do apresentador do relatório de boletins."""

from django.test import SimpleTestCase

from apps.boletim.relatorios.apresentador import montar_contexto_pdf


class TestApresentadorBoletinsPdf(SimpleTestCase):
    """Valida a preparação dos dados exibidos no PDF."""

    def test_distribui_quantidades_suportadas_por_pagina(self) -> None:
        """Empilha boletins em largura cheia, N por página."""
        boletins = [self._boletim(indice) for indice in range(7)]

        cenarios = (
            (1, 7, 1),
            (2, 4, 2),
            (6, 2, 3),
        )
        for (
            boletins_por_pagina,
            quantidade_paginas,
            linhas_primeira,
        ) in cenarios:
            with self.subTest(boletins_por_pagina=boletins_por_pagina):
                contexto = montar_contexto_pdf(
                    boletins,
                    boletins_por_pagina,
                )

                self.assertEqual(
                    len(contexto["paginas"]),
                    quantidade_paginas,
                )
                self.assertEqual(
                    len(contexto["paginas"][0]["linhas"]),
                    linhas_primeira,
                )
                if boletins_por_pagina == 6:
                    self.assertTrue(
                        all(
                            len(linha["boletins"]) == 2
                            for linha in contexto["paginas"][0]["linhas"]
                        )
                    )

    def test_formata_nota_conceito_e_frequencia(self) -> None:
        """Preserva conceito e formata frequência com duas casas."""
        boletim = self._boletim(1)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        componente = item["grupos"][0]["componentes"][0]
        self.assertEqual(componente["periodos"][0]["nota"], "S")
        self.assertEqual(componente["periodos"][0]["frequencia"], "95.00%")
        self.assertEqual(item["frequencia_global"], "90.00%")

    def test_exibe_ciclo_consolidado_no_cabecalho(self) -> None:
        """Exibe no cabeçalho o ciclo recebido da turma consolidada."""
        boletim = self._boletim(1)
        boletim["dados_aluno"]["ciclo"] = "Ciclo Interdisciplinar"

        contexto = montar_contexto_pdf([boletim], 2)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]

        self.assertEqual(item["dados"]["ciclo"], "Ciclo Interdisciplinar")

    def test_esconde_coluna_final_sem_nota_final(self) -> None:
        """Omite o par de colunas Final quando ninguém tem nota final."""
        boletim = self._boletim(1)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        self.assertFalse(item["possui_nota_final"])
        self.assertNotIn(0, item["periodos"])

    def test_usa_conceito_quando_ha_valor_p_s_ou_ns(self) -> None:
        """Troca o rótulo Nota por Conc. quando há conceito no boletim."""
        boletim = self._boletim(1)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        self.assertTrue(item["usa_conceito"])
        self.assertTrue(item["exibe_legenda"])

    def test_agrupa_componentes_por_matriz_em_tabelas_separadas(self) -> None:
        """Cada grupo de matriz vira uma tabela própria no relatório."""
        boletim = self._boletim_com_regencia(modalidade_codigo=5)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes_por_grupo = [
            [componente["nome"] for componente in grupo["componentes"]]
            for grupo in item["grupos"]
        ]
        self.assertEqual(
            nomes_por_grupo,
            [
                ["Matemática", "Português", "Arte"],
                ["Ciências", "Arte"],
            ],
        )

    def test_reune_matriz_repetida_em_uma_unica_tabela(self) -> None:
        """Não separa uma matriz quando seus itens chegam intercalados."""
        boletim = self._boletim_com_regencia(modalidade_codigo=5)
        componentes = boletim["componentes"]
        self.assertIsInstance(componentes, list)
        componentes[1], componentes[2] = componentes[2], componentes[1]

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes_por_grupo = [
            [componente["nome"] for componente in grupo["componentes"]]
            for grupo in item["grupos"]
        ]
        self.assertEqual(
            nomes_por_grupo,
            [
                ["Matemática", "Português", "Arte"],
                ["Ciências", "Arte"],
            ],
        )

    def test_insere_regencia_em_todos_os_grupos_da_turma_anual(self) -> None:
        """Turmas anuais repetem a regência ao final de cada grupo."""
        boletim = self._boletim_com_regencia(modalidade_codigo=5)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes = [
            [componente["nome"] for componente in grupo["componentes"]]
            for grupo in item["grupos"]
        ]
        self.assertEqual(
            nomes,
            [
                ["Matemática", "Português", "Arte"],
                ["Ciências", "Arte"],
            ],
        )
        primeira_regencia = item["grupos"][0]["componentes"][2]
        segunda_regencia = item["grupos"][1]["componentes"][1]
        self.assertTrue(primeira_regencia["primeira_linha_regencia"])
        self.assertTrue(segunda_regencia["primeira_linha_regencia"])
        self.assertEqual(primeira_regencia["linhas_regencia"], 1)
        self.assertEqual(segunda_regencia["linhas_regencia"], 1)

    def test_move_componente_normal_da_regencia_para_segundo_grupo(
        self,
    ) -> None:
        """Separa a linha normal da linha com frequência compartilhada."""
        boletim = self._boletim_com_regencia(modalidade_codigo=5)
        componentes = boletim["componentes"]
        regencias = boletim["regencias"]
        self.assertIsInstance(componentes, list)
        self.assertIsInstance(regencias, list)
        componentes.append(
            {
                "componente_codigo": 218,
                "disciplina_nome_sgp": "Libras",
                "grupo_matriz_id": 20,
                "lanca_nota": True,
                "bimestres": [{"bimestre": 1}],
            }
        )
        regencias[0]["componentes"][0]["componente_codigo"] = 218
        regencias[0]["componentes"][0]["disciplina_nome_sgp"] = "Libras"

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes = [
            [componente["nome"] for componente in grupo["componentes"]]
            for grupo in item["grupos"]
        ]
        self.assertEqual(
            nomes,
            [
                ["Matemática", "Português", "Libras"],
                ["Ciências", "Libras"],
            ],
        )

    def test_ordena_componentes_como_boletim_detalhado_de_referencia(
        self,
    ) -> None:
        """Reproduz grupos e ordem observados para o EOL 6795960."""
        boletim = self._boletim(6795960)
        nomes = {
            139: ("Arte", 1, True),
            6: ("Ed. Física", 1, True),
            1106: ("Língua Inglesa Compartilhada", 1, True),
            89: ("Ciências", 1, True),
            8: ("Geografia", 1, True),
            7: ("História", 1, True),
            218: ("Libras", 2, True),
            138: ("Língua Portuguesa", 1, True),
            2: ("Matemática", 1, True),
            1060: ("Laboratório de Educação Digital", 2, False),
            1061: ("Sala de leitura", 2, False),
        }
        boletim["componentes"] = [
            {
                "componente_codigo": codigo,
                "disciplina_nome_sgp": nome,
                "grupo_matriz_id": grupo,
                "lanca_nota": lanca_nota,
                "bimestres": [{"bimestre": 1}],
            }
            for codigo, (nome, grupo, lanca_nota) in nomes.items()
        ]
        filhos = [89, 8, 7, 218, 138, 2]
        boletim["regencias"] = [
            {
                "grupo_matriz_id": 1,
                "bimestres": [{"bimestre": 1}],
                "componentes": [
                    {
                        "componente_codigo": codigo,
                        "disciplina_nome_sgp": nomes[codigo][0],
                        "bimestres": [{"bimestre": 1}],
                    }
                    for codigo in filhos
                ],
            }
        ]

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes_por_grupo = [
            [componente["nome"] for componente in grupo["componentes"]]
            for grupo in item["grupos"]
        ]
        self.assertEqual(
            nomes_por_grupo,
            [
                [
                    "Arte",
                    "Ed. Física",
                    "Língua Inglesa Compartilhada",
                    "Ciências",
                    "Geografia",
                    "História",
                    "Libras",
                    "Língua Portuguesa",
                    "Matemática",
                ],
                [
                    "Laboratório de Educação Digital",
                    "Sala de leitura",
                    "Ciências",
                    "Geografia",
                    "História",
                    "Libras",
                    "Língua Portuguesa",
                    "Matemática",
                ],
            ],
        )
        primeira_regencia = item["grupos"][0]["componentes"][3]
        segunda_regencia = item["grupos"][1]["componentes"][2]
        self.assertTrue(primeira_regencia["primeira_linha_regencia"])
        self.assertTrue(segunda_regencia["primeira_linha_regencia"])
        self.assertEqual(primeira_regencia["linhas_regencia"], 6)
        self.assertEqual(segunda_regencia["linhas_regencia"], 6)

    def test_insere_regencia_antes_dos_grupos_em_turma_semestral(self) -> None:
        """Turmas semestrais (EJA) mostram a regência antes dos grupos."""
        boletim = self._boletim_com_regencia(modalidade_codigo=3)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        nomes = [
            componente["nome"]
            for grupo in item["grupos"]
            for componente in grupo["componentes"]
        ]
        self.assertEqual(
            nomes, ["Arte", "Matemática", "Português", "Ciências"]
        )

    def test_regencia_mostra_frequencia_uma_vez_com_rowspan(self) -> None:
        """A frequência da regência aparece só na primeira linha."""
        boletim = {
            "dados_aluno": {
                "ano_letivo": 2026,
                "modalidade_codigo": 5,
                "dre_nome": "DRE",
                "ue_nome": "UE",
                "turma_nome": "Turma",
                "aluno_codigo": 1,
                "aluno_nome": "Aluno",
                "nome_social": None,
            },
            "componentes": [],
            "regencias": [
                {
                    "bimestres": [
                        {
                            "bimestre": 1,
                            "total_aulas": 20,
                            "total_ausencias": 2,
                            "total_compensacoes": 0,
                        }
                    ],
                    "componentes": [
                        {
                            "disciplina_nome_sgp": "Arte",
                            "bimestres": [{"bimestre": 1, "conceito": "P"}],
                        },
                        {
                            "disciplina_nome_sgp": "Ed. Física",
                            "bimestres": [{"bimestre": 1, "conceito": "S"}],
                        },
                    ],
                }
            ],
        }

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        linhas = item["grupos"][0]["componentes"]
        self.assertEqual(len(linhas), 2)
        primeira, segunda = linhas
        self.assertTrue(primeira["eh_regencia"])
        self.assertTrue(primeira["primeira_linha_regencia"])
        self.assertEqual(primeira["linhas_regencia"], 2)
        self.assertEqual(primeira["periodos"][0]["frequencia"], "90.00%")
        self.assertTrue(segunda["eh_regencia"])
        self.assertNotIn("primeira_linha_regencia", segunda)
        self.assertNotIn("frequencia", segunda["periodos"][0])

    def test_exibe_recomendacoes_quando_informadas(self) -> None:
        """Extrai recomendações ao estudante e à família do bimestre."""
        boletim = self._boletim(1)
        boletim["componentes"][0]["bimestres"][0][
            "recomendacoes_aluno"
        ] = "Estudar mais"
        boletim["componentes"][0]["bimestres"][0][
            "recomendacoes_familia"
        ] = "Acompanhar tarefas"

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        self.assertEqual(item["recomendacoes_aluno"], "Estudar mais")
        self.assertEqual(item["recomendacoes_familia"], "Acompanhar tarefas")

    def test_exibe_recomendacoes_apenas_em_pagina_individual(self) -> None:
        """Replica a diferença entre os fluxos individual e coletivo."""
        boletim = self._boletim(1)

        individual = montar_contexto_pdf([boletim], 1)
        coletivo = montar_contexto_pdf([boletim], 2)

        item_individual = individual["paginas"][0]["linhas"][0]["boletins"][0]
        item_coletivo = coletivo["paginas"][0]["linhas"][0]["boletins"][0]
        self.assertTrue(item_individual["exibe_recomendacoes"])
        self.assertFalse(item_coletivo["exibe_recomendacoes"])

    def test_monta_turma_relatorio_com_abreviacao_da_modalidade(self) -> None:
        """Combina a abreviação da modalidade com o nome da turma."""
        boletim = self._boletim(1)

        contexto = montar_contexto_pdf([boletim], 1)

        item = contexto["paginas"][0]["linhas"][0]["boletins"][0]
        self.assertEqual(item["dados"]["turma_relatorio"], "EF - Turma")

    @staticmethod
    def _boletim_com_regencia(modalidade_codigo: int) -> dict[str, object]:
        """Cria um boletim com dois grupos de área e uma regência."""
        return {
            "dados_aluno": {
                "ano_letivo": 2026,
                "modalidade_codigo": modalidade_codigo,
                "dre_nome": "DRE",
                "ue_nome": "UE",
                "turma_nome": "Turma",
                "aluno_codigo": 1,
                "aluno_nome": "Aluno",
                "nome_social": None,
            },
            "componentes": [
                {
                    "disciplina_nome_sgp": "Português",
                    "ordem_grupo_area": 1,
                    "grupo_matriz_id": 10,
                    "bimestres": [{"bimestre": 1}],
                },
                {
                    "disciplina_nome_sgp": "Matemática",
                    "ordem_grupo_area": 1,
                    "grupo_matriz_id": 10,
                    "bimestres": [{"bimestre": 1}],
                },
                {
                    "disciplina_nome_sgp": "Ciências",
                    "ordem_grupo_area": 2,
                    "grupo_matriz_id": 20,
                    "bimestres": [{"bimestre": 1}],
                },
            ],
            "regencias": [
                {
                    "grupo_matriz_id": 10,
                    "bimestres": [{"bimestre": 1}],
                    "componentes": [
                        {
                            "disciplina_nome_sgp": "Arte",
                            "bimestres": [{"bimestre": 1}],
                        },
                    ],
                }
            ],
        }

    @staticmethod
    def _boletim(indice: int) -> dict[str, object]:
        """Cria um boletim mínimo para os cenários do apresentador."""
        return {
            "dados_aluno": {
                "ano_letivo": 2026,
                "modalidade_codigo": 5,
                "dre_nome": "DRE",
                "ue_nome": "UE",
                "turma_nome": "Turma",
                "aluno_codigo": indice,
                "aluno_nome": f"Aluno {indice}",
                "nome_social": None,
            },
            "componentes": [
                {
                    "disciplina_nome_sgp": "Matemática",
                    "bimestres": [
                        {
                            "bimestre": 1,
                            "nota": None,
                            "conceito": "S",
                            "sintese": None,
                            "total_aulas": 20,
                            "total_ausencias": 2,
                            "total_compensacoes": 1,
                            "total_aulas_global": 100,
                            "total_ausencias_global": 10,
                            "total_compensacoes_global": 0,
                            "parecer_conclusivo": "Promovido",
                        }
                    ],
                }
            ],
            "regencias": [],
        }
