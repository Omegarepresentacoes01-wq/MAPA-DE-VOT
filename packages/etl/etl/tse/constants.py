"""
Constantes e mapeamentos para os datasets do TSE.

Documentação das colunas dos arquivos de candidatura:
https://dadosabertos.tse.jus.br/dataset/candidatos-{ano}
"""
from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# URLs dos datasets TSE
# ──────────────────────────────────────────────────────────────────────────────

# Candidaturas (ZIP com CSVs por UF)
TSE_CANDIDATURES_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
    "consulta_cand_{ano}.zip"
)

# Resultados por município e zona
TSE_RESULTS_MUNZONA_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/"
    "votacao_candidato_munzona_{ano}.zip"
)

# Bens declarados
TSE_ASSETS_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/"
    "bem_candidato_{ano}.zip"
)

# Receitas
TSE_REVENUES_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/receitas_candidatos/"
    "receitas_candidatos_{ano}.zip"
)

# Despesas
TSE_EXPENSES_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/despesas_candidatos/"
    "despesas_candidatos_{ano}.zip"
)

# ──────────────────────────────────────────────────────────────────────────────
# Configurações de arquivo
# ──────────────────────────────────────────────────────────────────────────────

TSE_ENCODING = "latin-1"          # ISO-8859-1
TSE_SEPARATOR = ";"
TSE_QUOTE_CHAR = '"'

# ──────────────────────────────────────────────────────────────────────────────
# Colunas dos arquivos de candidatura (consulta_cand)
# Mapeamento: nome_coluna_tse → nome_interno
# ──────────────────────────────────────────────────────────────────────────────

CAND_COLUMNS = {
    "ANO_ELEICAO":         "ano_eleicao",
    "CD_TIPO_ELEICAO":     "cd_tipo_eleicao",
    "NM_TIPO_ELEICAO":     "nm_tipo_eleicao",
    "NR_TURNO":            "turno",
    "SG_UF":               "uf",
    "CD_MUNICIPIO":        "cd_municipio_tse",
    "NM_MUNICIPIO":        "nm_municipio",
    "NR_ZONA":             "nr_zona",
    "CD_CARGO":            "cd_cargo",
    "DS_CARGO":            "ds_cargo",
    "SQ_CANDIDATO":        "sq_candidato",
    "NR_CANDIDATO":        "numero_urna",
    "NM_CANDIDATO":        "nome",
    "NM_URNA_CANDIDATO":   "nome_urna",
    "NM_SOCIAL_CANDIDATO": "nome_social",
    "NR_CPF_CANDIDATO":    "cpf_raw",          # será hasheado, nunca persistido em claro
    "DT_NASCIMENTO":       "nascimento",
    "NR_IDADE_DATA_POSSE": "idade_posse",
    "DS_GENERO":           "genero",
    "DS_GRAU_INSTRUCAO":   "escolaridade",
    "DS_ESTADO_CIVIL":     "estado_civil",
    "DS_COR_RACA":         "raca_cor",
    "DS_OCUPACAO":         "ocupacao",
    "NR_PARTIDO":          "numero_partido",
    "SG_PARTIDO":          "sigla_partido",
    "NM_PARTIDO":          "nome_partido",
    "DS_COMPOSICAO_COLIGACAO": "coligacao",
    "CD_SIT_TOT_TURNO":    "cd_situacao",
    "DS_SIT_TOT_TURNO":    "situacao",
    "ST_REELEICAO":        "reeleicao",
    "ST_DECLARAR_BENS":    "declarou_bens",
}

# Situações finais consideradas "eleito"
SITUACOES_ELEITO = {
    "ELEITO",
    "ELEITO POR QP",
    "ELEITO POR MÉDIA",
    "ELEITO COM VOTOS",
}

# Nível do cargo
CARGO_NIVEL = {
    "1":  "federal",   # Presidente
    "2":  "federal",   # Vice-Presidente
    "3":  "federal",   # Governador
    "4":  "federal",   # Vice-Governador
    "5":  "federal",   # Senador
    "6":  "federal",   # Deputado Federal
    "7":  "estadual",  # Deputado Estadual
    "8":  "estadual",  # Deputado Distrital
    "9":  "estadual",  # Prefeito
    "10": "estadual",  # Vice-Prefeito
    "11": "municipal", # Vereador
    "12": "federal",   # Presidente (2o turno)
    "13": "federal",   # Governador (2o turno)
}

# ──────────────────────────────────────────────────────────────────────────────
# Colunas dos arquivos de resultados (votacao_candidato_munzona)
# ──────────────────────────────────────────────────────────────────────────────

RESULT_COLUMNS = {
    "ANO_ELEICAO":          "ano_eleicao",
    "NR_TURNO":             "turno",
    "SG_UF":                "uf",
    "CD_MUNICIPIO":         "cd_municipio_tse",
    "NM_MUNICIPIO":         "nm_municipio",
    "NR_ZONA":              "nr_zona",
    "CD_CARGO":             "cd_cargo",
    "SQ_CANDIDATO":         "sq_candidato",
    "QT_VOTOS_NOMINAIS":    "votos",
    "QT_VOTOS_NOMINAIS_VALIDOS": "votos_validos",
    "CD_SIT_TOT_TURNO":     "cd_situacao",
}

# ──────────────────────────────────────────────────────────────────────────────
# Colunas dos arquivos de bens (bem_candidato)
# ──────────────────────────────────────────────────────────────────────────────

ASSET_COLUMNS = {
    "ANO_ELEICAO":        "ano_eleicao",
    "SQ_CANDIDATO":       "sq_candidato",
    "SQ_BEM_CANDIDATO":   "sq_bem",
    "DS_TIPO_BEM_CANDIDATO": "tipo",
    "DS_BEM_CANDIDATO":   "descricao",
    "VR_BEM_CANDIDATO":   "valor",
}

# ──────────────────────────────────────────────────────────────────────────────
# UFs do Brasil (para iteração por arquivo)
# ──────────────────────────────────────────────────────────────────────────────

UFS = [
    "AC", "AL", "AM", "AP", "BA", "BR",  # BR = nacional (cargos federais)
    "CE", "DF", "ES", "GO", "MA", "MG",
    "MS", "MT", "PA", "PB", "PE", "PI",
    "PR", "RJ", "RN", "RO", "RR", "RS",
    "SC", "SE", "SP", "TO",
]
