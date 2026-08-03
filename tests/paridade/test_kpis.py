"""Harness de paridade dos KPIs.

Compara ``src.data.kpis`` com as referências de ``referencias.json``, geradas
por SQL cru independente (ver ``gerar_referencias.py``).

Regenerar as referências após mudar os dados::

    python -m tests.paridade.gerar_referencias
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data import kpis
from src.data.escopo import Escopo

REFERENCIAS = Path(__file__).parent / "referencias.json"

#: Tolerância relativa. As duas implementações fazem a mesma conta em ordem
#: diferente; só a última casa decimal pode divergir.
TOLERANCIA = 1e-9

CAMPOS = (
    "casos",
    "obitos",
    "cura",
    "pop",
    "incid",
    "mortalidade",
    "letalidade",
    "casos_0_14",
    "taxa_det_0_14",
    "hiv_pos_pct",
    "interrupcao_trat_pct",
)


def carregar() -> dict:
    if not REFERENCIAS.exists():
        pytest.skip(
            f"{REFERENCIAS.name} não existe. Rode: "
            f"python -m tests.paridade.gerar_referencias"
        )
    return json.loads(REFERENCIAS.read_text(encoding="utf-8"))


REFS = carregar()


def _escopo(dados: dict) -> Escopo:
    return Escopo(
        doenca=dados["doenca"],
        ano=dados["ano"],
        nivel=dados["nivel"],
        uf=dados["uf"],
        mun=dados["mun6"],
    )


@pytest.mark.parametrize("rotulo", sorted(REFS))
@pytest.mark.parametrize("campo", CAMPOS)
def test_kpi_bate_com_referencia(rotulo: str, campo: str) -> None:
    caso = REFS[rotulo]
    esperado = caso["kpis"][campo]
    obtido = getattr(kpis.calcular(_escopo(caso["escopo"])), campo)

    if esperado is None:
        assert obtido is None, f"{rotulo}/{campo}: esperado None, veio {obtido}"
        return

    assert obtido is not None, f"{rotulo}/{campo}: esperado {esperado}, veio None"
    assert obtido == pytest.approx(esperado, rel=TOLERANCIA), (
        f"{rotulo}/{campo}: esperado {esperado}, veio {obtido}"
    )


@pytest.mark.parametrize("rotulo", sorted(REFS))
def test_regra_ms_da_interrupcao(rotulo: str) -> None:
    """A regra alternativa do MS também precisa bater — ver armadilha 4."""
    caso = REFS[rotulo]
    esperado = caso["kpis"]["interrupcao_trat_pct_ms"]
    obtido = kpis.interrupcao_trat_pct(_escopo(caso["escopo"]), regra="ms")

    if esperado is None:
        assert obtido is None
    else:
        assert obtido == pytest.approx(esperado, rel=TOLERANCIA)


def test_regra_ms_difere_da_paridade() -> None:
    """Guarda a divergência conhecida: as duas regras não podem convergir.

    Se este teste falhar, ou a implementação de uma das regras quebrou, ou os
    dados mudaram — nos dois casos a pendência da armadilha 4 precisa ser
    reavaliada antes de seguir.
    """
    esc = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")
    assert kpis.interrupcao_trat_pct(esc, "paridade") == pytest.approx(11.885, abs=1e-3)
    assert kpis.interrupcao_trat_pct(esc, "ms") == pytest.approx(14.753, abs=1e-3)


def test_obitos_nao_vem_de_incidence() -> None:
    """Regressão da armadilha 1: ``incidence.casos_obitos`` é zero para TB.

    Se algum dia os óbitos passarem a sair de ``incidence``, este teste falha
    e evita que a mortalidade vire zero silenciosamente.
    """
    from src.data import leitura

    esc = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")
    assert leitura.incidencia(esc).get("casos_obitos") is None  # nem é lida
    assert leitura.obitos_sim(esc) > 0
