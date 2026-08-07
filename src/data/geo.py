"""Leitura da geometria pré-processada.

As camadas vêm de ``data/geo/``, geradas por ``scripts.preparar_geometria``.
Nunca leia o ``_geo_cache`` do pipeline direto na aplicação: ele é GeoJSON
gzipado e custa mais de dez vezes o tempo de um GeoParquet.

Regenerar após qualquer mudança nos dados de origem::

    python -m scripts.preparar_geometria
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import geopandas as gpd

from . import config


def geo_dir() -> Path:
    return config.data_dir() / "geo"


def _ler(caminho: Path) -> gpd.GeoDataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Camada não encontrada: {caminho}\n"
            f"Gere com: python -m scripts.preparar_geometria"
        )
    return gpd.read_parquet(caminho)


@lru_cache(maxsize=32)
def municipios(uf: str) -> gpd.GeoDataFrame:
    """Municípios de uma UF. Colunas: ``cod_mun6``, ``nome_mun``, ``uf``."""
    sigla = str(uf or "").strip().upper()
    if sigla not in config.CODIGO_POR_UF:
        raise ValueError(f"UF desconhecida: {uf!r}")
    return _ler(geo_dir() / "municipios" / f"{sigla}.parquet")


@lru_cache(maxsize=1)
def ufs() -> gpd.GeoDataFrame:
    """As 27 unidades da federação."""
    return _ler(geo_dir() / "ufs.parquet")


@lru_cache(maxsize=1)
def pais() -> gpd.GeoDataFrame:
    """Contorno do Brasil."""
    return _ler(geo_dir() / "pais.parquet")


@lru_cache(maxsize=2)
def regioes_pe(nivel: str = "macro") -> gpd.GeoDataFrame:
    """Recortes de saúde de Pernambuco. Coluna ``regiao``.

    ``macro`` são as macrorregiões; ``micro`` são as regiões de saúde.
    Exclusivo de PE — vem dos shapefiles de apoio, não do pipeline.
    """
    chave = str(nivel or "macro").strip().lower()
    if chave not in ("macro", "micro"):
        raise ValueError(f"Nível inválido: {nivel!r}. Esperado 'macro' ou 'micro'.")
    return _ler(geo_dir() / f"pe_{chave}.parquet")


@lru_cache(maxsize=1)
def centroides() -> gpd.GeoDataFrame:
    """Centroides dos municípios, para rótulos e para posicionar marcadores."""
    import pandas as pd

    caminho = config.dashboard_dir() / "_geo_cache" / "municipios_centroids.parquet"
    if not caminho.exists():
        raise FileNotFoundError(f"Centroides não encontrados: {caminho}")

    df = pd.read_parquet(caminho)
    df["cod_mun6"] = df["cod_mun7"].astype(str).str[:6]
    return gpd.GeoDataFrame(
        df[["cod_mun6", "nome_mun", "uf"]],
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=4326,
    )


def limpar_cache() -> None:
    """Descarta a geometria em memória. Útil após regerar as camadas."""
    for fn in (municipios, ufs, pais, regioes_pe, centroides):
        fn.cache_clear()
