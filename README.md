# Mapa de Voto — Sistema Privado de Inteligência Eleitoral e Territorial

Sistema interno para consulta, análise e operação eleitoral com base em dados oficiais (TSE, IBGE e fontes complementares). O acesso será restrito a pessoas autorizadas por login; não há cadastro aberto, assinatura ou oferta de API pública.

---

## Arquitetura

```
mapa-de-voto/
├── apps/
│   ├── api/        FastAPI — serving e exportações
│   ├── web/        Next.js — frontend
│   └── worker/     Celery — ETL e jobs assíncronos
├── packages/
│   ├── db/         SQLAlchemy + Alembic (modelos e migrations)
│   ├── etl/        Pipelines Python (polars, geopandas)
│   └── shared/     Schemas Pydantic compartilhados
├── infra/
│   ├── docker/     Dockerfiles por serviço
│   └── compose/    docker-compose.yml
├── data/
│   ├── raw/        Arquivos brutos originais (nunca editados)
│   └── staging/    Dados normalizados intermediários
└── scripts/        CLI de ingestão e manutenção
```

## Stack

| Serviço | Tecnologia |
|---------|-----------|
| Banco | PostgreSQL 16 + PostGIS 3.4 |
| API | FastAPI + SQLAlchemy async |
| Frontend | Next.js 15 (App Router) |
| Mapas | MapLibre GL JS + pg_tileserv |
| Busca | Meilisearch |
| Cache | Redis 7 |
| Fila | Celery + Redis |
| Storage bruto | MinIO (S3-compatible) |
| ETL | Python + Polars + GeoPandas |

---

## Início rápido

```bash
# 1. Clone e configure
git clone <repo> && cd mapa-de-voto
make setup          # copia .env.example → .env

# 2. Edite .env com suas senhas

# 3. Sobe infraestrutura
make up-infra       # postgres, redis, minio, meilisearch, pg_tileserv

# 4. Aplica migrations
make migrate

# 5. Seed de fontes
make seed-sources

# 6. Ingestão TSE 2022
make ingest-tse-2022

# 7. Ingestão IBGE
make ingest-ibge

# 8. Indexa busca
make index-search

# 9. Sobe API e frontend
make up
```

API disponível em: http://localhost:8000/docs  
Frontend em: http://localhost:3000  
MinIO Console: http://localhost:9001  
Meilisearch: http://localhost:7700  

### Demonstração local sem Docker

Para testar a interface sem banco ou serviços de infraestrutura, use:

```bash
make web-install  # apenas na primeira vez
make web
```

Abra http://localhost:3000. O sistema mostra dados de demonstração identificados como tal; não há ingestão, persistência ou consulta aos dados oficiais nesse modo.

O acesso local usa inicialmente `admin@mapadevoto.local` e `mapa-local-2026`. Antes de disponibilizar o sistema a outra pessoa, defina `MAPA_ADMIN_EMAIL`, `MAPA_ADMIN_PASSWORD` e `MAPA_SESSION_SECRET` em um arquivo `.env.local` que não é versionado.

---

## Fontes de dados

| Fonte | URL | Tipo | Classificação |
|-------|-----|------|--------------|
| TSE — Dados Abertos | https://dadosabertos.tse.jus.br/ | Bulk CSV | Ground truth |
| TSE — DivulgaCandContas | https://divulgacandcontas.tse.jus.br/ | API REST | Ground truth |
| IBGE — Malhas Territoriais | https://ibge.gov.br/geociencias | Bulk GPKG | Ground truth |
| IBGE — Censo 2022 / SIDRA | http://api.sidra.ibge.gov.br | API REST | Ground truth |
| CadÚnico / CECAD | https://cecad.cidadania.gov.br/ | Painel | Proxy |

---

## Comandos úteis

```bash
make help           # Lista todos os comandos disponíveis
make logs           # Acompanha logs de todos os serviços
make shell-db       # psql no PostgreSQL
make migrate-create MSG="descrição"  # Nova migration
make test           # Roda testes
make reconcile      # Reconcilia totais de votos com TSE
```

---

## Governança de dados

Todo dado tem:
- URL de origem (`fonte_url`)
- Data de ingestão (`dataset_version`)
- Hash do arquivo bruto (`hash_arquivo`)
- Lineage do registro (`record_lineage`)
- Flag `e_ground_truth` para proxies

Toda tela analítica exibe o bloco `SourceMeta` com fonte, data de atualização, cobertura e limitações.

---

## Roadmap

- **Fase 1 (MVP)**: Busca, Ficha 360, Mapa, Finanças, Comparador, Exportações
- **Fase 2**: Gestão interna de usuários, watchlists e camadas socioeconômicas
- **Fase 3**: CRM político, lideranças, surveys
- **Fase 4**: IA assistida, monitoramento narrativo
