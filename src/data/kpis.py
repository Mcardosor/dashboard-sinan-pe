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
# Três regras, e a diferença entre elas não é detalhe de implementação: é
# qual pergunta o indicador responde.
#
#   paridade  {2}    / todos      reproduz o dashboard em R
#   ms        {2,10} / avaliados  o indicador do Ministério, que exclui os
#                                 não avaliados do denominador
#   boletim   {2,10} / todos      como a Tabela 9 do Boletim Epidemiológico
#                                 apresenta a distribuição de desfechos
#
# As duas últimas são ambas "do MS" e não se contradizem: uma é definição de
# indicador de monitoramento, a outra é apresentação de distribuição — no
# boletim, cura, interrupção e "não avaliados" são três colunas da **mesma**
# base, o que só fecha com o denominador completo.
#
# Medido para o Brasil em 2024:
#
#     paridade = 14,91%      ms = 17,20%      boletim = 15,52%
#     Tabela 9 do boletim, casos novos de TB: 15,2%
#
# `boletim` é a que reproduz o publicado; os 0,32 pontos restantes são a
# defasagem de extração. Nosso denominador tem 75.404 encerramentos e as
# porcentagens do MS implicam 77.467, com a diferença concentrada em "não
# avaliados" — 9,7% aqui contra 12,6% lá, que é o que se espera de casos ainda
# sem encerramento numa extração anterior. Aplicando `{2,10}` sobre o
# denominador **deles**, dá 15,11%.
#
# **Atenção à população.** A Tabela 9 publica três: todos os casos novos de TB
# (86.204), só pulmonar (74.885) e pulmonar confirmada em laboratório
# (56.388), com interrupção de 15,2%, 15,9% e 16,5%. A nossa é a primeira.
# Comparar com 16,5% — como se chegou a fazer aqui — é comparar populações
# diferentes.
#
# Qual exibir continua sendo decisão com a equipe de R, e agora com três
# opções em vez de duas. Ver tests/paridade/excecoes.md.

REGRA_INTERRUPCAO = "boletim"

#: Códigos de SITUA_ENCE contados como interrupção. O MS soma abandono (2) e
#: abandono primário (10) — quem nunca chegou a iniciar também interrompeu.
_ABANDONO = {
    "paridade": {"2"},
    "ms": {"2", "10"},
    "boletim": {"2", "10"},
}

#: Ordem e composição dos desfechos empilhados da evolução, no formato da
#: Figura 22 do Boletim de TB 2026 — cura, interrupção, óbito e o resto.
#:
#: O denominador é **todos os encerramentos**, o mesmo de
#: `interrupcao_trat_pct` sob a regra `boletim`, e por isso as quatro fatias
#: somam 100% por construção: a última é o complemento, não uma lista. Listar
#: os códigos dela deixaria um código novo do SINAN sumir do gráfico sem
#: ninguém notar; sendo complemento, ele aparece — no balde errado, mas
#: aparece, e o total continua fechando.
#:
#: O boletim exclui do denominador os encerramentos por TB drogarresistente,
#: mudança de esquema e falência. Nós não excluímos, para o gráfico usar o
#: mesmo denominador do card de interrupção — ver `tests/paridade/excecoes.md`.
GRUPOS_DESFECHO: tuple[tuple[str, frozenset[str]], ...] = (
    ("cura", frozenset({"1"})),
    ("interrupcao", frozenset(_ABANDONO[REGRA_INTERRUPCAO])),
    ("obito", frozenset({"3", "4"})),
    ("outros", frozenset()),  # complemento; ver acima
)

#: Rótulo de cada grupo na legenda.
ROTULO_DESFECHO = {
    "cura": "Cura",
    "interrupcao": "Interrupção",
    "obito": "Óbito",
    "outros": "Não avaliados e outros",
}


def grupo_do_desfecho(codigo: str) -> str:
    """Em que fatia do empilhado um código de `SITUA_ENCE` cai.

    **Normaliza o zero à esquerda.** O dataset traz `03` e `04` convivendo com
    `3` e `4` — só em 2018 e 2019, 177 registros —, e `trim` não resolve isso.
    Sem normalizar, esses óbitos cairiam silenciosamente em "outros".
    """
    limpo = str(codigo).strip().lstrip("0") or "0"
    for nome, codigos in GRUPOS_DESFECHO:
        if limpo in codigos:
            return nome
    return "outros"


#: Códigos excluídos do denominador. Só o indicador de monitoramento do MS os
#: exclui; o R e o boletim usam todos os encerramentos.
_NAO_AVALIADOS = {
    "paridade": set(),
    "ms": {"0", "5", "7", "8"},
    "boletim": set(),
}


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

    Três regras disponíveis — ver docs/contrato-dados.md, armadilha 4:

    ``paridade``
        Reproduz o dashboard em R: conta apenas o código 2 e usa todos os
        encerramentos no denominador. Confirmado pela responsável pelo painel
        em R em 20/ago/2026: "eu conto só o 2".
    ``ms``
        Indicador de monitoramento do Ministério: soma abandono (2) e abandono
        primário (10), e tira os não avaliados (0, 5, 7, 8) do denominador.
    ``boletim``
        Como a Tabela 9 do Boletim Epidemiológico apresenta: mesmo numerador
        que ``ms``, mas com todos os encerramentos no denominador.

    Filtra por **código**, nunca por rótulo: ``valor_lbl`` vem reagrupado e
    põe abandono, óbito e falência todos como "Desfavorável".
    """
    if esc.doenca != "TUBERCULOSE":
        return None

    regra = (regra or REGRA_INTERRUPCAO).strip().lower()
    if regra not in _ABANDONO:
        raise ValueError(
            f"Regra inválida: {regra!r}. Esperado uma de {sorted(_ABANDONO)}."
        )

    df = leitura.variavel_sinan(esc, "SITUA_ENCE")
    if df.empty:
        return None

    abandono = float(df.loc[df["valor"].isin(_ABANDONO[regra]), "n"].sum())
    denominador = float(df.loc[~df["valor"].isin(_NAO_AVALIADOS[regra]), "n"].sum())
    return _div(abandono, denominador, 100)
