COMPOSE = docker compose -f docker-compose-dev.yml
EXEC = $(COMPOSE) exec boletim
RUN = $(COMPOSE) run --rm -T boletim
COVERAGE_ARGS = --source=apps

.PHONY: help run build stop test test-core test-boletim lint precommit \
	coverage schema docs docs-clean

help:
	@echo "Comandos disponíveis:"
	@echo "  make run           Inicia o ambiente de desenvolvimento"
	@echo "  make build         Reconstrói e inicia o ambiente"
	@echo "  make stop          Encerra o ambiente"
	@echo "  make test          Executa todos os testes com cobertura mínima de 80%"
	@echo "  make test-core     Executa os testes do app core"
	@echo "  make test-boletim  Executa os testes do app boletim"
	@echo "  make lint          Executa Black, Ruff e mypy"
	@echo "  make precommit     Executa todos os hooks do pre-commit"
	@echo "  make coverage      Gera o relatório HTML de cobertura em htmlcov/"
	@echo "  make schema        Gera o schema OpenAPI em schema.yml"
	@echo "  make docs          Gera a documentação Sphinx"
	@echo "  make docs-clean    Remove o build da documentação Sphinx"

run:
	$(COMPOSE) up

build:
	$(COMPOSE) up --build

stop:
	$(COMPOSE) down

test:
	$(RUN) sh -c "python -m coverage run $(COVERAGE_ARGS) manage.py test --no-input && python -m coverage report --show-missing --fail-under=80"

test-core:
	$(RUN) python manage.py test apps.core --no-input

test-boletim:
	$(RUN) python manage.py test apps.boletim --no-input

lint:
	$(EXEC) sh -c "black --check . && ruff check . && mypy apps config"

precommit:
	$(RUN) pre-commit run --all-files

coverage:
	$(RUN) sh -c "python -m coverage run $(COVERAGE_ARGS) manage.py test --no-input && python -m coverage report --show-missing --fail-under=80 && python -m coverage html -d htmlcov"
	@echo "Relatório gerado em htmlcov/index.html"

schema:
	$(EXEC) python manage.py spectacular --file schema.yml

docs:
	$(RUN) sphinx-build -b html docs docs/_build/html

docs-clean:
	$(RUN) rm -rf docs/_build
