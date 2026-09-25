# SME-SGP-Boletim-Microsservico

Expõe os dados consolidados dos boletins escolares do SGP e gera os boletins
em PDF, mantendo as regras de exibição do SME-ServidorRelatorios.

---

## Estrutura dos Apps

| App | Responsabilidade | Prefixo API |
|-----|------------------|-------------|
| `apps.boletim` | Consulta, organização e geração dos boletins escolares | `/api/boletim/` |
| `apps.core` | Autenticação por API key, health check e infraestrutura comum | `/api/boletim/` |

### Modelo ETL Coberto

- `Boletim` (`mv_boletim`)

O modelo é somente leitura (`managed=False`). O schema e a materialized view
são mantidos pela DAG `consolidar_boletim` do projeto `sme-airflow`; este
microsserviço não cria migrations para essa estrutura.

---

## Pré-requisitos

- Python 3.12+
- PostgreSQL com a `mv_boletim` criada e alimentada pelo ETL
- Docker e Docker Compose para execução em container

---

## Rodar Localmente

```bash
cp .env.example .env
python -m pip install -r requirements/local.txt
python manage.py runserver 0.0.0.0:8001
```

Acesse a documentação em:
http://localhost:8001/boletim/api/docs/

---

## Rodar com Docker

```bash
cp .env.example .env
docker compose -f docker-compose-dev.yml up --build
```

Acesse a documentação em:
http://localhost:8001/boletim/api/docs/

---

## Testes

```bash
# Suíte Django
python manage.py test

# Cobertura mínima de 80%
python -m coverage run --source=apps manage.py test --no-input
python -m coverage report --show-missing --fail-under=80

# Qualidade e tipagem
black --check .
ruff check .
mypy apps config
```

Os testes usam SQLite em memória e criam temporariamente as tabelas dos
models não gerenciados.

---

## Gerar Documentação Sphinx com Docker

```bash
docker compose -f docker-compose-dev.yml run --rm boletim \
  sphinx-build -b html docs docs/_build/html
```

A documentação HTML será gerada em `docs/_build/html/index.html`.

---

## Autenticação

Os endpoints do domínio exigem o header configurado em `API_KEY_HEADER` com o
valor de `API_KEY`. O health check e a documentação OpenAPI são públicos.

Exemplo:

```bash
curl -H "X-API-Key: dev-key-default" \
  "http://localhost:8001/api/boletim/?ano_letivo=2026&dre_codigo=108200&ue_codigo=094501&semestre=1&modalidade=5"
```

---

## Documentação da API

| URL | Descrição |
|-----|-----------|
| `/boletim/api/docs/` | Swagger UI |
| `/boletim/api/schema/` | Schema OpenAPI |

---

## Endpoints Implementados

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/api/boletim/health/` | Verifica a saúde do processo. |
| GET | `/api/boletim/` | Retorna os boletins consolidados dos estudantes selecionados. |
| GET | `/api/boletim/pdf/` | Gera os boletins selecionados em PDF. |

### Filtros dos boletins

| Parâmetro | Obrigatório | Descrição |
|-----------|-------------|-----------|
| `ano_letivo` | Sim | Ano letivo a partir de 2000. |
| `dre_codigo` | Sim | Código da Diretoria Regional de Educação. |
| `ue_codigo` | Sim | Código da unidade escolar. |
| `semestre` | Sim | Semestre da turma (`0`, `1` ou `2`). |
| `modalidade` | Sim | Código da modalidade de ensino. |
| `turma_codigo` | Não | Restringe a consulta a uma turma. |
| `alunos_codigo` | Não | Lista repetível de códigos de estudantes; sem ela, retorna todos do contexto. |
| `considera_inativo` | Não | Inclui estudantes inativos quando `true`; o padrão é `false`. |
| `bimestre` | Não | Restringe a consulta a um bimestre entre `1` e `4`. |
| `boletins_por_pagina` | Somente PDF | Quantidade de boletins por página: `1`, `2` ou `6`; o padrão é `2`. |

---

## Variáveis de Ambiente

### Aplicação

| Variável | Padrão local | Descrição |
|----------|--------------|-----------|
| `DJANGO_SECRET_KEY` | Definido em `.env.example` | Chave de assinatura do Django; deve ser substituída fora do ambiente local. |
| `DJANGO_DEBUG` | `1` | Habilita o modo de depuração. |
| `DJANGO_ALLOWED_HOSTS` | `*` | Hosts aceitos pelo Django. |
| `API_KEY` | `dev-key-default` | Credencial exigida pelos endpoints protegidos. |
| `API_KEY_HEADER` | `X-API-Key` | Nome do header da credencial. |
| `PORT_WEB` | `8001` | Porta HTTP do ambiente de desenvolvimento. |
| `PORT_DEBUGPY` | `5678` | Porta reservada para depuração remota. |
| `URL_BANCO_BOLETIM` | — | URL de conexão com o PostgreSQL do boletim. |
| `DB_POOL_SIZE` | `5` | Quantidade de conexões persistentes do pool. |

### SME Sidecar SDK

| Variável | Padrão local | Descrição |
|----------|--------------|-----------|
| `SME_SDK_ENABLED` | `true` | Habilita a integração com o SDK. |
| `SME_SERVICE_NAME` | `sme_sgp_boletim_ms` | Nome do serviço nos logs e traces. |
| `SME_SERVICE_VERSION` | `0.1.0` | Versão publicada na telemetria. |
| `SME_ENVIRONMENT` | `local` | Ambiente de execução. |
| `SME_LOGGING_ENABLED` | `true` | Habilita os logs estruturados. |
| `SME_LOG_LEVEL` | `INFO` | Nível mínimo dos logs. |
| `SME_LOG_FORMAT` | `json` | Formato dos logs. |
| `SME_CORRELATION_ID_HEADER` | `X-Request-ID` | Header usado para correlação das requisições. |
| `SME_BROKER_URL` | Definido em `.env.example` | URL AMQP para o transporte opcional de logs. |
| `SME_LOG_QUEUE` | — | Fila exclusiva para publicação dos logs. |
| `SME_OBSERVABILITY_BACKEND` | `elastic` | Backend de observabilidade. |
| `SME_OTEL_ENABLED` | `false` | Ativa o rastreamento OpenTelemetry. |
| `SME_OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | Endpoint OTLP gRPC. |
| `SME_OTEL_EXPORTER_OTLP_HEADERS` | — | Headers do exporter no formato `chave=valor`. |
| `SME_OTEL_EXPORTER_OTLP_INSECURE` | `true` | Desabilita TLS no transporte OTLP. |

As configurações e credenciais reais devem ser injetadas pelo ambiente de
execução. Consulte [`.env.example`](.env.example) para a relação atualizada.
