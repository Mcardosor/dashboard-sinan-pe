"""Gráficos do painel direito.

Altair, e não ECharts como no original: `st.altair_chart` tem evento de clique
nativo — verificado com clique real antes da escolha, não só pela assinatura —
e já vem com o Streamlit, sem componente de terceiros. O ranking precisa desse
evento para navegar o mapa ao clicar numa barra.

A configuração visual vive em :func:`tema` e é aplicada a todo gráfico, para a
linguagem não divergir entre eles como divergia no original.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from .theme import tokens

#: Altura padrão dos gráficos do painel direito.
ALTURA = 300

#: Tooltip escuro do original: fundo quase preto, cantos arredondados.
TOOLTIP_FUNDO = "#111827"


def tema(grafico: alt.Chart, *, altura: int = ALTURA) -> alt.Chart:
    """Aplica a linguagem visual do projeto.

    Sem eixo de cor de fundo e sem grade vertical: o painel já tem superfície
    própria, e a grade horizontal basta para ler valor.
    """
    return (
        grafico.properties(height=altura)
        .configure_view(strokeWidth=0, fill=None)
        .configure_axis(
            labelFont=tokens.FONTE,
            titleFont=tokens.FONTE,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            labelColor="currentColor",
            titleColor="currentColor",
            domainColor="rgba(128,128,128,.35)",
            tickColor="rgba(128,128,128,.35)",
            gridColor="rgba(128,128,128,.18)",
        )
        .configure_axisX(grid=False)
        .configure_legend(
            labelFont=tokens.FONTE,
            titleFont=tokens.FONTE,
            labelFontSize=11,
            titleFontSize=11,
            labelColor="currentColor",
            titleColor="currentColor",
            orient="top",
            direction="horizontal",
            title=None,
        )
        .configure_title(font=tokens.FONTE, fontSize=13, color="currentColor")
    )


def sem_dado(mensagem: str) -> alt.Chart:
    """Gráfico vazio com um recado, no lugar de um painel em branco."""
    return (
        alt.Chart(pd.DataFrame({"t": [mensagem]}))
        .mark_text(font=tokens.FONTE, fontSize=13, opacity=0.55, color="gray")
        .encode(text="t:N")
        .properties(height=ALTURA)
    )


#: A série mensal vem de `_cache_ts`, que é por **notificação**, enquanto os
#: KPIs vêm de `incidence`, que é por **residência** — medido no SINAN bruto,
#: ver docs/contrato-dados.md, armadilha 7. Os totais não batem: no DF a
#: diferença chega a 36,8% em 2011. Enquanto não houver uma série mensal por
#: residência, o gráfico avisa em vez de fingir que fecha.
AVISO_NOTIFICACAO = (
    "Série por UF de notificação; os KPIs acima são por UF de residência. "
    "Os totais não fecham — ver docs/contrato-dados.md."
)


def evolucao_mensal(dados: pd.DataFrame, *, rotulo: str, cor: str) -> alt.Chart:
    """Casos por mês do ano selecionado."""
    if dados.empty:
        return sem_dado("Sem série mensal para este recorte")

    base = dados.assign(mes_rotulo=dados["mes_nome"].str.slice(0, 3).str.capitalize())
    return tema(
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=cor)
        .encode(
            x=alt.X("mes_rotulo:N", sort=list(base["mes_rotulo"]), title=None),
            y=alt.Y("valor:Q", title=rotulo),
            tooltip=[
                alt.Tooltip("mes_nome:N", title="Mês"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.0f"),
            ],
        )
    )


def evolucao_anual(dados: pd.DataFrame, *, rotulo: str, cor: str, ano: int) -> alt.Chart:
    """Série histórica anual, com o ano selecionado destacado."""
    if dados.empty:
        return sem_dado("Sem série histórica para este recorte")

    base = dados.assign(atual=dados["ano"] == ano)
    return tema(
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("ano:O", title=None),
            y=alt.Y("valor:Q", title=rotulo),
            # O ano selecionado fica opaco e os demais recuam: mantém o
            # contexto histórico sem competir com o recorte ativo.
            color=alt.value(cor),
            opacity=alt.condition(alt.datum.atual, alt.value(1.0), alt.value(0.45)),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.0f"),
            ],
        )
    )
