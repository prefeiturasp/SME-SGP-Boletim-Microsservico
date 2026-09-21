# SME SGP Boletim MS

Microsserviço responsável pelo domínio de boletim do SGP. O projeto parte da
mesma arquitetura do `SME-IntegracaoEOL-Pedagogico-Microsservico`: Python
3.12, Django 5, Django REST Framework 3, autenticação por API key, OpenAPI e
separação entre view, service, repository e model.

## Estado atual

O projeto contém o núcleo executável e o app `boletim`, que mapeia a view
materializada `mv_boletim` com um model Django não gerenciado. Novos contratos
devem continuar usando o schema publicado pelo ETL, sem migrations no
microsserviço.

## Execução local

```bash
cp .env.example .env
python -m pip install -r requirements/local.txt
python manage.py runserver 0.0.0.0:8001
```

Com Docker:

```bash
cp .env.example .env
docker compose -f docker-compose-dev.yml up --build
```

## Observabilidade

O SME Sidecar SDK é inicializado no processo Django e fornece logs
estruturados, correlação de requisições e rastreamento distribuído. O
middleware reutiliza o header `X-Request-ID` recebido ou gera um novo valor e
o devolve na resposta.

No desenvolvimento, os logs estruturados são enviados ao `stdout`. Para
publicá-los também no RabbitMQ, configure uma fila exclusiva do serviço:

```env
SME_BROKER_URL=amqp://usuario:senha@rabbitmq:5672/%2F
SME_LOG_QUEUE=ms.boletim.logs
```

O rastreamento OpenTelemetry permanece desabilitado por padrão. Para ativá-lo
em um ambiente integrado ao Elastic APM ou a um OpenTelemetry Collector:

```env
SME_OTEL_ENABLED=true
SME_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
SME_OTEL_EXPORTER_OTLP_INSECURE=true
```

As configurações e credenciais reais devem ser injetadas pelo ambiente de
execução. Consulte [`.env.example`](.env.example) para a lista usada pelo
serviço.

Endpoints iniciais:

- `GET /api/v1/boletim/health/`: saúde pública do processo;
- `GET /api/v1/boletim/alunos/{alunoCodigo}/?anoLetivo=2026`: consulta o
  boletim consolidado na view materializada `mv_boletim`. A consulta também
  aceita `dreCodigo`, `ueCodigo`, `semestre`, `turmaCodigo`, `modalidade` e
  `bimestre` para restringir o contexto do boletim;
- `GET /api/v1/boletim/?anoLetivo=2026&dreCodigo=108200&ueCodigo=094501&semestre=1&modalidade=5&alunosCodigo=123&alunosCodigo=456`:
  consulta os boletins de vários alunos. Sem `alunosCodigo`, retorna todos os
  alunos encontrados no contexto informado;
- `/boletim/api/v1/schema/`: schema OpenAPI;
- `/boletim/api/v1/docs/`: Swagger UI.

## Criando um domínio

Crie um pacote em `apps/<dominio>/` com `api/urls.py`, `api/views.py`,
`serializers.py`, `services.py`, `repository.py`, `models.py` e `tests/`.
Registre o app em `INSTALLED_APPS` e as rotas em `config/urls.py`. O fluxo de
dependências obrigatório é:

```text
view -> service -> repository -> model/banco
```

Views cuidam apenas de HTTP e OpenAPI; services concentram os casos de uso;
repositories concentram ORM; models `managed=False` espelham o banco. Consulte
[`AGENTS.md`](AGENTS.md) e [`.agents/architecture.md`](.agents/architecture.md)
antes de implementar regras de negócio.

## Banco alimentado pelo Airflow

A variável `URL_BANCO_BOLETIM` deve apontar para o mesmo PostgreSQL de destino
da Connection `boletim_postgres` usada pela DAG `consolidar_boletim` do
`sme-airflow`. O app consulta somente `mv_boletim`; a criação das tabelas, as
cargas e o refresh das views continuam sob responsabilidade da DAG e do
Flyway. O microsserviço não executa migrations nem atualiza esses dados.

## Qualidade

```bash
black --check .
ruff check .
mypy apps config
python -m coverage run --source=apps manage.py test --no-input
python -m coverage report --show-missing --fail-under=80
```

Os mesmos comandos podem ser executados pelos scripts em `scripts/` usando o
container de desenvolvimento.
