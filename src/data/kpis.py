"""Cálculo dos KPIs.

Fórmulas em docs/contrato-dados.md. Todas devolvem ``None`` quando o
denominador é zero ou o dado não existe — nunca zero, que seria confundido
com um valor real.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from . import leitura
from .escopo import Escopo

POR_100K = 100_000


def _div(numerador, denominador, fator: float = 1.0) -> float | None:
    try:
        n, d = float(numerador), float(denominador)
    except (TypeError, ValueError):
        return None
    if d <= 0 or n != n or d != d:  # NaN não é igual a si mesmo
        return None
    return (n / d) * fator


def _sem_acento(texto) -> str:
    s = str(texto or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Regra do indicador de interrupção de tratamento
# ---------------------------------------------------------------------------
# Pendência aberta — ver docs/contrato-dados.md, armadilha 4, e o gate da
# semana 1 no cronograma. O padrão aqui é "paridade", que reproduz o
# dashboard em R. Trocar para "ms" só depois de decidir com a equipe de R,
# registrando em tests/paridade/excecoes.md.

REGRA_INTERRUPCAO = "paridade"

#: Códigos de SITUA_ENCE contados como abandono.
_ABANDONO = {"paridade": {"2"}, "ms": {"2", "10"}}

#: Códigos excluídos do denominador. Vazio na regra do R — ela usa todos.
_NAO_AVALIADOS = {"paridade": set(), "ms": {"0", "5", "7", "8"}}


@dataclass(frozen=True, slots=True)
class Kpis:
    casos: float | None = None
    obitos: float | None = None
    cura: float | None = None
    #: Curas sobre casos novos do **mesmo ano**, em %.
    #:
    #: É aproximação, e a tela diz isso. Tratamento de TB leva cerca de seis
    #: meses, então o desfecho dos casos de um ano só se conhece no seguinte —
    #: o boletim do MS reporta coorte fechada, e nós não temos como fechar a
    #: coorte com os agregados que recebemos. `letalidade` já convive com a
    #: mesma aproximação, pelo mesmo motivo.
    cura_pct: float | None = None
    pop: float | None = None
    incid: float | None = None
    mortalidade: float | None = None
    letalidade: float | None = None
    casos_0_14: float | None = None
    pop_0_14: float | None = None
    taxa_det_0_14: float | None = None
    hiv_pos_pct: float | None = None
    interrupcao_trat_pct: float | None = None


def calcular(esc: Escopo, regra_interrupcao: str | None = None) -> Kpis:
    """Todos os KPIs do recorte."""
    inc = leitura.incidencia(esc)
    inc14 = leitura.incidencia_0_14(esc)

    casos = inc.get("casos_total")
    cura = inc.get("casos_cura")
    pop = inc.get("pop_total")

    # Óbitos vêm do SIM, não de incidence — lá o campo é zero para TB.
    obitos = leitura.obitos_sim(esc)

    casos_0_14 = inc14.get("casos_0_14_total")
    pop_0_14 = inc14.get("pop_0_14_total")

    return Kpis(
        casos=_num(casos),
        obitos=_num(obitos),
        cura=_num(cura),
        pop=_num(pop),
        incid=_div(casos, pop, POR_100K),
        mortalidade=_div(obitos, pop, POR_100K),
        letalidade=_div(obitos, casos, 100),
        cura_pct=_div(cura, casos, 100),
        casos_0_14=_num(casos_0_14),
        pop_0_14=_num(pop_0_14),
        taxa_det_0_14=_div(casos_0_14, pop_0_14, POR_100K),
        hiv_pos_pct=hiv_pos_pct(esc),
        interrupcao_trat_pct=interrupcao_trat_pct(esc, regra_interrupcao),
    )


def _num(valor) -> float | None:
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def hiv_pos_pct(esc: Escopo) -> float | None:
    """Positividade do HIV entre os testados (tuberculose).

    Denominador = positivos + negativos. "Não realizado" e "em andamento"
    ficam de fora — testar a regra pelo rótulo, porque os códigos de HIV não
    são estáveis entre versões da ficha.
    """
    if esc.doenca != "TUBERCULOSE":
        return None

    df = leitura.variavel_sinan(esc, "HIV")
    if df.empty:
        return None

    rotulos = df["valor_lbl"].map(_sem_acento)
    negativo = rotulos.str.contains("negativ|nao reag", regex=True, na=False)
    positivo = ~negativo & rotulos.str.contains("positiv|reagente", regex=True, na=False)

    pos = float(df.loc[positivo, "n"].sum())
    testados = float(df.loc[positivo | negativo, "n"].sum())
    return _div(pos, testados, 100)


def interrupcao_trat_pct(esc: Escopo, regra: str | None = None) -> float | None:
    """Interrupção de tratamento a partir de SITUA_ENCE (tuberculose).

    Duas regras disponíveis — ver docs/contrato-dados.md, armadilha 4:

    ``paridade``
        Reproduz o dashboard em R: conta apenas o código 2 e usa todos os
        encerramentos no denominador.
    ``ms``
        Soma abandono (2) e abandono primário (10), e tira os não avaliados
        (0, 5, 7, 8) do denominador.

    Filtra por **código**, nunca por rótulo: ``valor_lbl`` vem reagrupado e
    põe abandono, óbito e falência todos como "Desfavorável".
    """
    if esc.doenca != "TUBERCULOSE":
        return None

    regra = (regra or REGRA_INTERRUPCAO).strip().lower()
    if regra not in _ABANDONO:
        raise ValueError(f"Regra inválida: {regra!r}. Esperado 'paridade' ou 'ms'.")

    df = leitura.variavel_sinan(esc, "SITUA_ENCE")
    if df.empty:
        return None

    abandono = float(df.loc[df["valor"].isin(_ABANDONO[regra]), "n"].sum())
    denominador = float(df.loc[~df["valor"].isin(_NAO_AVALIADOS[regra]), "n"].sum())
    return _div(abandono, denominador, 100)
