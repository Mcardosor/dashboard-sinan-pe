"""Gera o arquivo de referências do harness de paridade.

Calcula os KPIs por um caminho **independente** da camada de dados: SQL cru,
escrito a partir das fórmulas do dashboard em R, sem importar ``src.data``.
Duas implementações independentes que concordam é um sinal muito mais forte
do que uma implementação comparada consigo mesma.

Limitação conhecida: estas referências saem dos parquets, não de uma execução
do dashboard em R — os pacotes de R não estão instalados nesta máquina. Isso
valida as fórmulas e pega regressões, mas não substitui conferir os números
contra a tela do original. Ver a pendência na semana 1 do cronograma.

Uso::

    python -m tests.paridade.gerar_referencias
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]
DASH = RAIZ / "data" / "parquet" / "dashboard"
SAIDA = Path(__file__).parent / "referencias.json"

#: (rótulo, nível, uf, mun6, ano)
CASOS = [
    ("BR/2024", "BR", None, None, 2024),
    ("BR/2020", "BR", None, None, 2020),
    ("BR/2015", "BR", None, None, 2015),
    ("PE/2024", "UF", "PE", None, 2024),
    ("PE/2023", "UF", "PE", None, 2023),
    ("PE/2020", "UF", "PE", None, 2020),
    ("PE/2015", "UF", "PE", None, 2015),
    ("SP/2024", "UF", "SP", None, 2024),
    ("AC/2024", "UF", "AC", None, 2024),
    ("Recife/2024", "MUN", "PE", "261160", 2024),
    ("Recife/2020", "MUN", "PE", "261160", 2020),
    ("Petrolina/2024", "MUN", "PE", "261110", 2024),
]

DOENCA = "TUBERCULOSE"


def _glob(dataset: str, *partes: str) -> str:
    return (DASH.joinpath(dataset, *partes) / "**" / "*.parquet").as_posix()


def _filtro(nivel: str, uf: str | None, mun6: str | None, col: str) -> tuple[str, list]:
    if nivel == "UF":
        return " WHERE uf = ?", [uf]
    if nivel == "MUN":
        return f" WHERE {col} = ?", [mun6]
    return "", []


def referencias_de(con, nivel, uf, mun6, ano) -> dict:
    onde7, p7 = _filtro(nivel, uf, mun6 and mun6 + "6", "cod_mun7")
    # incidence chaveia por cod_mun7; reconstruímos o 7º dígito pelo cod_mun6.
    if nivel == "MUN":
        onde7, p7 = " WHERE cod_mun6 = ?", [mun6]

    base = con.execute(
        f"SELECT casos_total, casos_cura, pop_total FROM read_parquet("
        f"'{_glob('incidence', f'doenca={DOENCA}', f'nivel={nivel}', f'ano={ano}')}',"
        f" hive_partitioning=true){onde7}",
        p7,
    ).fetchone()

    b14 = con.execute(
        f"SELECT casos_0_14_total, pop_0_14_total FROM read_parquet("
        f"'{_glob('incidence_0_14', f'doenca={DOENCA}', f'nivel={nivel}', f'ano={ano}')}',"
        f" hive_partitioning=true){onde7}",
        p7,
    ).fetchone()

    ondeg, pg = _filtro(nivel, uf, mun6, "geo_id")
    obitos = con.execute(
        f"SELECT sum(casos_obitos) FROM read_parquet("
        f"'{_glob('cache_ts_sim_obitos', f'nivel={nivel}', f'doenca={DOENCA}', f'ano={ano}')}',"
        f" hive_partitioning=true){ondeg}",
        pg,
    ).fetchone()[0]

    landing = _glob("sinan_landing", f"doenca={DOENCA}", f"nivel={nivel}", f"ano={ano}")
    ondel = ondeg.replace(" WHERE ", " AND ") if ondeg else ""

    hiv = con.execute(
        f"""
        WITH b AS (
          SELECT lower(strip_accents(any_value(valor_lbl))) lbl, sum(n) n
          FROM read_parquet('{landing}', hive_partitioning=true)
          WHERE variavel = 'HIV'{ondel} GROUP BY trim(valor)
        )
        SELECT 100.0 * sum(CASE WHEN lbl LIKE '%positiv%' THEN n END)
               / nullif(sum(CASE WHEN lbl LIKE '%positiv%' OR lbl LIKE '%negativ%'
                                 THEN n END), 0)
        FROM b
        """,
        pg,
    ).fetchone()[0]

    enc = con.execute(
        f"""
        SELECT trim(valor) v, sum(n) n
        FROM read_parquet('{landing}', hive_partitioning=true)
        WHERE variavel = 'SITUA_ENCE'{ondel} GROUP BY 1
        """,
        pg,
    ).fetchdf()

    def pct(codigos, excluir):
        if enc.empty:
            return None
        num = float(enc.loc[enc["v"].isin(codigos), "n"].sum())
        den = float(enc.loc[~enc["v"].isin(excluir), "n"].sum())
        return None if den <= 0 else 100.0 * num / den

    casos, cura, pop = (base or (None, None, None))
    c14, p14 = (b14 or (None, None))

    def taxa(n, d, fator):
        if n is None or d in (None, 0):
            return None
        return float(n) / float(d) * fator

    return {
        "casos": casos and float(casos),
        "obitos": obitos and float(obitos),
        "cura": cura and float(cura),
        "pop": pop and float(pop),
        "incid": taxa(casos, pop, 1e5),
        "mortalidade": taxa(obitos, pop, 1e5),
        "letalidade": taxa(obitos, casos, 100),
        "casos_0_14": c14 and float(c14),
        "taxa_det_0_14": taxa(c14, p14, 1e5),
        "hiv_pos_pct": hiv and float(hiv),
        "interrupcao_trat_pct": pct({"2"}, set()),
        "interrupcao_trat_pct_ms": pct({"2", "10"}, {"0", "5", "7", "8"}),
    }


def main() -> None:
    con = duckdb.connect()
    saida = {}
    for rotulo, nivel, uf, mun6, ano in CASOS:
        saida[rotulo] = {
            "escopo": {"doenca": DOENCA, "ano": ano, "nivel": nivel, "uf": uf, "mun6": mun6},
            "kpis": referencias_de(con, nivel, uf, mun6, ano),
        }
        print(f"  {rotulo:18s} ok")
    SAIDA.write_text(json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(saida)} recortes -> {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
