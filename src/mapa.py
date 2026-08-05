"""Mapa coroplético.

Plotly, por duas razões: ``st.plotly_chart`` tem evento de clique nativo
(``on_select``), o que dispensa um componente de terceiros para o drill-down;
e o dashboard demográfico da casa já usa Plotly, o que mantém a mesma
linguagem visual.

A escala é por **quantil**, como no original. Em dados epidemiológicos poucos
municípios concentram o volume, e uma escala linear achata todo o resto numa
cor só.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Número de classes da escala. Valor do original.
CLASSES = 6

#: Cor de quem não tem dado. Precisa ser distinguível de qualquer tom da rampa.
SEM_DADO = "#F3F4F6"

#: Altura da figura, em pixels. O painel reserva `ALTURA_MIN_MAPA`; a legenda
#: horizontal ocupa a faixa de baixo e precisa caber junto, senão é cortada.
ALTURA = 520
ALTURA_LEGENDA = 74

ROTULO_SEM_DADO = "sem dado"


@dataclass(frozen=True, slots=True)
class Escala:
    """Classes de uma escala por quantil."""

    cortes: list[float]
    rotulos: list[str]
    cores: dict[str, str]

    @property
    def classes(self) -> int:
        return len(self.rotulos)


def _formatar(valor: float, decimais: int) -> str:
    texto = f"{valor:,.{decimais}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def escala_quantil(
    valores: pd.Series, rampa: list[str], classes: int = CLASSES, decimais: int = 1
) -> Escala:
    """Divide os valores em classes de igual frequência.

    Quantis repetidos são colapsados: quando mais da metade dos municípios tem
    zero caso — o que é comum em recortes pequenos — vários cortes caem no
    mesmo número e produziriam classes vazias.
    """
    limpos = pd.to_numeric(valores, errors="coerce").dropna()
    limpos = limpos[np.isfinite(limpos)]
    if limpos.empty:
        return Escala(cortes=[], rotulos=[], cores={ROTULO_SEM_DADO: SEM_DADO})

    cortes = sorted(set(np.quantile(limpos, np.linspace(0, 1, classes + 1))))
    if len(cortes) < 2:
        unico = float(cortes[0])
        rotulo = _formatar(unico, decimais)
        return Escala(
            cortes=[unico, unico],
            rotulos=[rotulo],
            cores={rotulo: rampa[len(rampa) // 2], ROTULO_SEM_DADO: SEM_DADO},
        )

    # A rampa tem 7 tons; com menos classes, pega tons distribuídos nela.
    usadas = len(cortes) - 1
    indices = np.linspace(0, len(rampa) - 1, usadas).round().astype(int)
    tons = [rampa[i] for i in indices]

    rotulos = [
        f"{_formatar(cortes[i], decimais)} a {_formatar(cortes[i + 1], decimais)}"
        for i in range(usadas)
    ]
    cores = dict(zip(rotulos, tons))
    cores[ROTULO_SEM_DADO] = SEM_DADO
    return Escala(cortes=[float(c) for c in cortes], rotulos=rotulos, cores=cores)


def classificar(valores: pd.Series, escala: Escala) -> pd.Series:
    """Rótulo da classe de cada valor. Ausente e não-finito viram "sem dado"."""
    numeros = pd.to_numeric(valores, errors="coerce")
    if not escala.rotulos:
        return pd.Series([ROTULO_SEM_DADO] * len(numeros), index=numeros.index)

    # `cut` não inclui o limite inferior da primeira classe; `include_lowest`
    # resolve, e o `duplicates` cobre cortes colapsados.
    faixas = pd.cut(
        numeros,
        bins=escala.cortes,
        labels=escala.rotulos,
        include_lowest=True,
        duplicates="drop",
    )
    return faixas.astype(object).where(faixas.notna(), ROTULO_SEM_DADO)


def enquadrar(limites: tuple[float, float, float, float]) -> dict:
    """Centro e zoom para o bounding box caber na tela.

    O Plotly não tem `fitBounds`; o zoom é derivado da maior dimensão do bbox
    contra a resolução de tela típica do painel.
    """
    xmin, ymin, xmax, ymax = limites
    centro = {"lat": (ymin + ymax) / 2, "lon": (xmin + xmax) / 2}

    extensao = max(xmax - xmin, ymax - ymin)
    if extensao <= 0:
        return {"center": centro, "zoom": 9.0}

    # 360° cabem no zoom 0; cada nível dobra a escala. O -0.4 é folga para a
    # geometria não encostar na borda do painel.
    zoom = float(np.log2(360 / extensao) - 0.4)
    return {"center": centro, "zoom": max(2.0, min(zoom, 11.0))}


def figura(
    camada,
    geojson: dict,
    valores: pd.Series,
    *,
    chave: str,
    rampa: list[str],
    rotulo_metrica: str,
    coluna_nome: str = "nome_mun",
    decimais: int = 1,
    altura: int = ALTURA,
):
    """Coroplético de uma camada, colorido por classe de quantil.

    ``valores`` é indexado pela mesma chave da camada. Quem não aparece nele
    entra como "sem dado" — é o caso de municípios criados depois do último
    ano com dado, por exemplo.
    """
    import plotly.express as px

    # `dict.fromkeys` remove repetição preservando a ordem: no nível de UF a
    # chave e a coluna de nome são ambas `uf`, e selecionar a mesma coluna
    # duas vezes faria `dados[chave]` devolver um DataFrame em vez de Série.
    colunas = list(dict.fromkeys([chave, coluna_nome if coluna_nome in camada else chave]))
    dados = pd.DataFrame(camada[colunas]).copy()
    dados["valor"] = dados[chave].map(valores)

    escala = escala_quantil(dados["valor"], rampa, decimais=decimais)
    dados["classe"] = classificar(dados["valor"], escala)
    dados["exibicao"] = dados["valor"].map(
        lambda v: "—" if pd.isna(v) else _formatar(float(v), decimais)
    )

    ordem = [*escala.rotulos, ROTULO_SEM_DADO]
    nome = coluna_nome if coluna_nome in dados else chave

    fig = px.choropleth_map(
        dados,
        geojson=geojson,
        locations=chave,
        featureidkey=f"properties.{chave}",
        color="classe",
        color_discrete_map=escala.cores,
        category_orders={"classe": ordem},
        custom_data=[nome, "exibicao"],
        opacity=0.85,
        **enquadrar(tuple(camada.total_bounds)),
    )

    fig.update_traces(
        marker_line_width=0.4,
        marker_line_color="rgba(255,255,255,.55)",
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            + rotulo_metrica
            + ": %{customdata[1]}<extra></extra>"
        ),
    )
    fig.update_layout(
        map_style="white-bg",
        height=altura,
        # A margem inferior reserva a faixa da legenda dentro da própria
        # figura; ancorá-la em `y` negativo a jogaria para fora do recorte.
        margin={"r": 0, "t": 0, "l": 0, "b": ALTURA_LEGENDA},
        legend={
            "title": {"text": rotulo_metrica, "font": {"size": 12}},
            "orientation": "h",
            "yanchor": "top",
            "y": 0,
            "yref": "paper",
            "x": 0,
            "font": {"size": 11},
            "itemsizing": "constant",
            "bgcolor": "rgba(0,0,0,0)",
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # Sem isso, o Plotly herda a fonte dele e destoa do resto da página.
        font={"family": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"},
    )
    return fig


def alvo_do_clique(evento) -> str | None:
    """Extrai a geografia clicada do evento de seleção do ``st.plotly_chart``.

    O ``on_select`` devolve os pontos selecionados, e como a figura usa
    ``locations=chave``, o campo ``location`` já traz a chave da geografia —
    sigla de UF ou código de município de 6 dígitos.

    Tolerante de propósito: o formato do evento é detalhe interno do Streamlit
    e já mudou entre versões. Se vier algo inesperado, devolve ``None`` e o
    mapa apenas não navega, em vez de derrubar a página.
    """
    if not evento:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if not selecao:
        return None

    pontos = selecao.get("points") if isinstance(selecao, dict) else None
    if not pontos:
        return None

    primeiro = pontos[0]
    if not isinstance(primeiro, dict):
        return None

    for campo in ("location", "hovertext", "label", "id"):
        valor = primeiro.get(campo)
        if valor not in (None, ""):
            return str(valor)
    return None
