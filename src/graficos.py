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


def ranking(dados: pd.DataFrame, *, rotulo: str, cor: str, selecao: alt.Parameter) -> alt.Chart:
    """Barras horizontais das maiores geografias, clicáveis.

    Horizontal e não vertical: nome de município não cabe num eixo x sem
    rotacionar, e rótulo rotacionado é mais difícil de ler que uma barra a
    mais de altura.
    """
    if dados.empty:
        return sem_dado("Sem dados para ranquear neste recorte")

    return tema(
        alt.Chart(dados)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            y=alt.Y("nome:N", sort="-x", title=None),
            x=alt.X("valor:Q", title=rotulo),
            color=alt.value(cor),
            # O item sob o cursor destaca; os demais recuam. Dá retorno de
            # que a barra é clicável sem precisar de instrução escrita.
            opacity=alt.condition(selecao, alt.value(1.0), alt.value(0.55)),
            tooltip=[
                alt.Tooltip("nome:N", title="Local"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.1f"),
            ],
        )
        .add_params(selecao),
        altura=max(180, 22 * len(dados)),
    )


def alvo_do_clique(evento, nome_selecao: str = "barra") -> str | None:
    """Chave da barra clicada no ``st.altair_chart``.

    Tolerante ao formato, pelo mesmo motivo do mapa: o payload é detalhe
    interno do Streamlit e já mudou entre versões. Vindo algo inesperado, o
    gráfico apenas não navega, em vez de derrubar a página.
    """
    if not evento:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if not isinstance(selecao, dict):
        return None

    itens = selecao.get(nome_selecao)
    if not itens:
        return None

    primeiro = itens[0]
    if not isinstance(primeiro, dict):
        return None
    valor = primeiro.get("chave")
    return str(valor) if valor not in (None, "") else None


def evolucao_dupla(
    dados: pd.DataFrame, *, cor_barra: str, cor_linha: str, eixo_x: str, titulo_x: str | None = None
) -> alt.Chart:
    """Contagem em barras e taxa em linha, com eixos independentes.

    O original da tuberculose mostra casos e incidência no mesmo gráfico. Duas
    grandezas de ordem diferente — milhares contra dezenas — precisam de eixos
    próprios: num eixo só, a linha da taxa vira uma reta colada no zero.

    O eixo da taxa fica à direita e na cor da linha, para não haver dúvida de
    qual escala pertence a qual série.
    """
    if dados.empty:
        return sem_dado("Sem série para este recorte")

    base = alt.Chart(dados).encode(
        x=alt.X(eixo_x, sort=list(dados[eixo_x.split(":")[0]]), title=titulo_x)
    )

    barras = base.mark_bar(
        cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=cor_barra, opacity=0.85
    ).encode(
        y=alt.Y("casos:Q", title="Casos novos", axis=alt.Axis(titleColor=cor_barra)),
        tooltip=[
            alt.Tooltip(eixo_x, title="Período"),
            alt.Tooltip("casos:Q", title="Casos novos", format=",.0f"),
            alt.Tooltip("incid:Q", title="Incidência", format=",.1f"),
        ],
    )

    linha = base.mark_line(color=cor_linha, strokeWidth=2, point=True).encode(
        y=alt.Y(
            "incid:Q",
            title="Incidência (por 100 mil hab.)",
            axis=alt.Axis(titleColor=cor_linha),
        )
    )

    return tema(alt.layer(barras, linha).resolve_scale(y="independent"))
