"""
Script de seed das fontes oficiais — popula tabela data_source.
Executar após migrations: make seed-sources
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.session import AsyncSessionLocal
from db.models.governance import DataSource


SOURCES = [
    {
        "nome": "TSE — Portal de Dados Abertos",
        "url": "https://dadosabertos.tse.jus.br/",
        "tipo": "BULK_CSV",
        "descricao": "Datasets eleitorais estruturados: resultados, candidaturas, bases por ano.",
        "classificacao": "ground_truth",
        "limitacoes": "Granularidade por seção disponível a partir de 2002.",
    },
    {
        "nome": "TSE — DivulgaCandContas",
        "url": "https://divulgacandcontas.tse.jus.br/",
        "tipo": "API_REST",
        "descricao": "Candidaturas, situação, contas eleitorais, receitas, despesas, fornecedores, doadores.",
        "classificacao": "ground_truth",
        "limitacoes": None,
    },
    {
        "nome": "TSE — Estatísticas do Eleitorado",
        "url": "https://sig.tse.jus.br/ords/dwapr/r/seai/sig-eleitor-eleitorado-mensal/home",
        "tipo": "PAINEL",
        "descricao": "Eleitorado mensal, perfil do eleitorado, proxy de população adulta eleitoral.",
        "classificacao": "ground_truth",
        "limitacoes": None,
    },
    {
        "nome": "IBGE — Malhas Territoriais",
        "url": "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html",
        "tipo": "BULK_SHP",
        "descricao": "Municípios, distritos, limites administrativos em GPKG/SHP.",
        "classificacao": "ground_truth",
        "limitacoes": None,
    },
    {
        "nome": "IBGE — Malha de Setores Censitários",
        "url": "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html",
        "tipo": "BULK_SHP",
        "descricao": "Setores censitários para cruzamento estatístico e territorial fino.",
        "classificacao": "ground_truth",
        "limitacoes": "Atualizado a cada Censo. Última versão: Censo 2022.",
    },
    {
        "nome": "IBGE — SIDRA / Censo 2022",
        "url": "http://api.sidra.ibge.gov.br",
        "tipo": "API_REST",
        "descricao": "População, domicílios, escolaridade, renda, composição domiciliar.",
        "classificacao": "ground_truth",
        "limitacoes": None,
    },
    {
        "nome": "CadÚnico / CECAD",
        "url": "https://cecad.cidadania.gov.br/",
        "tipo": "PAINEL",
        "descricao": "Vulnerabilidade social, famílias cadastradas, atualização cadastral.",
        "classificacao": "proxy",
        "limitacoes": "Proxy social — não representa população total. Cobertura variável por município.",
    },
    {
        "nome": "ANEEL — Dados Abertos",
        "url": "https://dadosabertos.aneel.gov.br/",
        "tipo": "API_REST",
        "descricao": "Unidades consumidoras — proxy de ocupação e expansão territorial.",
        "classificacao": "proxy",
        "limitacoes": "Proxy de ocupação, não de população.",
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        for data in SOURCES:
            existing = await session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(DataSource).where(
                    DataSource.nome == data["nome"]
                )
            )
            if existing.scalar_one_or_none():
                print(f"  → já existe: {data['nome']}")
                continue
            source = DataSource(**data)
            session.add(source)
            print(f"  ✅ inserido: {data['nome']}")
        await session.commit()
    print("\nSeed de fontes concluído.")


if __name__ == "__main__":
    asyncio.run(seed())
