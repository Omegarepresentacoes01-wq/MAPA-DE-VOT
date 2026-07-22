"""
Constantes e URLs para os datasets IBGE.

Fontes:
  - Malhas municipais (GeoFTP): geoftp.ibge.gov.br
  - API de localidades: servicodados.ibge.gov.br/api/v1/localidades
  - SIDRA (Censo 2022): servicodados.ibge.gov.br/api/v3/agregados
  - Setores censitários: geoftp.ibge.gov.br
"""
from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Malhas municipais (Shapefile/GPKG)
# ──────────────────────────────────────────────────────────────────────────────

IBGE_MUNICIPIOS_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/{ano}/Brasil/BR/"
    "BR_Municipios_{ano}.zip"
)

IBGE_MUNICIPIOS_URL_2022 = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/2022/Brasil/BR/"
    "BR_Municipios_2022.zip"
)

# Malha de estados (UFs)
IBGE_ESTADOS_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_de_unidades_da_federacao/2022/Brasil/BR/"
    "BR_UF_2022.zip"
)

# Setores censitários (grande — ~500 MB)
IBGE_SETORES_URL = (
    "https://geoftp.ibge.gov.br/recortes_para_fins_estatisticos/"
    "malha_de_setores_censitarios/censo_2022/base/BR/"
    "BR_Malha_Preliminar_2022.zip"
)

# ──────────────────────────────────────────────────────────────────────────────
# API de Localidades (mapeamento código IBGE → nome, UF)
# ──────────────────────────────────────────────────────────────────────────────

IBGE_LOCALIDADES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

# ──────────────────────────────────────────────────────────────────────────────
# API SIDRA — Censo 2022
# ──────────────────────────────────────────────────────────────────────────────

SIDRA_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Tabela 4714 — Pessoas por sexo e grupos de idade (Censo 2022)
# Variável 93 = total de pessoas
SIDRA_POPULACAO_URL = f"{SIDRA_BASE}/4714/periodos/2022/variaveis/93?localidades=N6[all]"

# Tabela 6579 — Pessoas por cor ou raça
SIDRA_COR_RACA_URL = f"{SIDRA_BASE}/6579/periodos/2022/variaveis/606?localidades=N6[all]"

# Tabela 4709 — Domicílios particulares permanentes
SIDRA_DOMICILIOS_URL = f"{SIDRA_BASE}/4709/periodos/2022/variaveis/188?localidades=N6[all]"

# Tabela 7358 — Rendimento médio mensal domiciliar per capita
SIDRA_RENDA_URL = f"{SIDRA_BASE}/7358/periodos/2010/variaveis/5938?localidades=N6[all]"

# ──────────────────────────────────────────────────────────────────────────────
# Mapeamento de colunas do Shapefile de municípios IBGE 2022
# ──────────────────────────────────────────────────────────────────────────────

MUNICIPIOS_SHP_COLUMNS = {
    "CD_MUN":    "codigo_ibge",   # 7 dígitos (ex: 3550308)
    "NM_MUN":    "nome",
    "SIGLA_UF":  "uf",
    "AREA_KM2":  "area_km2",
    # geometry → geom (PostGIS)
}

# Colunas do Shapefile de UFs
ESTADOS_SHP_COLUMNS = {
    "CD_UF":     "codigo_uf",
    "NM_UF":     "nome",
    "SIGLA":     "uf",
    "NM_REGIAO": "regiao",
}

# ──────────────────────────────────────────────────────────────────────────────
# Mapeamento TSE-codigo → IBGE-7digitos
# O código TSE tem 5 dígitos; o IBGE tem 7 (inclui UF + dígito verificador).
# O arquivo de mapeamento oficial está disponível na API de localidades do IBGE.
# ──────────────────────────────────────────────────────────────────────────────

# Prefixo IBGE por UF (2 dígitos)
IBGE_UF_PREFIX = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15",
    "AP": "16", "TO": "17", "MA": "21", "PI": "22", "CE": "23",
    "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28",
    "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
    "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51",
    "GO": "52", "DF": "53",
}

# CRS padrão para armazenamento no PostGIS
POSTGIS_SRID = 4326  # WGS84
