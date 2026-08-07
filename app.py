"""Dashboard SINAN — Tuberculose.

Estado da semana 2: navegação, faixa de KPIs e o recorte vivo em
``st.session_state``. Mapa e gráficos entram nas semanas 3 e 4.
"""

from __future__ import annotations

import streamlit as st

from src import graficos, mapa
from src.data import config, geo, recortes
from src.data import kpis as calc
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack
from src.estado import RECORTES, Navegacao
from src.theme import componentes as ui
from src.theme import marcas

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


@st.cache_data(ttl=3600, show_spinner=False)
def _camada(
    nivel: str,
    uf: str | None,
    recorte: str = "MUN",
    mun: str | None = None,
    detalhe: bool = False,
    micro: str | None = None,
):
    """Geometria a desenhar.

    Em PE o recorte pode ser macro ou região de saúde; no modo detalhe a
    camada encolhe para o município escolhido, que é o que o zoom acompanha.
    """
    if nivel == "BR":
        return geo.ufs()
    if recorte == "MACRO":
        return geo.regioes(uf, "macro")
    if recorte == "MICRO":
        return geo.regioes(uf, "micro")

    municipios = geo.municipios(uf)
    if detalhe and mun:
        return municipios[municipios["cod_mun6"] == mun]
    # Fora do detalhe, entrar por uma região de saúde restringe o mapa a ela,
    # senão o zoom volta para o estado inteiro e perde-se o contexto do drill.
    if micro:
        dentro = set(recortes.municipios_de(micro=micro, uf=uf))
        recorte_geo = municipios[municipios["cod_mun6"].isin(dentro)]
        if not recorte_geo.empty:
            return recorte_geo
    return municipios


@st.cache_data(ttl=600, max_entries=128, show_spinner=False)
def _valores_mapa(
    doenca: str, ano: int, nivel: str, uf: str | None, metrica: str, recorte: str
):
    escopo = Escopo(doenca, ano, "UF" if nivel != "BR" else "BR", uf=uf)
    if recorte in ("MACRO", "MICRO") and nivel != "BR":
        return leitura.valores_por_regiao(
            escopo, metrica, "macro" if recorte == "MACRO" else "micro"
        )
    return leitura.valores_por_geografia(escopo, metrica)


@st.cache_data(ttl=600, max_entries=256, show_spinner=False)
def _serie(doenca, ano, nivel, uf, mun, horizonte, metrica):
    escopo = Escopo(doenca, ano, nivel, uf=uf, mun=mun)
    if horizonte == "meses":
        return leitura.serie_mensal_metrica(escopo, metrica)
    return leitura.serie_anual(escopo, metrica)


@st.cache_data(ttl=600, max_entries=128, show_spinner=False)
def _serie_dupla(doenca, ano, nivel, uf, mun, horizonte):
    return leitura.serie_dupla(Escopo(doenca, ano, nivel, uf=uf, mun=mun), horizonte)


@st.cache_data(ttl=600, max_entries=128, show_spinner=False)
def _ranking(doenca: str, ano: int, nivel: str, uf: str | None, metrica: str, top_n: int):
    return leitura.ranking(Escopo(doenca, ano, nivel, uf=uf), metrica, top_n)


@st.cache_data(ttl=3600)
def _municipios(uf: str) -> dict[str, str]:
    """Código de 6 dígitos → nome, para o seletor e para a trilha."""
    camada = geo.municipios(uf)
    return dict(zip(camada["cod_mun6"], camada["nome_mun"]))


@st.cache_data(ttl=3600)
def _rotulos_busca(uf: str) -> dict[str, str]:
    """Rótulo da busca. Em PE inclui a região de saúde, como no original.

    Pernambuco tem municípios de nome parecido em regiões diferentes, e o
    sufixo é o que desempata na lista.
    """
    nomes = _municipios(uf)
    if not recortes.configurada(uf):
        return dict(nomes)

    regiao = recortes.lookup(uf).set_index("cod_mun6")["micro"].to_dict()
    return {
        codigo: f"{nome} — {regiao[codigo]}" if codigo in regiao else nome
        for codigo, nome in nomes.items()
    }


def _navegacao() -> Navegacao:
    if "nav" not in st.session_state:
        st.session_state.nav = Navegacao(doenca=pack.DOENCA, ano=_anos()[-2])
    return st.session_state.nav


st.markdown(ui.css_base(), unsafe_allow_html=True)
st.markdown(ui.css_layout(), unsafe_allow_html=True)

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
        rotulos = _rotulos_busca(nav.uf)
        opcoes = [TODA_A_UF, *sorted(nomes, key=lambda c: rotulos[c])]
        selecionado = nav.mun if nav.mun in nomes else None
        municipio = st.selectbox(
            "Buscar município",
            opcoes,
            index=0 if selecionado is None else opcoes.index(selecionado),
            format_func=lambda c: c if c == TODA_A_UF else rotulos[c],
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

    if ausentes := marcas.faltando():
        st.caption(
            "Faixa de identificação sem imagem: "
            + ", ".join(f"`{nome}`" for nome in ausentes)
            + " não vieram na entrega do projeto em R. "
            "Basta colocá-los em `data/support/`."
        )


# --- KPIs ------------------------------------------------------------------
def selecionar_metrica(chave: str) -> None:
    nav.metrica = chave


st.markdown(
    ui.faixa_intro(pack.TITULO, bandeira=marcas.bandeira(), logo=marcas.logo()),
    unsafe_allow_html=True,
)

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

# --- Linha principal e composição -----------------------------------------
# Os painéis são espaços reservados: o mapa entra na semana 3, os gráficos na
# 4 e a composição na 5. Ficam aqui para o layout ser exercitado desde já.
esquerda, direita = st.columns(2, gap="small")

with esquerda:
    # O nível do escopo diz o que está selecionado; o mapa desenha um abaixo.
    # O que o mapa desenha depende do nível e, em PE, do recorte escolhido.
    recorte = nav.recorte if nav.tem_recortes_de_saude else "MUN"
    nivel_mapa = "UF" if nav.nivel == "BR" else recorte
    valores = _valores_mapa(
        pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.metrica, recorte
    )

    if valores.empty:
        st.markdown(
            ui.painel_vazio(
                "Mapa",
                f"{pack.rotulo(nav.metrica)} ainda não é pintável no mapa",
                mapa=True,
            ),
            unsafe_allow_html=True,
        )
    else:
        # Voltar dentro do mapa, como no original: quem navega clicando não
        # deveria ter de procurar o controle na barra lateral.
        if nav.pode_voltar:
            st.button(
                "◀ Voltar",
                key="voltar-mapa",
                on_click=nav.voltar,
                help="Desfaz um passo da navegação no mapa",
            )

        camada = _camada(
            nav.nivel, nav.uf, recorte, nav.mun, nav.detalhe, nav.micro
        )
        chave = {"UF": "uf", "MACRO": "regiao", "MICRO": "regiao"}.get(
            nivel_mapa, "cod_mun6"
        )
        desenho, escala = mapa.deck(
            camada,
            valores,
            chave=chave,
            rampa=pack.rampa_mapa(nav.metrica),
            rotulo_metrica=pack.rotulo(nav.metrica),
            coluna_nome="nome_mun" if chave == "cod_mun6" else chave,
            decimais=0 if nav.metrica in ("casos", "obitos", "pop") else 1,
        )

        # pydeck, e não Plotly: o coroplético do Plotly não emite evento de
        # clique. Ver docs/mapa-clique.md. A chave inclui o recorte para o
        # Streamlit recriar o widget ao mudar de nível — senão a seleção
        # anterior redispara a cada rerun e prende a navegação num laço.
        evento = st.pydeck_chart(
            desenho,
            use_container_width=True,
            height=mapa.ALTURA,
            key=(
                f"mapa-{nav.nivel}-{nav.uf or 'BR'}-{recorte}-{nav.mun or '-'}"
                f"-{'det' if nav.detalhe else 'geral'}-{nav.ano}-{nav.metrica}"
            ),
            on_select="rerun",
            selection_mode="single-object",
        )

        st.markdown(
            mapa.legenda(escala, pack.rotulo(nav.metrica)), unsafe_allow_html=True
        )

        if nav.nivel == "MUN" and not nav.detalhe:
            st.caption("Clique de novo no município para abrir o detalhe.")
        elif nav.detalhe:
            st.caption(f"Detalhe de {nav.nome_mun or nav.mun}.")

        if alvo := mapa.alvo_do_clique(evento):
            if nivel_mapa == "UF" and alvo != nav.uf:
                nav.entrar_uf(alvo)
                st.rerun()
            elif nivel_mapa == "MACRO" and alvo != nav.macro:
                # Clicar numa macrorregião abre as regiões de saúde dela.
                nav.entrar_macro(alvo)
                st.rerun()
            elif nivel_mapa == "MICRO" and alvo != nav.micro:
                # Clicar numa região de saúde abre os municípios dela.
                nav.entrar_micro(alvo)
                st.rerun()
            elif nivel_mapa == "MUN":
                nomes = _municipios(nav.uf)
                if alvo == nav.mun and not nav.detalhe:
                    # Clicar de novo no município já selecionado abre o
                    # detalhe, que é como o original entra nesse modo.
                    nav.abrir_detalhe()
                    st.rerun()
                elif alvo != nav.mun and alvo in nomes:
                    nav.entrar_municipio(alvo, nome=nomes[alvo])
                    st.rerun()

with direita:
    controle_h, controle_d = st.columns([2, 1])
    horizonte = controle_h.radio(
        "Evolução temporal",
        ["meses", "anos"],
        format_func=lambda h: "Meses do ano" if h == "meses" else "Todos os anos",
        horizontal=True,
        key="horizonte",
    )
    # Casos e incidência juntos é o gráfico que o original mostra para
    # tuberculose. Fica como opção, não como padrão, porque só faz sentido
    # para essas duas métricas.
    duplo = controle_d.toggle("Casos + incidência", key="serie_dupla")

    if duplo:
        serie = _serie_dupla(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun, horizonte)
        figura_serie = graficos.evolucao_dupla(
            serie,
            cor_barra=pack.cor("casos"),
            cor_linha=pack.cor("incid"),
            eixo_x="mes_nome:N" if horizonte == "meses" else "ano:O",
        )
    else:
        serie = _serie(
            pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun, horizonte, nav.metrica
        )
        rotulo = pack.rotulo(nav.metrica)
        if serie.empty:
            figura_serie = graficos.sem_dado(
                f"{rotulo} ainda não tem série temporal"
            )
        elif horizonte == "meses":
            figura_serie = graficos.evolucao_mensal(
                serie, rotulo=rotulo, cor=pack.cor(nav.metrica)
            )
        else:
            figura_serie = graficos.evolucao_anual(
                serie, rotulo=rotulo, cor=pack.cor(nav.metrica), ano=nav.ano
            )

    st.altair_chart(figura_serie, use_container_width=True)

    # A série mensal vem por notificação e os KPIs por residência — ver
    # docs/contrato-dados.md, armadilha 7. Avisar é melhor que deixar o
    # usuário descobrir somando as barras.
    if horizonte == "meses":
        st.caption(graficos.AVISO_NOTIFICACAO)

    st.divider()

    # O ranking mostra o nível abaixo do escopo, igual ao mapa: no Brasil as
    # UFs, numa UF os municípios dela.
    alvo = "UFs" if nav.nivel == "BR" else f"municípios de {nav.uf}"
    st.caption(f"Ranking — {alvo}, por {pack.rotulo(nav.metrica).lower()}")

    top_n = st.slider("Quantos exibir", 5, 30, 15, step=5, key="top_n")
    tabela = _ranking(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.metrica, top_n)

    import altair as alt

    escolha = alt.selection_point(name="barra", fields=["chave"], on="click")
    evento_rank = st.altair_chart(
        graficos.ranking(
            tabela,
            rotulo=pack.rotulo(nav.metrica),
            cor=pack.cor(nav.metrica),
            selecao=escolha,
        ),
        use_container_width=True,
        on_select="rerun",
        key=f"rank-{nav.nivel}-{nav.uf or 'BR'}-{nav.ano}-{nav.metrica}-{top_n}",
    )

    if clicado := graficos.alvo_do_clique(evento_rank, "barra"):
        # Clicar numa barra navega o mapa — o ranking responde a mesma
        # máquina de estados, não tem navegação própria.
        if nav.nivel == "BR" and clicado != nav.uf:
            nav.entrar_uf(clicado)
            st.rerun()
        elif nav.nivel != "BR" and clicado != nav.mun:
            nomes = _municipios(nav.uf)
            if clicado in nomes:
                nav.entrar_municipio(clicado, nome=nomes[clicado])
                st.rerun()

    st.markdown(
        ui.painel_vazio("Pirâmide etária", "Entra ainda esta semana"),
        unsafe_allow_html=True,
    )

st.markdown(
    ui.painel_vazio("Composição por variável do SINAN", "Entra na semana 5"),
    unsafe_allow_html=True,
)

st.caption(
    "Divergências conhecidas entre fontes de dados: ver docs/contrato-dados.md."
)
