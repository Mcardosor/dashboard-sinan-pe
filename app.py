"""Dashboard SINAN — Tuberculose.

Estado da semana 2: navegação, faixa de KPIs e o recorte vivo em
``st.session_state``. Mapa e gráficos entram nas semanas 3 e 4.
"""

from __future__ import annotations

import streamlit as st

from src.data import config, geo
from src.data import kpis as calc
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack
from src.estado import RECORTES, Navegacao
from src.theme import componentes as ui

st.set_page_config(page_title=f"SINAN — {pack.TITULO}", layout="wide")

#: KPIs por linha. Um `st.columns` por linha, e não um único para todas: ao
#: empilhar no mobile, o Streamlit renderiza coluna a coluna, e um grid único
#: entregaria os cards fora da ordem do `LAYOUT_KPI`.
POR_LINHA = 3

ROTULO_RECORTE = {
    "MUN": "Municípios",
    "MACRO": "Macrorregiões",
    "MICRO": "Regiões de saúde",
}

BRASIL = "— Brasil —"
TODA_A_UF = "— toda a UF —"


@st.cache_resource
def _anos() -> list[int]:
    return leitura.anos_disponiveis(pack.DOENCA)


@st.cache_data(ttl=600, max_entries=256)
def _kpis(doenca: str, ano: int, nivel: str, uf: str | None, mun: str | None):
    return calc.calcular(Escopo(doenca, ano, nivel, uf=uf, mun=mun))


@st.cache_data(ttl=3600)
def _municipios(uf: str) -> dict[str, str]:
    """Código de 6 dígitos → nome, para o seletor e para a trilha."""
    camada = geo.municipios(uf)
    return dict(zip(camada["cod_mun6"], camada["nome_mun"]))


def _navegacao() -> Navegacao:
    if "nav" not in st.session_state:
        st.session_state.nav = Navegacao(doenca=pack.DOENCA, ano=_anos()[-2])
    return st.session_state.nav


st.markdown(ui.css_base(), unsafe_allow_html=True)

nav = _navegacao()
anos = _anos()
ufs = sorted(config.CODIGO_POR_UF)


# --- Barra lateral ---------------------------------------------------------
with st.sidebar:
    st.title(pack.TITULO)

    nav.ano = st.select_slider("Ano", options=anos, value=nav.ano)

    st.divider()

    # Enquanto o mapa não existe, estes seletores fazem o papel do clique nele.
    # Na semana 3 passam a ser espelho da navegação, não a origem dela.
    destino = st.selectbox(
        "Unidade da federação",
        [BRASIL, *ufs],
        index=0 if nav.uf is None else ufs.index(nav.uf) + 1,
    )
    if destino == BRASIL:
        if nav.nivel != "BR":
            nav.reset()
    elif destino != nav.uf:
        nav.entrar_uf(destino)

    if nav.uf:
        if nav.tem_recortes_de_saude:
            recorte = st.radio(
                "Recorte",
                RECORTES,
                format_func=ROTULO_RECORTE.get,
                index=RECORTES.index(nav.recorte),
                horizontal=True,
            )
            if recorte != nav.recorte:
                nav.definir_recorte(recorte)

        nomes = _municipios(nav.uf)
        opcoes = [TODA_A_UF, *sorted(nomes, key=lambda c: nomes[c])]
        selecionado = nav.mun if nav.mun in nomes else None
        municipio = st.selectbox(
            "Município",
            opcoes,
            index=0 if selecionado is None else opcoes.index(selecionado),
            format_func=lambda c: c if c == TODA_A_UF else nomes[c],
        )
        if municipio == TODA_A_UF:
            if nav.nivel == "MUN":
                nav.voltar()
        elif municipio != nav.mun:
            nav.entrar_municipio(municipio, nome=nomes[municipio])

    st.divider()

    coluna_voltar, coluna_reset = st.columns(2)
    coluna_voltar.button(
        "Voltar",
        use_container_width=True,
        disabled=not nav.pode_voltar,
        on_click=nav.voltar,
    )
    coluna_reset.button("Reset", use_container_width=True, on_click=nav.reset)

    st.caption(f"Escopo: {nav.trilha()}")
    st.caption(f"Métrica ativa: {pack.rotulo(nav.metrica)}")


# --- KPIs ------------------------------------------------------------------
def selecionar_metrica(chave: str) -> None:
    nav.metrica = chave


escopo = nav.escopo
atual = _kpis(pack.DOENCA, escopo.ano, escopo.nivel, escopo.uf, escopo.mun)
anterior = (
    _kpis(pack.DOENCA, escopo.ano - 1, escopo.nivel, escopo.uf, escopo.mun)
    if escopo.ano - 1 >= anos[0]
    else None
)

for inicio in range(0, len(pack.LAYOUT_KPI), POR_LINHA):
    colunas = st.columns(POR_LINHA, gap="small")
    for coluna, chave in zip(colunas, pack.LAYOUT_KPI[inicio : inicio + POR_LINHA]):
        valor = getattr(atual, chave)
        taxa = chave in pack.TAXAS
        with coluna:
            ui.kpi_clicavel(
                st,
                chave,
                pack.rotulo(chave),
                ui.formatar_decimal(valor) if taxa else ui.formatar_inteiro(valor),
                cor=pack.cor(chave),
                selecionado=(chave == nav.metrica),
                badge_delta=ui.delta(
                    valor,
                    getattr(anterior, chave) if anterior else None,
                    taxa=taxa,
                    bom_se_cai=chave in pack.BOM_SE_CAI,
                ),
                ao_clicar=selecionar_metrica,
            )

st.divider()
st.caption(
    "Mapa e gráficos entram nas semanas 3 e 4. "
    "Divergências conhecidas entre fontes: ver docs/contrato-dados.md."
)
