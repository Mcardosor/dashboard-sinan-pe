"""Consistência estrutural dos dados.

Estes testes não comparam a implementação com uma referência — eles checam
invariantes que os próprios dados deveriam respeitar. É a classe de erro que o
harness de paridade não pega: se a camada de dados e o gerador de referências
partirem da mesma premissa errada, os dois concordam e os dois erram.
"""

from __future__ import annotations

import duckdb
import pytest

from src.data.conexao import caminho

DOENCA = "TUBERCULOSE"
ANOS = range(2010, 2025)


@pytest.fixture(scope="module")
def con():
    return duckdb.connect()


def _soma(con, fonte: str, coluna: str, onde: str = "") -> float:
    sql = f"SELECT sum({coluna}) FROM read_parquet('{fonte}', hive_partitioning=true)"
    if onde:
        sql += f" WHERE {onde}"
    return con.execute(sql).fetchone()[0]


@pytest.mark.parametrize("nivel,chave", [("BR", "1"), ("UF", "uf"), ("MUN", "cod_mun6")])
def test_incidence_tem_uma_linha_por_geografia(con, nivel, chave) -> None:
    """Sem isso, ler ``.iloc[0]`` silenciosamente descartaria linhas."""
    fonte = caminho("incidence", doenca=DOENCA, nivel=nivel, ano=2024)
    linhas, chaves = con.execute(
        f"SELECT count(*), count(DISTINCT {chave}) "
        f"FROM read_parquet('{fonte}', hive_partitioning=true)"
    ).fetchone()
    assert linhas == chaves, f"{nivel}: {linhas} linhas para {chaves} geografias"


@pytest.mark.parametrize("ano", ANOS)
def test_soma_dos_municipios_bate_com_a_uf(con, ano) -> None:
    mun = caminho("incidence", doenca=DOENCA, nivel="MUN", ano=ano)
    uf = caminho("incidence", doenca=DOENCA, nivel="UF", ano=ano)
    divergentes = con.execute(f"""
        WITH m AS (SELECT uf, sum(casos_total) c
                   FROM read_parquet('{mun}', hive_partitioning=true) GROUP BY 1),
             u AS (SELECT uf, casos_total c
                   FROM read_parquet('{uf}', hive_partitioning=true))
        SELECT count(*) FROM m JOIN u USING (uf) WHERE m.c <> u.c
    """).fetchone()[0]
    assert divergentes == 0, f"{ano}: {divergentes} UFs não fecham com seus municípios"


@pytest.mark.parametrize("ano", ANOS)
def test_soma_das_ufs_bate_com_o_brasil(con, ano) -> None:
    uf = caminho("incidence", doenca=DOENCA, nivel="UF", ano=ano)
    br = caminho("incidence", doenca=DOENCA, nivel="BR", ano=ano)
    assert _soma(con, uf, "casos_total") == _soma(con, br, "casos_total")
    assert _soma(con, uf, "pop_total") == _soma(con, br, "pop_total")


@pytest.mark.parametrize("nivel", ["BR", "UF", "MUN"])
def test_obitos_do_sim_fecham_entre_niveis(con, nivel) -> None:
    fonte = caminho("cache_ts_sim_obitos", nivel=nivel, doenca=DOENCA, ano=2024)
    assert _soma(con, fonte, "casos_obitos") == 6376


# ---------------------------------------------------------------------------
# Divergência conhecida: série mensal x total anual
# ---------------------------------------------------------------------------
# `incidence` e `_cache_ts` atribuem o caso a UFs diferentes. Nacionalmente as
# diferenças se cancelam (pior ano: 0,0086%), mas por UF o desvio é grande:
#
#     DF        7,7% (2024) a 36,8% (2011) — o pior em todos os 15 anos
#     ex-DF     4,5% a 13,9%, concentrado em PI, TO e AP
#
# O padrão — DF ganhando enquanto GO e TO perdem — é compatível com UF de
# residência num dataset e UF de notificação no outro. A tendência de queda ao
# longo dos anos acompanha a melhora do preenchimento no SINAN.
#
# Consequência prática: no nível UF, o card de KPI e o gráfico de série
# temporal mostram totais diferentes para o mesmo recorte. Em DF/2011 a
# diferença é de mais de um terço. O dashboard em R tem exatamente a mesma
# inconsistência, porque lê KPI de `incidence` e série de `_cache_ts` como
# aqui — é problema de pipeline, a montante. Levar à equipe de R.
#
# Estes testes não mascaram o defeito: fixam o tamanho dele. Se crescer, algo
# mudou e precisa ser reavaliado.

#: Desvio máximo numa UF que não seja o DF. Medido: 13,87% (PI, 2010).
LIMITE_UF = 0.15

#: O DF é caso à parte e precisa de folga própria. Medido: 36,83% (2011).
LIMITE_DF = 0.40

#: Nacional, onde a realocação se cancela. Medido: 0,0086% (2016).
LIMITE_BR = 0.0001


@pytest.mark.parametrize("ano", ANOS)
def test_divergencia_mensal_anual_esta_contida(con, ano) -> None:
    uf = caminho("incidence", doenca=DOENCA, nivel="UF", ano=ano)
    ts = caminho("_cache_ts", nivel="UF", doenca=DOENCA, ano=ano)

    desvios = f"""
        WITH a AS (SELECT uf, casos_total c
                   FROM read_parquet('{uf}', hive_partitioning=true)),
             m AS (SELECT uf, sum(casos) c
                   FROM read_parquet('{ts}', hive_partitioning=true) GROUP BY 1)
        SELECT uf, abs(m.c - a.c) / nullif(a.c, 0) d FROM a JOIN m USING (uf)
    """

    pior_uf, desvio = con.execute(
        f"SELECT uf, d FROM ({desvios}) WHERE uf <> 'DF' ORDER BY d DESC LIMIT 1"
    ).fetchone()
    assert desvio <= LIMITE_UF, (
        f"{ano}: {pior_uf} desviou {desvio:.2%}, acima do limite de {LIMITE_UF:.0%}"
    )

    desvio_df = con.execute(
        f"SELECT d FROM ({desvios}) WHERE uf = 'DF'"
    ).fetchone()[0]
    assert desvio_df <= LIMITE_DF, (
        f"{ano}: DF desviou {desvio_df:.2%}, acima do limite de {LIMITE_DF:.0%}"
    )

    anual = _soma(con, uf, "casos_total")
    mensal = _soma(con, ts, "casos")
    relativo = abs(mensal - anual) / anual
    assert relativo <= LIMITE_BR, (
        f"{ano}: nacional divergiu {relativo:.3%} (anual={anual}, mensal={mensal})"
    )


def test_serie_mensal_cobre_doze_meses(con) -> None:
    ts = caminho("_cache_ts", nivel="UF", doenca=DOENCA, ano=2024)
    meses = con.execute(
        f"SELECT count(DISTINCT mes) FROM read_parquet('{ts}', hive_partitioning=true)"
        f" WHERE uf = 'PE'"
    ).fetchone()[0]
    assert meses == 12


# ---------------------------------------------------------------------------
# Conciliação entre fontes do mesmo indicador
# ---------------------------------------------------------------------------
# Quatro datasets respondem "quantos casos", em três camadas:
#
#   1. incidence ~ cases_new        divergem em 3 das 27 UFs, no máximo
#                                   0,098%. DF/2024 = 440
#   2. _cache_ts                    atribuição geográfica diferente da camada 1.
#                                   DF/2024 = 474 (+7,7%) — ver armadilha 7
#   3. piramides                    igual a _cache_ts, menos os registros sem
#                                   sexo ou faixa etária, que não cabem numa
#                                   pirâmide. Perde em 4 das 27 UFs, no máximo
#                                   0,13% (SP: -26 casos)
#
# A coluna geográfica dos indicadores de TB se chama CO_MUNI_RESIDENCIA, o que
# sugere que a camada 1 é por residência — mas precisa ser confirmado com a
# equipe de R antes de virar decisão.

#: Perda máxima aceitável de `piramides` contra `_cache_ts`. Medido: 0,13% (SP).
LIMITE_PIRAMIDE = 0.002

#: Divergência máxima entre `incidence` e `cases_new`. Medido: 0,098% (GO).
LIMITE_CAMADA_1 = 0.002


def _casos_por_fonte(esc):
    from src.data import leitura

    return {
        "incidence": float(leitura.incidencia(esc)["casos_total"]),
        "cases_new": float(leitura.casos_novos(esc)),
        "_cache_ts": float(leitura.serie_mensal(esc)["casos"].sum()),
        "piramides": float(leitura.piramide(esc, "CASOS")["valor"].sum()),
    }


@pytest.mark.parametrize("uf", ["PE", "SP", "DF", "AC", "TO", "RJ"])
def test_incidence_e_cases_new_praticamente_batem(uf) -> None:
    """Nenhuma fonte é exatamente igual a outra; aqui a diferença é residual."""
    from src.data.escopo import Escopo

    fontes = _casos_por_fonte(Escopo("TUBERCULOSE", 2024, "UF", uf=uf))
    a, b = fontes["incidence"], fontes["cases_new"]
    assert abs(b - a) / a <= LIMITE_CAMADA_1, (
        f"{uf}: incidence={a:.0f} cases_new={b:.0f}"
    )


@pytest.mark.parametrize("uf", ["PE", "SP", "DF", "AC", "TO", "RJ"])
def test_piramide_perde_pouco_contra_a_serie(uf) -> None:
    """A pirâmide descarta registros sem sexo ou faixa; a perda tem que ser pequena."""
    from src.data.escopo import Escopo

    fontes = _casos_por_fonte(Escopo("TUBERCULOSE", 2024, "UF", uf=uf))
    serie, piramide = fontes["_cache_ts"], fontes["piramides"]
    assert piramide <= serie, f"{uf}: pirâmide ({piramide}) acima da série ({serie})"
    perda = (serie - piramide) / serie
    assert perda <= LIMITE_PIRAMIDE, f"{uf}: pirâmide perdeu {perda:.2%}"


def test_divergencia_entre_camadas_permanece_conhecida() -> None:
    """Fixa o caso extremo. Se mudar, a armadilha 7 precisa ser reavaliada."""
    from src.data.escopo import Escopo

    fontes = _casos_por_fonte(Escopo("TUBERCULOSE", 2024, "UF", uf="DF"))
    assert fontes["incidence"] == 440
    assert fontes["_cache_ts"] == 474


# ---------------------------------------------------------------------------
# piramides: CURA e OBITOS vazios para tuberculose
# ---------------------------------------------------------------------------
# O dataset `piramides` tem a partição `tipo` com CASOS, CURA e OBITOS, mas
# para tuberculose só CASOS tem dado — CURA e OBITOS somam zero em todos os
# 15 anos e nos três níveis. Só a dengue tem OBITOS preenchido.
#
# Consequência: a alternância CASOS/CURA/ÓBITOS da pirâmide etária não funciona
# na entrega de TB. A pirâmide de óbitos precisa sair de `obitos_sim_faixa`,
# que tem o dado (6.354 óbitos no BR em 2024).


@pytest.mark.parametrize("tipo", ["CURA", "OBITOS"])
def test_piramide_de_tb_esta_vazia_fora_de_casos(con, tipo) -> None:
    fonte = caminho("piramides", nivel="UF", tipo=tipo, doenca=DOENCA, ano=2024)
    assert _soma(con, fonte, "valor") == 0


def test_piramide_de_casos_tem_dado(con) -> None:
    fonte = caminho("piramides", nivel="UF", tipo="CASOS", doenca=DOENCA, ano=2024)
    assert _soma(con, fonte, "valor") > 0


def test_obitos_por_faixa_supre_a_piramide_de_obitos() -> None:
    """A alternativa precisa ter dado, senão a pirâmide de óbitos é inviável."""
    from src.data import leitura
    from src.data.escopo import Escopo

    df = leitura.obitos_por_faixa(Escopo("TUBERCULOSE", 2024, "BR"))
    assert not df.empty
    assert df["obitos"].sum() > 0
