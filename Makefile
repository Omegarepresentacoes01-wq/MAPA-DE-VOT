# Mapa de Voto — Makefile
# Comandos principais para desenvolvimento e operação

COMPOSE = docker compose -f infra/compose/docker-compose.yml --env-file .env
PYTHON = python

.PHONY: help setup up down logs shell-api shell-db migrate migrate-create \
        seed-sources ingest-tse-2022 ingest-ibge index-search test lint web web-install

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────────────────────────
# Setup inicial
# ──────────────────────────────────────────────────────────────────

setup: ## Configuração inicial: copia .env, cria diretórios de dados
	@cp -n .env.example .env || true
	@mkdir -p data/raw data/staging
	@echo "✅ Setup concluído. Edite .env antes de subir os serviços."

web-install: ## Instala as dependências do frontend local
	@npm --prefix apps/web ci

web: ## Inicia a demonstração local do frontend em http://localhost:3000
	@npm --prefix apps/web run dev

# ──────────────────────────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────────────────────────

up: ## Sobe todos os serviços
	$(COMPOSE) up -d

up-infra: ## Sobe apenas infraestrutura (postgres, redis, minio, meilisearch)
	$(COMPOSE) up -d postgres redis minio meilisearch pg_tileserv

down: ## Para todos os serviços
	$(COMPOSE) down

logs: ## Acompanha logs de todos os serviços
	$(COMPOSE) logs -f

logs-api: ## Logs da API
	$(COMPOSE) logs -f api

logs-worker: ## Logs do worker
	$(COMPOSE) logs -f worker

ps: ## Status dos serviços
	$(COMPOSE) ps

shell-api: ## Shell no container da API
	$(COMPOSE) exec api bash

shell-db: ## psql no PostgreSQL
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-mapa} -d $${POSTGRES_DB:-mapa_voto}

shell-worker: ## Shell no container do worker
	$(COMPOSE) exec worker bash

# ──────────────────────────────────────────────────────────────────
# Banco de dados
# ──────────────────────────────────────────────────────────────────

migrate: ## Aplica migrations pendentes
	$(COMPOSE) exec api alembic -c packages/db/alembic.ini upgrade head

migrate-create: ## Cria nova migration (uso: make migrate-create MSG="descrição")
	$(COMPOSE) exec api alembic -c packages/db/alembic.ini revision --autogenerate -m "$(MSG)"

migrate-history: ## Histórico de migrations
	$(COMPOSE) exec api alembic -c packages/db/alembic.ini history

# ──────────────────────────────────────────────────────────────────
# Seeds e ingestão
# ──────────────────────────────────────────────────────────────────

seed-sources: ## Popula tabela data_source com fontes oficiais
	$(COMPOSE) exec worker python scripts/seed_sources.py

ingest-tse-2022: ## Ingestão completa TSE 2022 (candidaturas + resultados + finanças)
	$(COMPOSE) exec worker python scripts/ingest.py tse --ano 2022

ingest-tse-uf: ## Ingestão TSE 2022 para uma UF (uso: make ingest-tse-uf UF=SP)
	$(COMPOSE) exec worker python scripts/ingest.py tse --ano 2022 --uf $(UF)

ingest-ibge: ## Ingestão malhas municipais IBGE (geometrias)
	$(COMPOSE) exec worker python scripts/ingest.py ibge territories

ingest-ibge-census: ## Ingestão dados Censo 2022 via SIDRA
	$(COMPOSE) exec worker python scripts/ingest.py ibge census --ano 2022

build-indexes: ## Constrói índices espaciais e de performance no PostgreSQL
	$(COMPOSE) exec api python scripts/build_indexes.py

index-search: ## (Re)indexa candidatos e municípios no Meilisearch
	$(COMPOSE) exec api python scripts/index_search.py

# ──────────────────────────────────────────────────────────────────
# Qualidade e testes
# ──────────────────────────────────────────────────────────────────

test: ## Roda todos os testes de integração
	$(COMPOSE) exec api pytest apps/api/tests/ -v --tb=short
	$(COMPOSE) exec worker pytest apps/worker/tests/ -v --tb=short

test-api: ## Roda apenas os testes da API
	$(COMPOSE) exec api pytest apps/api/tests/ -v --tb=short

test-system: ## Roda apenas os testes de sistema (health, root, docs)
	$(COMPOSE) exec api pytest apps/api/tests/test_system.py -v

lint: ## Lint com ruff
	$(COMPOSE) exec api ruff check apps/api packages/

reconcile: ## Reconcilia totais de votos com a fonte oficial (uso: make reconcile ANO=2022)
	$(COMPOSE) exec worker python scripts/reconcile.py --ano $(or $(ANO),2022)

reconcile-uf: ## Reconcilia totais por UF (uso: make reconcile-uf ANO=2022 UF=SP)
	$(COMPOSE) exec worker python scripts/reconcile.py --ano $(or $(ANO),2022) --uf $(UF)
