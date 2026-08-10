"""Mapa coroplético.

Desenhado com **pydeck**. A escolha começou no Plotly, pelo evento de clique
nativo do ``st.plotly_chart``, mas o coroplético do Plotly não dispara esse
evento — nem na versão maplibre nem na SVG. O ``GeoJsonLayer`` do deck.gl faz
*picking* por GPU e resolveu. O caminho descartado está registrado em
docs/mapa-clique.md; o código dele foi removido para não dar a impressão de
que há duas rotas mantidas.

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

#: Altura do mapa, em pixels. O painel reserva `ALTURA_MIN_MAPA`.
ALTURA = 520

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


def _rgb(cor: str) -> list[int]:
    """`#RRGGBB` para `[r, g, b]`, que é como o deck.gl espera."""
    texto = cor.lstrip("#")
    return [int(texto[i : i + 2], 16) for i in (0, 2, 4)]


#: Geometrias já convertidas para GeoJSON, por chave de recorte.
#:
#: Converter a malha custa 75 ms em Minas Gerais, e é o item mais caro de
#: montar o mapa — mais que todas as leituras de dado somadas. O trabalho é
#: idêntico a cada renderização: a geometria não muda quando o usuário troca
#: de métrica ou de ano, só as cores mudam.
#:
#: Guarda só a geometria, nunca as propriedades. Propriedade carrega cor e
#: valor, que mudam a cada interação — cachear junto serviria mapa velho.
_GEOMETRIAS: dict[str, list] = {}

#: Recortes distintos guardados. Cabe o país, as 27 UFs e folga para os
#: recortes de saúde; cada entrada custa poucos MB.
_LIMITE_GEOMETRIAS = 40


def _geometrias(camada, chave_cache: str | None) -> list | None:
    """Geometrias em GeoJSON, reaproveitadas entre renderizações.

    Sem ``chave_cache`` devolve ``None`` e o chamador segue pelo caminho
    normal — é o que os testes usam, e evita que uma chave errada sirva a
    malha de outro estado.
    """
    if chave_cache is None:
        return None
    if chave_cache not in _GEOMETRIAS:
        if len(_GEOMETRIAS) >= _LIMITE_GEOMETRIAS:
            _GEOMETRIAS.clear()
        bruto = camada[["geometry"]].__geo_interface__
        _GEOMETRIAS[chave_cache] = [f["geometry"] for f in bruto["features"]]
    return _GEOMETRIAS[chave_cache]


def _compactar(mapa_deck) -> None:
    """Faz o deck serializar sem indentação.

    O `pydeck.serialize` chama ``json.dumps(..., indent=2)``, e o
    ``st.pydeck_chart`` envia ao navegador exatamente o que ``to_json()``
    devolver. Com a geometria aninhada em listas de coordenadas, essa
    indentação é a maior parte do que trafega: em Minas Gerais, com 853
    municípios, são 2,76 MB dos quais 2,0 MB são espaço em branco.

    E não é custo só da primeira carga — as cores fazem parte do mesmo spec,
    então o mosaico inteiro volta pela rede a cada navegação e a cada troca
    de métrica.

    Substituir o método na instância é feio, mas é o único ponto de entrada:
    o Streamlit não expõe opção de serialização e o `pydeck` não parametriza
    o `indent`. Se a API interna do pydeck mudar, o `except` devolve o
    comportamento padrão — payload grande, nunca página quebrada.
    """
    try:
        import json

        from pydeck.bindings.json_tools import default_serialize

        compacto = json.dumps(
            mapa_deck,
            sort_keys=True,
            default=default_serialize,
            separators=(",", ":"),
        )
    except Exception:  # noqa: BLE001 — otimização não pode derrubar o mapa
        return

    mapa_deck.to_json = lambda: compacto


def deck(
    camada,
    valores: pd.Series,
    *,
    chave: str,
    rampa: list[str],
    rotulo_metrica: str,
    coluna_nome: str = "nome_mun",
    decimais: int = 1,
    altura: int = ALTURA,
    chave_cache: str | None = None,
):
    """Mapa em pydeck, para o drill-down por clique.

    O coroplético do Plotly não emite evento de clique — ver
    docs/mapa-clique.md. O ``GeoJsonLayer`` do deck.gl faz *picking* por GPU,
    que é o caminho que sobrou.

    Devolve ``(deck, escala)``: a escala sai junto porque o deck.gl não desenha
    legenda, e ela é montada em HTML por :func:`legenda`.
    """
    import pydeck

    colunas = list(dict.fromkeys([chave, coluna_nome if coluna_nome in camada else chave]))
    dados = camada[[*colunas, "geometry"]].copy()
    dados["valor"] = dados[chave].map(valores)

    escala = escala_quantil(dados["valor"], rampa, decimais=decimais)
    dados["classe"] = classificar(dados["valor"], escala)
    dados["cor"] = dados["classe"].map(
        lambda c: _rgb(escala.cores.get(c, SEM_DADO))
    )
    dados["exibicao"] = dados["valor"].map(
        lambda v: "—" if pd.isna(v) else _formatar(float(v), decimais)
    )
    dados["rotulo"] = dados[colunas[-1]].astype(str)

    quadro = enquadrar(tuple(camada.total_bounds))

    # A geometria vem do cache quando o chamador identifica o recorte; as
    # propriedades são sempre montadas do zero, porque carregam a cor.
    geometrias = _geometrias(camada, chave_cache)
    if geometrias is not None and len(geometrias) == len(dados):
        propriedades = dados.drop(columns="geometry").to_dict("records")
        colecao = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": g, "properties": p}
                for g, p in zip(geometrias, propriedades)
            ],
        }
    else:
        colecao = dados.__geo_interface__

    camada_geo = pydeck.Layer(
        "GeoJsonLayer",
        data=colecao,
        get_fill_color="properties.cor",
        get_line_color=[255, 255, 255, 150],
        line_width_min_pixels=0.6,
        stroked=True,
        filled=True,
        # `pickable` é o que faz o clique existir; `auto_highlight` dá o
        # retorno visual que o hover do Plotly dava de graça.
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
    )

    mapa_deck = pydeck.Deck(
        layers=[camada_geo],
        views=[pydeck.View(type="MapView", controller=False)],
        initial_view_state=pydeck.ViewState(
            latitude=quadro["center"]["lat"],
            longitude=quadro["center"]["lon"],
            zoom=quadro["zoom"],
            bearing=0,
            pitch=0,
            height=altura,
        ),
        map_provider=None,
        tooltip={
            "html": f"<b>{{rotulo}}</b><br>{rotulo_metrica}: {{exibicao}}",
            "style": {
                "backgroundColor": "rgba(17,24,39,.96)",
                "color": "#fff",
                "fontSize": "12px",
                "borderRadius": "10px",
                "padding": "6px 8px",
            },
        },
    )

    _compactar(mapa_deck)

    # Declara o mapa travado nos dois lugares do spec — mas saiba que **isto
    # sozinho não funciona no Streamlit**. O `DeckGlJsonChart` renderiza
    # `<DeckGL controller={true}>` fixo no componente React e ignora o que vem
    # no JSON (conferido no bundle: `controller:!0`). Fica aqui porque é a
    # declaração correta, vale se o mapa for renderizado fora do Streamlit, e
    # volta a valer sozinha no dia em que eles pararem de sobrescrever.
    #
    # Quem de fato trava é `componentes.script_travar_zoom`, no DOM.
    mapa_deck.controller = False

    return mapa_deck, escala


def legenda(escala: Escala, titulo: str) -> str:
    """Legenda em HTML — o deck.gl não desenha uma."""
    from html import escape

    itens = "".join(
        f'<span class="mapa-legenda-item">'
        f'<i style="background:{escape(escala.cores[r])}"></i>{escape(r)}</span>'
        for r in [*escala.rotulos, ROTULO_SEM_DADO]
        if r in escala.cores
    )
    return (
        f'<div class="mapa-legenda">'
        f'<div class="mapa-legenda-titulo">{escape(titulo)}</div>{itens}</div>'
    )


def alvo_do_clique(evento) -> str | None:
    """Chave da geografia clicada no ``st.pydeck_chart``.

    O evento traz os objetos selecionados por camada; cada objeto é a feição
    GeoJSON, então a chave está em ``properties``.
    """
    if not evento:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if not isinstance(selecao, dict):
        return None

    objetos = selecao.get("objects") or {}
    for lista in objetos.values():
        if not lista:
            continue
        props = lista[0].get("properties") if isinstance(lista[0], dict) else None
        if isinstance(props, dict):
            for campo in ("cod_mun6", "uf", "regiao"):
                if props.get(campo):
                    return str(props[campo])
    return None
