"""Monta o pacote de dados que vai para o servidor.

Em disco há 892 MB, mas a aplicação lê 213 MB. A diferença quase toda é o
``_geo_cache``: 683 MB de GeoJSON gzipado que o pipeline da equipe parceira
usou para gerar a geometria e que nós já convertemos para GeoParquet em
``data/geo`` (3,7 MB). Dele sobra em uso um único arquivo, o de centroides.

Copiar os 892 MB funcionaria e seria três vezes mais lento para subir, três
vezes mais caro em disco e deixaria no servidor uma cópia de dado bruto que
ninguém lê — do tipo que alguém encontra em dois anos e não sabe se pode
apagar.

Uso::

    python -m scripts.preparar_publicacao --destino /tmp/pacote
    python -m scripts.preparar_publicacao --conferir     # só mede, não copia
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from src.data import config

#: Datasets que a aplicação realmente consulta. A lista é conferida contra o
#: código pelo teste `test_publicacao.py` — dataset novo no `leitura.py` sem
#: entrada aqui quebra o teste, não a produção.
DATASETS = (
    "_cache_ts",
    "cache_ts_sim_obitos",
    "cases_new",
    "incidence",
    "incidence_0_14",
    "indicadores_tb_contatos",
    "indicadores_tb_cultura_retratamento",
    # Atenção: não existe dataset "obitos". O diretório de mesmo nome em
    # `data/parquet/dashboard/` nunca é lido — `obitos` no código é sempre
    # nome de coluna. Entrou nesta lista por um grep meu que confundiu os
    # dois, e o teste de publicação pegou.
    "obitos_sim_faixa",
    "piramides",
    "sinan_dict",
    "sinan_landing",
)

#: O único arquivo aproveitado do `_geo_cache`. Ver `src/data/geo.centroides`.
CENTROIDES = Path("_geo_cache") / "municipios_centroids.parquet"


def _tamanho(caminho: Path) -> int:
    if caminho.is_file():
        return caminho.stat().st_size
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file())


def itens() -> list[tuple[Path, Path]]:
    """Pares ``(origem, destino relativo)`` que compõem o pacote."""
    dados = config.data_dir()
    painel = config.dashboard_dir()
    relativo = painel.relative_to(dados)

    pares: list[tuple[Path, Path]] = []
    for nome in DATASETS:
        origem = painel / nome
        if origem.is_dir():
            pares.append((origem, relativo / nome))

    centroides = painel / CENTROIDES
    if centroides.is_file():
        pares.append((centroides, relativo / CENTROIDES))

    for nome in ("geo", "support"):
        origem = dados / nome
        if origem.is_dir():
            pares.append((origem, Path(nome)))

    return pares


def relatorio(pares: list[tuple[Path, Path]]) -> int:
    total = 0
    for origem, destino in pares:
        n = _tamanho(origem)
        total += n
        print(f"  {str(destino):48} {n / 1e6:8.1f} MB")
    print(f"  {'TOTAL':48} {total / 1e6:8.1f} MB")
    return total


def copiar(destino: Path, pares: list[tuple[Path, Path]]) -> None:
    for origem, relativo in pares:
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if origem.is_dir():
            shutil.copytree(origem, alvo, dirs_exist_ok=True)
        else:
            shutil.copy2(origem, alvo)
        print(f"  copiado {relativo}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--destino", type=Path, help="pasta onde montar o pacote")
    ap.add_argument(
        "--conferir", action="store_true", help="só mede o tamanho, não copia"
    )
    args = ap.parse_args()

    pares = itens()
    if not pares:
        print("Nada encontrado. Confira SINAN_DATA_DIR.", file=sys.stderr)
        return 1

    print("Conteúdo do pacote:")
    total = relatorio(pares)
    em_disco = _tamanho(config.data_dir())
    print(f"\n  em disco hoje: {em_disco / 1e6:.1f} MB")
    print(f"  economia:      {(em_disco - total) / 1e6:.1f} MB")

    if args.conferir:
        return 0
    if not args.destino:
        print("\nInforme --destino, ou use --conferir.", file=sys.stderr)
        return 1

    print(f"\nCopiando para {args.destino}…")
    copiar(args.destino, pares)
    print("Pronto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
