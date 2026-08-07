"""Comparação com os valores lidos da tela do dashboard em R.

Este é o gate do bloco 1.3, parado desde o começo por não termos o R rodando.
Destravou quando os dois painéis ficaram acessíveis; os valores estão em
`referencia_r.json`, com a data e a URL de onde saíram.

O teste **não falha** nas divergências já conhecidas — elas estão listadas em
`DIVERGENTES` e documentadas em `excecoes.md`. Falhar aqui todo dia não
informa nada; o que informa é o dia em que algo hoje idêntico deixar de ser.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack

REFERENCIA = json.loads(
    (Path(__file__).parent / "referencia_r.json").read_text(encoding="utf-8")
)

#: Tolerância relativa. Os cards do R mostram poucas casas — "3,0" contra o
#: nosso 2,9993 —, então a comparação é do valor exibido, não do float.
TOLERANCIA = 0.01

#: KPIs cuja divergência é conhecida e ainda não explicada. Ver `excecoes.md`.
#: Não é lista de perdão permanente: é o que precisa de resposta da equipe.
DIVERGENTES = {"casos", "incid", "cura", "letalidade"}


def _recortes():
    for r in REFERENCIA["recortes"]:
        yield pytest.param(r, id=f"{r['uf'] or 'BR'}-{r['ano']}")


@pytest.mark.parametrize("recorte", _recortes())
def test_kpis_que_devem_bater(recorte: dict) -> None:
    """Os que reproduzem o R hoje. Regressão aqui é bug nosso."""
    esc = Escopo(pack.DOENCA, recorte["ano"], recorte["nivel"], uf=recorte["uf"])
    nosso = calc.calcular(esc)

    for nome, esperado in recorte["kpis"].items():
        if nome in DIVERGENTES:
            continue
        obtido = getattr(nosso, nome)
        assert obtido is not None, f"{nome} não calculado"
        assert obtido == pytest.approx(esperado, rel=TOLERANCIA), (
            f"{nome}: nosso {obtido} vs R {esperado}"
        )


def test_denominadores_do_sinan_batem_exatamente() -> None:
    """O achado mais forte da comparação.

    Testados e encerramentos de PE conferem no número exato — 8.250 e 8.700 —,
    o que mostra que os percentuais derivados do `sinan_landing` reproduzem a
    regra do R, incluindo o critério de quem entra no denominador.
    """
    import unicodedata

    from src.data import leitura

    esc = Escopo(pack.DOENCA, 2024, "UF", uf="PE")
    esperado = REFERENCIA["recortes"][1]["denominadores"]

    def sem_acento(texto: str) -> str:
        base = unicodedata.normalize("NFD", str(texto))
        return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()

    hiv = leitura.variavel_sinan(esc, "HIV")
    rotulos = hiv["valor_lbl"].map(sem_acento)
    negativo = rotulos.str.contains("negativ|nao reag", regex=True, na=False)
    positivo = ~negativo & rotulos.str.contains("positiv|reagente", regex=True, na=False)
    assert int(hiv.loc[positivo | negativo, "n"].sum()) == esperado["hiv_testados"]

    encerramentos = leitura.variavel_sinan(esc, "SITUA_ENCE")
    assert int(encerramentos["n"].sum()) == esperado["encerramentos"]


@pytest.mark.parametrize("recorte", _recortes())
def test_divergentes_continuam_divergindo(recorte: dict) -> None:
    """Prende a divergência para ela não sumir sem ninguém notar.

    Se um destes passar a bater, alguém corrigiu a origem — e aí este teste
    falha pedindo que a exceção saia de `excecoes.md`.
    """
    esc = Escopo(pack.DOENCA, recorte["ano"], recorte["nivel"], uf=recorte["uf"])
    nosso = calc.calcular(esc)

    for nome in DIVERGENTES & set(recorte["kpis"]):
        obtido = getattr(nosso, nome)
        esperado = recorte["kpis"][nome]
        if obtido == pytest.approx(esperado, rel=TOLERANCIA):
            pytest.fail(
                f"{nome} passou a bater com o R ({obtido} ≈ {esperado}). "
                f"Tire de DIVERGENTES e de excecoes.md."
            )
