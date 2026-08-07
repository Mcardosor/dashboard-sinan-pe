"""Leitores por dataset.

Cada função recebe um ``Escopo`` e devolve dados já normalizados: doença
traduzida para o código do dataset, ``valor`` sem o espaço à esquerda e
código de município no comprimento que cada dataset espera.

Sobre o município: o ``Escopo`` normaliza tudo para o código de 6 dígitos,
que é a chave presente em todos os datasets — ``cod_mun6`` em ``incidence`` e
``geo_id`` nos demais. Cruzar com o ``cod_mun7`` não dá erro, devolve vazio.
Ver docs/contrato-dados.md.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .conexao import caminho, conectar
from .escopo import Escopo, mun6


def _uma_linha(sql: str, params: list) -> dict:
    df = conectar().execute(sql, params).fetchdf()
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def incidencia(esc: Escopo) -> dict:
    """Linha de ``incidence`` para o recorte: casos, cura, população, incidência.

    Atenção: ``casos_obitos`` deste dataset é zero para tuberculose em todos os
    anos. Use :func:`obitos_sim`. Ver docs/contrato-dados.md, armadilha 1.
    """
    fonte = caminho(
        "incidence",
        doenca=config.cod_agregado(esc.doenca),
        nivel=esc.nivel,
        ano=esc.ano,
    )
    onde, params = esc.filtro_geo()
    sql = f"""
        SELECT casos_total, casos_M, casos_F,
               casos_cura, cura_M, cura_F,
               pop_total, pop_M, pop_F,
               incid_100k_total, incid_100k_M, incid_100k_F
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return _uma_linha(sql, params)


def incidencia_0_14(esc: Escopo) -> dict:
    """Linha de ``incidence_0_14``: casos, população e incidência na faixa 0–14."""
    fonte = caminho(
        "incidence_0_14",
        doenca=config.cod_agregado(esc.doenca),
        nivel=esc.nivel,
        ano=esc.ano,
    )
    onde, params = esc.filtro_geo()
    sql = f"""
        SELECT casos_0_14_total, casos_0_14_M, casos_0_14_F, casos_0_14_cura,
               pop_0_14_total, incid_0_14_100k_total
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return _uma_linha(sql, params)


def obitos_sim(esc: Escopo) -> float | None:
    """Óbitos do SIM no recorte — a fonte real de mortalidade."""
    fonte = caminho(
        "cache_ts_sim_obitos",
        nivel=esc.nivel,
        doenca=config.cod_sim(esc.doenca),
        ano=esc.ano,
    )
    sql = f"SELECT sum(casos_obitos) FROM read_parquet('{fonte}', hive_partitioning=true)"
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE uf = ?"
        params.append(esc.uf)
    elif esc.nivel == "MUN":
        sql += " WHERE geo_id = ?"
        params.append(mun6(esc.mun))
    linha = conectar().execute(sql, params).fetchone()
    return None if linha is None else linha[0]


def serie_mensal(esc: Escopo) -> pd.DataFrame:
    """Série mensal de ``_cache_ts`` para o ano do escopo."""
    fonte = caminho(
        "_cache_ts",
        nivel=esc.nivel,
        doenca=config.cod_agregado(esc.doenca),
        ano=esc.ano,
    )
    sql = f"""
        SELECT mes, mes_nome, casos, casos_obitos, casos_cura, pop_total, incid_100k
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE uf = ?"
        params.append(esc.uf)
    elif esc.nivel == "MUN":
        sql += " WHERE geo_id = ?"
        params.append(mun6(esc.mun))
    return conectar().execute(sql + " ORDER BY mes", params).fetchdf()


def variavel_sinan(esc: Escopo, variavel: str) -> pd.DataFrame:
    """Distribuição de uma variável do SINAN no recorte.

    O ``valor`` bruto vem com espaço à esquerda (``" 2"``, não ``"2"``). Aqui ele
    sai já com ``trim`` aplicado — sem isso, todo filtro por código falha em
    silêncio. Ver docs/contrato-dados.md, armadilha 3.
    """
    fonte = caminho(
        "sinan_landing",
        doenca=config.cod_landing(esc.doenca),
        nivel=esc.nivel,
        ano=esc.ano,
    )
    sql = f"""
        SELECT trim(valor) AS valor, any_value(valor_lbl) AS valor_lbl, sum(n) AS n
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE variavel = ?
    """
    params: list = [variavel]
    if esc.nivel == "UF":
        sql += " AND uf = ?"
        params.append(esc.uf)
    elif esc.nivel == "MUN":
        sql += " AND geo_id = ?"
        params.append(mun6(esc.mun))
    sql += " GROUP BY 1 ORDER BY n DESC"
    return conectar().execute(sql, params).fetchdf()


def anos_disponiveis(doenca: str) -> list[int]:
    """Anos com dado em ``incidence``, para o slider dar *snap*."""
    fonte = caminho("incidence", doenca=config.cod_agregado(doenca), nivel="BR")
    sql = f"""
        SELECT DISTINCT ano FROM read_parquet('{fonte}', hive_partitioning=true)
        ORDER BY ano
    """
    return [int(a) for a in conectar().execute(sql).fetchdf()["ano"]]


def piramide(esc: Escopo, tipo: str = "CASOS") -> pd.DataFrame:
    """Pirâmide etária: evento e população por sexo e faixa.

    ``tipo`` é ``CASOS``, ``CURA`` ou ``OBITOS``.
    """
    tipo = str(tipo or "CASOS").strip().upper()
    if tipo not in ("CASOS", "CURA", "OBITOS"):
        raise ValueError(f"Tipo inválido: {tipo!r}. Esperado CASOS, CURA ou OBITOS.")

    fonte = caminho(
        "piramides",
        nivel=esc.nivel,
        tipo=tipo,
        doenca=config.cod_agregado(esc.doenca),
        ano=esc.ano,
    )
    sql = f"""
        SELECT sexo, faixa_ord, faixa_etaria, valor, pop, ratio
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE uf = ?"
        params.append(esc.uf)
    elif esc.nivel == "MUN":
        sql += " WHERE geo_id = ?"
        params.append(mun6(esc.mun))
    return conectar().execute(sql + " ORDER BY faixa_ord, sexo", params).fetchdf()


def casos_novos(esc: Escopo) -> float | None:
    """Casos novos do recorte.

    ``cases_new`` só traz ``cod_mun6`` — a UF é derivada dos dois primeiros
    dígitos, porque o dataset não tem coluna de UF.
    """
    fonte = caminho("cases_new", doenca=config.cod_agregado(esc.doenca), ano=esc.ano)
    sql = f"SELECT sum(casos_novos) FROM read_parquet('{fonte}', hive_partitioning=true)"
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE cod_mun6 LIKE ?"
        params.append(config.codigo_uf(esc.uf) + "%")
    elif esc.nivel == "MUN":
        sql += " WHERE cod_mun6 = ?"
        params.append(mun6(esc.mun))
    linha = conectar().execute(sql, params).fetchone()
    return None if linha is None else linha[0]


def obitos_por_faixa(esc: Escopo) -> pd.DataFrame:
    """Óbitos do SIM por sexo e faixa etária.

    Este dataset só existe no nível MUN — não há partições de UF nem de BR.
    A agregação para os níveis acima é feita aqui, filtrando por ``cod_uf``.
    """
    fonte = caminho(
        "obitos_sim_faixa",
        doenca=config.cod_sim(esc.doenca),
        nivel="MUN",
        ano=esc.ano,
    )
    sql = f"""
        SELECT sexo, faixa_ord, faixa_etaria, sum(obitos_sim) AS obitos
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE cod_uf = ?"
        params.append(config.codigo_uf(esc.uf))
    elif esc.nivel == "MUN":
        sql += " WHERE cod_mun = ?"
        params.append(esc.mun)
    sql += " GROUP BY 1, 2, 3 ORDER BY faixa_ord, sexo"
    return conectar().execute(sql, params).fetchdf()


def dicionario(doenca: str, variavel: str | None = None) -> pd.DataFrame:
    """Dicionário de código → rótulo das variáveis do SINAN.

    O ``valor`` sai com ``trim`` aplicado. Cuidado: o dicionário registra
    ``" 3"`` e ``"03"`` como entradas distintas para o mesmo código, então o
    resultado pode trazer duplicatas legítimas do dado de origem.
    """
    fonte = caminho("sinan_dict", doenca=config.cod_landing(doenca))
    sql = f"""
        SELECT variavel, trim(valor) AS valor, valor_lbl, n_total, n_years
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = []
    if variavel:
        sql += " WHERE variavel = ?"
        params.append(variavel)
    return conectar().execute(sql + " ORDER BY variavel, valor", params).fetchdf()


def _indicador_tb(dataset: str, esc: Escopo, colunas: str) -> dict:
    """Base dos indicadores de TB, que têm dois arquivos de esquemas diferentes.

    ``por_ano.parquet`` é nacional; ``por_ano_geo.parquet`` tem o município.
    A coluna geográfica é ``CO_MUNI_RESIDENCIA`` — **residência**, não
    notificação. O código ``0`` marca município ignorado e é descartado nos
    recortes de UF e município, mas continua no total nacional.
    """
    if esc.doenca != "TUBERCULOSE":
        return {}

    nacional = esc.nivel == "BR"
    fonte = caminho(
        dataset, arquivo="por_ano.parquet" if nacional else "por_ano_geo.parquet"
    )
    sql = f"SELECT {colunas} FROM read_parquet('{fonte}') WHERE NU_ANO = ?"
    params: list = [str(esc.ano)]

    if esc.nivel == "UF":
        sql += " AND CO_MUNI_RESIDENCIA LIKE ?"
        params.append(config.codigo_uf(esc.uf) + "%")
    elif esc.nivel == "MUN":
        sql += " AND CO_MUNI_RESIDENCIA = ?"
        params.append(esc.mun)

    return _uma_linha(sql, params)


def indicador_tb_contatos(esc: Escopo) -> dict:
    """Contatos identificados e examinados, com a proporção."""
    return _indicador_tb(
        "indicadores_tb_contatos",
        esc,
        "sum(identificados_total) AS identificados, sum(examinados_total) AS examinados",
    )


def indicador_tb_cultura(esc: Escopo) -> dict:
    """Cultura realizada em casos de retratamento, com a proporção."""
    return _indicador_tb(
        "indicadores_tb_cultura_retratamento",
        esc,
        "sum(total_retratamento) AS retratamento, "
        "sum(cultura_realizada_total) AS cultura",
    )


#: Colunas de `incidence` que servem uma métrica diretamente.
_COLUNA_DIRETA = {
    "casos": "casos_total",
    "cura": "casos_cura",
    "pop": "pop_total",
    "incid": "incid_100k_total",
}

#: Métricas derivadas de óbitos do SIM, que `incidence` não tem.
_DERIVADA_DE_OBITO = {"obitos", "mortalidade", "letalidade"}


def valores_por_geografia(esc: Escopo, metrica: str) -> pd.Series:
    """Valor da métrica para cada geografia dentro do escopo, para o mapa.

    O nível do ``Escopo`` diz o que está **selecionado**; o mapa desenha um
    nível abaixo. No Brasil pinta as UFs; numa UF, os municípios dela.

    O índice é a chave da camada geográfica: sigla no nível de UF, código de
    6 dígitos no de município.
    """
    metrica = str(metrica or "incid")
    desce_para_municipio = esc.nivel in ("UF", "MUN")

    if desce_para_municipio:
        fonte = caminho(
            "incidence",
            doenca=config.cod_agregado(esc.doenca),
            nivel="MUN",
            ano=esc.ano,
        )
        chave, onde, params = "cod_mun6", " WHERE uf = ?", [esc.uf]
    else:
        fonte = caminho(
            "incidence", doenca=config.cod_agregado(esc.doenca), nivel="UF", ano=esc.ano
        )
        chave, onde, params = "uf", "", []

    if metrica in _COLUNA_DIRETA:
        coluna = _COLUNA_DIRETA[metrica]
        sql = f"SELECT {chave}, {coluna} AS valor FROM read_parquet('{fonte}', hive_partitioning=true){onde}"
        df = conectar().execute(sql, params).fetchdf()
        return df.set_index(chave)["valor"]

    if metrica in _DERIVADA_DE_OBITO:
        base = conectar().execute(
            f"SELECT {chave}, casos_total, pop_total "
            f"FROM read_parquet('{fonte}', hive_partitioning=true){onde}",
            params,
        ).fetchdf()

        sim = caminho(
            "cache_ts_sim_obitos",
            nivel="MUN" if desce_para_municipio else "UF",
            doenca=config.cod_sim(esc.doenca),
            ano=esc.ano,
        )
        chave_sim = "geo_id" if desce_para_municipio else "uf"
        obitos = conectar().execute(
            f"SELECT {chave_sim} AS {chave}, sum(casos_obitos) AS obitos "
            f"FROM read_parquet('{sim}', hive_partitioning=true)"
            + (" WHERE uf = ?" if desce_para_municipio else "")
            + f" GROUP BY {chave_sim}",
            params if desce_para_municipio else [],
        ).fetchdf()

        juncao = base.merge(obitos, on=chave, how="left")
        juncao["obitos"] = juncao["obitos"].fillna(0)

        if metrica == "obitos":
            valor = juncao["obitos"]
        elif metrica == "mortalidade":
            valor = juncao["obitos"] / juncao["pop_total"].replace(0, pd.NA) * 100_000
        else:
            valor = juncao["obitos"] / juncao["casos_total"].replace(0, pd.NA) * 100

        return pd.Series(valor.values, index=juncao[chave])

    # As demais (0-14, HIV, interrupção) exigem outros datasets e entram
    # quando o mapa passar a aceitá-las. Melhor um mapa vazio e honesto do
    # que um mapa colorido com a métrica errada.
    return pd.Series(dtype=float)


def componentes_municipais(esc: Escopo) -> pd.DataFrame:
    """Casos, cura, população e óbitos por município da UF.

    Base para agregar por macrorregião e região de saúde: as taxas precisam
    ser recalculadas a partir das somas, não tiradas como média das taxas
    municipais.
    """
    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel="MUN", ano=esc.ano
    )
    base = conectar().execute(
        f"SELECT cod_mun6, casos_total AS casos, casos_cura AS cura, "
        f"pop_total AS pop FROM read_parquet('{fonte}', hive_partitioning=true) "
        f"WHERE uf = ?",
        [esc.uf],
    ).fetchdf()

    sim = caminho(
        "cache_ts_sim_obitos",
        nivel="MUN",
        doenca=config.cod_sim(esc.doenca),
        ano=esc.ano,
    )
    obitos = conectar().execute(
        f"SELECT geo_id AS cod_mun6, sum(casos_obitos) AS obitos "
        f"FROM read_parquet('{sim}', hive_partitioning=true) "
        f"WHERE uf = ? GROUP BY geo_id",
        [esc.uf],
    ).fetchdf()

    juncao = base.merge(obitos, on="cod_mun6", how="left")
    juncao["obitos"] = juncao["obitos"].fillna(0)
    return juncao.set_index("cod_mun6")


def valores_por_regiao(esc: Escopo, metrica: str, nivel: str) -> pd.Series:
    """Valor da métrica por macrorregião ou região de saúde de PE."""
    from . import pernambuco

    return pernambuco.agregar(componentes_municipais(esc), metrica, nivel)


def serie_anual(esc: Escopo, metrica: str = "casos") -> pd.DataFrame:
    """Série histórica anual da métrica no recorte, vinda de ``incidence``.

    Diferente de :func:`serie_mensal`, esta é por **residência**, igual aos
    KPIs — `incidence` e `_cache_ts` usam critérios geográficos diferentes.
    """
    coluna = _COLUNA_DIRETA.get(metrica, "casos_total")
    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel=esc.nivel
    )
    sql = f"SELECT ano, {coluna} AS valor FROM read_parquet('{fonte}', hive_partitioning=true)"
    params: list = []
    onde, p = esc.filtro_geo()
    if onde:
        sql += f" WHERE {onde}"
        params += p
    return conectar().execute(sql + " ORDER BY ano", params).fetchdf()
