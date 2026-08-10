"""Configuração do cache da aplicação.

Não testa o Streamlit — testa as decisões, que estão em constantes no `app.py`
e são fáceis de mexer sem pensar. O que importa aqui é que os números
continuem justificados pelo tamanho medido dos objetos.
"""

from __future__ import annotations

import pickle
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = (RAIZ / "app.py").read_text(encoding="utf-8")


def _constante(nome: str) -> int:
    achado = re.search(rf"^{nome} = (.+)$", APP, re.M)
    assert achado, f"constante {nome} sumiu do app.py"
    return int(eval(achado.group(1).split("#")[0].strip()))  # noqa: S307


def test_ttl_e_longo_porque_o_dado_e_imutavel() -> None:
    """Os parquets só mudam quando alguém os troca e reinicia o serviço.

    O TTL de 10 minutos que existia antes só produzia releitura periódica sem
    motivo. Continua finito para limitar o estrago de uma troca sem reinício.
    """
    ttl = _constante("TTL_DADOS")
    assert ttl >= 3600, "TTL curto demais: volta a reler sem motivo"
    assert ttl <= 7 * 24 * 3600, "TTL longo demais: serviria dado velho por semanas"


def test_todo_cache_declara_limite_de_entradas() -> None:
    """`_camada` guardava geometria **sem limite** — 359 KB por UF.

    Cache sem teto num processo de longa duração é vazamento com outro nome.
    """
    sem_limite = [
        linha
        for linha in APP.splitlines()
        if "@st.cache_data(" in linha and "max_entries" not in linha
    ]
    # Os lookups de rótulo são poucos e minúsculos; os demais precisam de teto.
    assert len(sem_limite) <= 3, f"cache sem max_entries: {sem_limite}"


def test_limites_seguem_a_ordem_do_tamanho() -> None:
    """Quanto maior o objeto, menos entradas cabem."""
    leves = _constante("ENTRADAS_LEVES")
    medias = _constante("ENTRADAS_MEDIAS")
    pesadas = _constante("ENTRADAS_PESADAS")
    geometria = _constante("ENTRADAS_GEOMETRIA")
    assert leves > medias > pesadas > geometria


def test_orcamento_de_memoria_do_cache_de_geometria() -> None:
    """O limite precisa refletir o tamanho real da malha, não um palpite."""
    from src.data import geo

    maior = max(len(pickle.dumps(geo.municipios(uf))) for uf in ("MG", "SP", "BA"))
    teto_mb = _constante("ENTRADAS_GEOMETRIA") * maior / 1e6
    assert teto_mb < 40, f"pior caso do cache de geometria em {teto_mb:.0f} MB"


@pytest.mark.parametrize("nome", ["ENTRADAS_LEVES", "ENTRADAS_MEDIAS", "ENTRADAS_PESADAS"])
def test_limites_nao_cobrem_a_cardinalidade_e_isso_e_esperado(nome: str) -> None:
    """Documenta a premissa: isto é limite de memória, não de cobertura.

    São 8.064 combinações possíveis só para o mapa e 89.568 para os KPIs.
    Nenhum limite razoável cobre isso — o cache serve o caminho que o usuário
    realmente percorre, e a releitura custa milissegundos.
    """
    assert _constante(nome) < 8000
