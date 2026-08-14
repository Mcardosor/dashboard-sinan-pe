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


def test_pacote_nao_leva_nada_do_geo_cache() -> None:
    """683 MB de GeoJSON bruto do pipeline não vão para o servidor.

    Por um tempo o pacote levava um arquivo de lá, o de centroides, porque
    `geo.centroides()` o lia. Descobriu-se que essa função não era chamada por
    nenhum caminho de produção; as duas saíram em 14/ago/2026 e o `_geo_cache`
    deixou de entrar por qualquer via.

    O teste é sobre o diretório inteiro, e não sobre aquele arquivo: assim ele
    continua valendo se alguém voltar a precisar de um dado de lá e for pelo
    caminho errado — copiar do cache bruto em vez de converter para GeoParquet
    em `data/geo`.
    """
    destinos = [str(rel) for _, rel in itens()]
    cache = [d for d in destinos if "_geo_cache" in d]
    assert cache == [], f"o `_geo_cache` não deve entrar no pacote, veio: {cache}"
