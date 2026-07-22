"""Importa votação oficial TSE 2022 de Rondônia para uso local sem Docker.

Entrada: data/raw/votacao_secao_2022_RO.zip (arquivo oficial do TSE)
Saída: data/staging/tse_2022_ro_governador.json (ignorado pelo Git)
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/votacao_secao_2022_RO.zip"
OUT = ROOT / "data/staging/tse_2022_ro_governador.json"
TSE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_RO.zip"
IBGE_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/estados/11?" + urllib.parse.urlencode({"formato": "application/vnd.geo+json", "qualidade": "minima", "intrarregiao": "municipio"})
IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/11/municipios"


def normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.upper()) if unicodedata.category(char) != "Mn")


def load_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return json.loads(payload)


def main() -> int:
    if not RAW.exists():
        print("Baixando arquivo oficial do TSE — RO 2022...")
        RAW.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(TSE_URL, RAW)

    votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    candidate_names: dict[str, str] = {}
    municipality_names: dict[str, str] = {}

    with zipfile.ZipFile(RAW) as archive:
        csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
        with archive.open(csv_name) as raw_file:
            rows = csv.DictReader(io.TextIOWrapper(raw_file, encoding="latin-1"), delimiter=";")
            for row in rows:
                if row["DS_CARGO"] != "Governador" or row["NR_TURNO"] != "1":
                    continue
                candidate = row["NR_VOTAVEL"]
                municipality = row["CD_MUNICIPIO"]
                votes[municipality][candidate] += int(row["QT_VOTOS"] or 0)
                candidate_names[candidate] = row["NM_VOTAVEL"].title()
                municipality_names[municipality] = row["NM_MUNICIPIO"].title()

    geometries = load_json(IBGE_URL)
    municipalities_ibge = load_json(IBGE_MUNICIPIOS_URL)
    ibge_names = {normalized(item["nome"]): str(item["id"]) for item in municipalities_ibge}
    ibge_by_code = {str(item["id"]): item["nome"] for item in municipalities_ibge}

    votes_by_ibge = {ibge_names[normalized(name)]: municipality_votes for tse_code, municipality_votes in votes.items() if (name := municipality_names[tse_code]) and normalized(name) in ibge_names}

    features = []
    for feature in geometries["features"]:
        code = feature.get("properties", {}).get("codarea")
        if code not in votes_by_ibge:
            continue
        feature["properties"] = {
            "codigo_ibge": code,
            "nome": ibge_by_code[code],
            "votos": dict(votes_by_ibge[code]),
            "total": sum(votes_by_ibge[code].values()),
        }
        features.append(feature)

    totals: dict[str, int] = defaultdict(int)
    for municipality_votes in votes.values():
        for candidate, value in municipality_votes.items():
            totals[candidate] += value
    candidates = [{"id": candidate, "nome": candidate_names[candidate], "votos": value} for candidate, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "meta": {"fonte": "TSE — Resultados 2022", "url": "https://dadosabertos.tse.jus.br/dataset/resultados-2022", "cargo": "Governador", "turno": 1, "uf": "RO"},
        "candidates": candidates,
        "mapa": {"type": "FeatureCollection", "features": features},
    }, ensure_ascii=False), encoding="utf-8")
    print(f"Importados {len(features)} municípios e {len(candidates)} candidaturas: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
