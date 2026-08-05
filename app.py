"""Dashboard SINAN — Tuberculose.

Esqueleto da semana 1: sidebar, faixa de KPIs e o recorte em `session_state`.
Mapa e gráficos entram nas semanas 3 e 4.
"""

from __future__ import annotations

import streamlit as st

from src.data import kpis as calc
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack
from src.theme import componentes as ui

st.set_page_config(page_title=f"SINAN — {pack.TITULO}", layout="wide")


@st.cache_resource
def _anos() -> list[int]:
    return leitura.anos_disponiveis(pack.DOENCA)


@st.cache_data(ttl=600, max_entries=256)
def _kpis(doenca: str, ano: int, nivel: str, uf: str | None, mun: str | None):
    return calc.calcular(Escopo(doenca, ano, nivel, uf=uf, mun=mun))


def _ufs() -> list[str]:
    from src.data import config

    return sorted(config.CODIGO_POR_UF)


st.markdown(ui.css_base(), unsafe_allow_html=True)

# A métrica ativa vive no estado da sessão; clicar num card a substitui.
# Precisa existir antes da sidebar, que já a exibe.
st.session_state.setdefault("metrica", pack.LAYOUT_KPI[0])


def selecionar_metrica(chave: str) -> None:
    st.session_state.metrica = chave


with st.sidebar:
    st.title(pack.TITULO)
    anos = _anos()
    ano = st.select_slider("Ano", options=anos, value=anos[-2])

    nivel = st.radio("Nível", ["BR", "UF", "MUN"], horizontal=True)
    uf = st.selectbox("UF", _ufs(), index=_ufs().index("PE")) if nivel in ("UF", "MUN") else None
    mun = st.text_input("Município (código IBGE)", "261160") if nivel == "MUN" else None

    escopo_txt = {"BR": "Brasil", "UF": f"UF {uf}", "MUN": f"Município {mun}"}[nivel]
    st.caption(f"Escopo: {escopo_txt} • Ano: {ano}")
    st.caption(f"Métrica ativa: {pack.rotulo(st.session_state.metrica)}")

atual = _kpis(pack.DOENCA, ano, nivel, uf, mun)
anterior = _kpis(pack.DOENCA, ano - 1, nivel, uf, mun) if ano - 1 >= anos[0] else None

#: KPIs por linha. Um `st.columns` por linha, e não um único para todos: ao
#: empilhar no mobile, o Streamlit renderiza coluna a coluna, e um grid único
#: entregaria os cards fora da ordem do `LAYOUT_KPI`.
POR_LINHA = 3

for inicio in range(0, len(pack.LAYOUT_KPI), POR_LINHA):
    linha = pack.LAYOUT_KPI[inicio : inicio + POR_LINHA]
    colunas = st.columns(POR_LINHA, gap="small")
    for coluna, chave in zip(colunas, linha):
        valor = getattr(atual, chave)
        taxa = chave in pack.TAXAS
        with coluna:
            ui.kpi_clicavel(
                st,
                chave,
                pack.rotulo(chave),
                ui.formatar_decimal(valor) if taxa else ui.formatar_inteiro(valor),
                cor=pack.cor(chave),
                selecionado=(chave == st.session_state.metrica),
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
