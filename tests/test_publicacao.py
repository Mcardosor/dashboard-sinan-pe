"""O pacote de publicação precisa conter tudo que a aplicação lê.

Dataset novo em `leitura.py` sem entrada em `DATASETS` produziria um servidor
que sobe, renderiza, e só quebra quando alguém clica no painel que usa o
arquivo que não foi copiado. Melhor descobrir aqui.

A fonte da verdade é `conexao.PARTICOES`, não uma varredura do código: todo
dataset legível precisa declarar a ordem das partições ali, e nomes chegam ao
`caminho()` por variável em alguns pontos — `_indicador_tb` é um deles —, o
que um regex sobre o fonte não enxerga.
"""

from __future__ import annotations

from pathlib import Path

from scripts.preparar_publicacao import DATASETS, itens
from src.data import conexao


def test_todo_dataset_legivel_entra_no_pacote() -> None:
    faltando = set(conexao.PARTICOES) - set(DATASETS)
    assert not faltando, (
        f"declarados em PARTICOES mas fora do pacote: {sorted(faltando)}. "
        f"Acrescente em scripts/preparar_publicacao.DATASETS."
    )


def test_pacote_nao_leva_dataset_ilegivel() -> None:
    """O contrário também importa.

    `obitos` entrou na lista por engano — é nome de coluna em todo o código,
    e o diretório de mesmo nome nunca é lido. Foram 3,6 MB de dado morto que
    iriam para o servidor sem ninguém notar.
    """
    sobrando = set(DATASETS) - set(conexao.PARTICOES)
    assert not sobrando, (
        f"no pacote mas sem partição declarada, logo ilegível: {sorted(sobrando)}"
    )


def test_pacote_inclui_geometria_e_apoio() -> None:
    destinos = {str(rel) for _, rel in itens()}
    assert "geo" in destinos, "sem data/geo o mapa não abre"
    assert "support" in destinos, "sem data/support somem os recortes de PE"


def test_pacote_leva_os_centroides_e_nao_o_cache_inteiro() -> None:
    """683 MB de GeoJSON bruto iam junto; a aplicação lê um arquivo de lá."""
    destinos = [str(rel) for _, rel in itens()]
    cache = [d for d in destinos if "_geo_cache" in d]
    esperado = str(Path("parquet/dashboard/_geo_cache/municipios_centroids.parquet"))
    assert cache == [esperado], (
        f"o `_geo_cache` deve entrar só pelo arquivo de centroides, veio: {cache}"
    )
