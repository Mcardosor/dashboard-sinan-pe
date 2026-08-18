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
from src import resiliencia
from src.estado import RECORTES, Navegacao, nivel_agregado
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


#: Validade do cache de dados, em segundos.
#:
#: Os parquets são imutáveis entre publicações — mudam quando alguém troca os
#: arquivos e reinicia o serviço, e o reinício já limpa o cache. O TTL de 10
#: minutos que estava aqui só produzia releitura periódica sem motivo.
#:
#: Não é infinito de propósito: se alguém trocar os arquivos **sem** reiniciar,
#: um dia é o limite de quanto o painel serve dado velho. É a única razão de o
#: número não ser `None`.
TTL_DADOS = 24 * 3600

#: Quantos resultados guardar por leitor.
#:
#: A cardinalidade possível é grande demais para caber — 8.064 combinações só
#: para o mapa, 89.568 para os KPIs —, então isto é limite de memória, não de
#: cobertura. Os números saem do tamanho medido de cada resultado:
#: KPI ocupa 0,1 KB, série e ranking cerca de 2 KB, valores do mapa até 31 KB
#: em Minas Gerais.
ENTRADAS_LEVES = 1024   # ~0,1 KB cada: KPIs
ENTRADAS_MEDIAS = 512   # ~2 KB cada: séries, ranking, pirâmide, composição
ENTRADAS_PESADAS = 256  # até 31 KB: valores do mapa

#: Camadas geométricas: de 122 KB (as 27 UFs) a 359 KB (municípios de MG).
#: Estava **sem limite** — 27 UFs mais os recortes de saúde e o modo detalhe
#: cresciam sem teto. Com 48, o pior caso fica em torno de 17 MB.
#:
ENTRADAS_GEOMETRIA = 48

#: Altura da primeira linha da grade. O mapa manda: é ele que tem altura fixa,
#: e o painel ao lado precisa fechar no mesmo ponto. Sem isto a coluna do mapa
#: ficava com mais de 1.000px de vazio embaixo.
#:
#: Desconta a barra de controles que fica acima do gráfico, para os dois
#: painéis terminarem juntos e não só começarem juntos. Os 46px são o quanto
#: essa barra excede o cabeçalho de uma linha do mapa, medido no navegador;
#: `tests/test_app.py` confere que o valor deriva de `mapa.ALTURA`, e a
#: conferência final é olhar se os dois fecham no mesmo pixel.
ALTURA_LINHA_1 = mapa.ALTURA - 46

#: Altura da série temporal, agora que ela ocupa a largura inteira.
#:
#: Antes a série dividia a linha 1 com o mapa e herdava os 520px dele — 12
#: barras esticadas em meio metro de altura, que não acrescenta informação
#: nenhuma, só tinta. O ranking trocou de lugar com ela porque as duas
#: precisam de eixos opostos: 12 meses pedem **largura**, e 15 barras
#: horizontais empilhadas pedem **altura**. Estavam nos slots trocados.
ALTURA_SERIE = 280

@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_LEVES)
def _kpis(doenca: str, ano: int, nivel: str, uf: str | None, mun: str | None):
    return calc.calcular(Escopo(doenca, ano, nivel, uf=uf, mun=mun))


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_GEOMETRIA, show_spinner=False)
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


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_GEOMETRIA, show_spinner=False)
def _geojson(nivel, uf, recorte, mun, detalhe, micro):
    """Geometria da camada já em GeoJSON.

    Recebe exatamente os argumentos de `_camada` para as duas terem a **mesma
    identidade**. Antes a chave era remontada à mão como string na página:
    mudar a assinatura de `_camada` e esquecer a string serviria a malha
    errada, em silêncio.
    """
    return mapa.geometrias_geojson(_camada(nivel, uf, recorte, mun, detalhe, micro))


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_PESADAS, show_spinner=False)
def _valores_mapa(
    doenca: str, ano: int, nivel: str, uf: str | None, metrica: str, recorte: str
):
    escopo = Escopo(doenca, ano, nivel_agregado(nivel), uf=uf)
    if recorte in ("MACRO", "MICRO") and nivel != "BR":
        return leitura.valores_por_regiao(
            escopo, metrica, "macro" if recorte == "MACRO" else "micro"
        )
    return leitura.valores_por_geografia(escopo, metrica)


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _serie(doenca, ano, nivel, uf, mun, horizonte, metrica):
    escopo = Escopo(doenca, ano, nivel, uf=uf, mun=mun)
    if horizonte == "meses":
        return leitura.serie_mensal_metrica(escopo, metrica)
    return leitura.serie_anual(escopo, metrica)


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _serie_dupla(doenca, ano, nivel, uf, mun, horizonte):
    return leitura.serie_dupla(Escopo(doenca, ano, nivel, uf=uf, mun=mun), horizonte)


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _ranking(doenca: str, ano: int, nivel: str, uf: str | None, metrica: str, top_n: int):
    return leitura.ranking(Escopo(doenca, ano, nivel_agregado(nivel), uf=uf), metrica, top_n)


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _indicadores_programa(doenca, ano, nivel, uf, mun):
    return leitura.indicadores_programa(
        Escopo(doenca, ano, nivel, uf=uf, mun=mun), pack.INDICADORES_PROGRAMA
    )


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _composicao(doenca, ano, nivel, uf, mun, variavel):
    return leitura.composicao(Escopo(doenca, ano, nivel, uf=uf, mun=mun), variavel)


@st.cache_data(ttl=TTL_DADOS, max_entries=ENTRADAS_MEDIAS, show_spinner=False)
def _piramide(doenca, ano, nivel, uf, mun, tipo):
    return leitura.piramide_completa(Escopo(doenca, ano, nivel, uf=uf, mun=mun), tipo)


@st.cache_data(ttl=TTL_DADOS)
def _meses_com_dado(doenca: str, ano: int) -> int:
    return leitura.meses_com_dado(doenca, ano)


@st.cache_data(ttl=TTL_DADOS)
def _municipios(uf: str) -> dict[str, str]:
    """Código de 6 dígitos → nome, para o seletor e para a trilha."""
    camada = geo.municipios(uf)
    return dict(zip(camada["cod_mun6"], camada["nome_mun"]))


@st.cache_data(ttl=TTL_DADOS)
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


#: Para nomear o último mês com dado no aviso de ano incompleto.
MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

st.markdown(ui.css_base(), unsafe_allow_html=True)
st.markdown(ui.css_layout(), unsafe_allow_html=True)

# Precisa ser `components.v1.html`, não `st.markdown`: o markdown remove
# `<script>`. Altura zero — o iframe existe só para rodar o script.
st.components.v1.html(ui.script_travar_zoom(), height=0)


nav = _navegacao()
anos = _anos()
ufs = sorted(config.CODIGO_POR_UF)


# --- Barra lateral ---------------------------------------------------------
with st.sidebar:
    st.title(pack.TITULO)

    # `key` e **sem** `value`: o Streamlit é o dono do valor do slider.
    #
    # Com `value=nav.ano` era preciso arrastar duas vezes para o ano mudar.
    # Widget sem `key` tem identidade derivada dos argumentos, então devolver
    # o valor novo em `value` no rerun seguinte recria o widget e descarta a
    # interação que acabou de acontecer; só a segunda pegava.
    #
    # Só o slider mexe no ano — `nav.reset()` preserva por padrão, e o clique
    # no mapa muda geografia, não tempo. Sem ninguém mais escrevendo, o estado
    # do widget pode ser a fonte da verdade, e `nav.ano` vira reflexo dele.
    #
    # Os seletores de UF e de município abaixo continuam com `index` dinâmico
    # de propósito: aqueles são espelho da navegação e precisam acompanhar o
    # clique no mapa, que é outro dono do mesmo estado.
    if "ano" not in st.session_state:
        st.session_state.ano = nav.ano
    nav.ano = st.select_slider("Ano", options=anos, key="ano")

    # Ano em andamento precisa dizer que está em andamento. Sem isto o painel
    # mente por omissão: em 2025 a incidência aparece como 0,83 contra 40,42
    # em 2024, e a leitura natural é queda, não ano pela metade.
    if (meses := _meses_com_dado(pack.DOENCA, nav.ano)) < 12:
        st.warning(
            f"**{nav.ano} está incompleto** — dado até {MESES[meses - 1] if meses else '—'}"
            f" ({meses} de 12 meses). Não compare o total com anos fechados.",
            icon=":material/schedule:",
        )

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

    # Reservado agora, preenchido depois do rádio que define a métrica.
    #
    # Quem escolhe a métrica é um controle dentro do painel do mapa, umas 50
    # linhas abaixo. Escrevendo a legenda aqui, ela mostrava o valor da
    # interação **anterior**: trocar para "Casos novos" deixava a barra
    # dizendo "Incidência" até o clique seguinte.
    #
    # `st.empty()` guarda o lugar na barra lateral e aceita conteúdo mais
    # tarde no script, então a posição visual não muda e o valor deixa de
    # atrasar. Mover o rádio para cá resolveria também, mas separaria o
    # controle do mapa que ele comanda.
    espaco_metrica = st.empty()


# --- KPIs ------------------------------------------------------------------
# O escopo vai na faixa, e não só na barra lateral: recolhida — que é como o
# painel é projetado — não sobrava nada na tela dizendo de que ano e de que
# território são os números.
#
# Montado aqui, e não com `nav.trilha()`, porque a trilha é o breadcrumb da
# barra lateral e traz "Ano: " por extenso mais os níveis de recorte. Na faixa
# cabe o resumo; o detalhe continua ao lado.
_local = (
    "Brasil" if nav.nivel == "BR"
    else (nav.nome_mun or config.NOME_POR_UF.get(nav.uf, nav.uf))
)
st.markdown(
    ui.faixa_intro(
        pack.TITULO,
        escopo=f"{_local} · {nav.ano} · Sinan/MS",
        cor=pack.cor("primary"),
    ),
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
        coluna.markdown(
            ui.kpi_card(
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
                ajuda=pack.descricao(chave),
            ),
            unsafe_allow_html=True,
        )

# --- Linha principal e composição -----------------------------------------
# Os painéis são espaços reservados: o mapa entra na semana 3, os gráficos na
# 4 e a composição na 5. Ficam aqui para o layout ser exercitado desde já.
esquerda, direita = st.columns(2, gap="small")

with esquerda, resiliencia.painel("Mapa"):
    # O nível do escopo diz o que está selecionado; o mapa desenha um abaixo.
    # O que o mapa desenha depende do nível e, em PE, do recorte escolhido.
    recorte = nav.recorte if nav.tem_recortes_de_saude else "MUN"
    nivel_mapa = "UF" if nav.nivel == "BR" else recorte

    # Cabeçalho, que também alinha as duas colunas: a da direita gasta 84px
    # com o rádio de horizonte e o toggle, e sem isto o mapa começava no topo
    # enquanto a série começava bem abaixo.
    # A métrica do mapa é escolhida aqui, e não clicando no card. O card não
    # avisava que era clicável — parecia indicador porque é indicador —, e a
    # interação custou quatro rodadas de conserto. Este controle é nativo:
    # teclado, foco e `aria-checked` vêm de graça.
    nav.metrica = st.radio(
        "Métrica do mapa",
        pack.METRICAS_MAPA,
        index=pack.METRICAS_MAPA.index(nav.metrica)
        if nav.metrica in pack.METRICAS_MAPA
        else 0,
        format_func=pack.rotulo,
        horizontal=True,
        key="metrica_mapa",
        help="Define o que o mapa pinta e o que o ranking ordena.",
    )
    espaco_metrica.caption(f"Métrica ativa: {pack.rotulo(nav.metrica)}")

    st.markdown(
        ui.titulo_painel(
        "Mapa — "
        + {
            "UF": "unidades da federação" if nav.nivel == "BR" else f"municípios de {nav.uf}",
            "MACRO": f"macrorregiões de {nav.uf}",
            "MICRO": f"regiões de saúde de {nav.uf}",
            "MUN": f"municípios de {nav.uf}",
        }[nivel_mapa]
        ),
        unsafe_allow_html=True,
    )
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
        #
        # `disabled` e não `if`: escondendo o botão, entrar numa UF empurrava o
        # mapa uns 48px para baixo — exatamente onde o usuário acabara de
        # clicar, e no instante seguinte ao clique. A barra lateral já fazia
        # assim; era o mapa que destoava.
        st.button(
            "◀ Voltar",
            key="voltar-mapa",
            disabled=not nav.pode_voltar,
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
            # Casa decimal só em taxa. A regra sai de `pack.TAXAS`, a mesma
            # que formata os KPIs, e não de uma lista de contagens escrita à
            # mão aqui — `cura` tinha ficado de fora dela e o mapa exibia
            # "13.315,0 curas", meia pessoa inclusa. Invertendo a pergunta,
            # métrica nova nasce como contagem até ser declarada taxa.
            decimais=1 if nav.metrica in pack.TAXAS else 0,
            geometrias=_geojson(
                nav.nivel, nav.uf, recorte, nav.mun, nav.detalhe, nav.micro
            ),
            # Rótulo de valor só onde ele cabe. Com 27 UFs o mapa fica como o
            # do boletim do MS, legível em captura de tela e sem depender de
            # hover — que não existe em toque. Nos 5.570 municípios, ou nas
            # centenas de um estado, os rótulos se sobrepõem e viram mancha.
            rotulos_valor=(chave == "uf"),
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


@st.fragment
def _painel_ranking() -> None:
    """Ranking, isolado num fragmento.

    O `top_n` é local: mudar quantas posições aparecem não altera mapa, série
    nem pirâmide. Sem o fragmento, arrastar esse slider reconstruía a página
    inteira e reenviava o mapa — 0,19 MB no Brasil, 0,70 MB em Minas Gerais.

    **O clique numa barra é o oposto e por isso usa `scope="app"`.** Dentro de
    um fragmento o `st.rerun()` padrão recarrega só o fragmento, e a navegação
    morreria em silêncio: a barra ficaria destacada, o mapa continuaria no
    recorte antigo e ninguém veria erro nenhum.
    """
    with resiliencia.painel("Ranking"):

        # O ranking mostra o nível abaixo do escopo, igual ao mapa: no Brasil as
        # UFs, numa UF os municípios dela.
        alvo = "UFs" if nav.nivel == "BR" else f"municípios de {nav.uf}"
        st.markdown(
            ui.titulo_painel(f"Ranking — {alvo}, por {pack.rotulo(nav.metrica).lower()}"),
            unsafe_allow_html=True,
        )

        top_n = st.slider(
        "Quantos exibir", 5, 30, 15, step=5, key="top_n",
        help="Quantas posições do ranking aparecem, da maior para a menor.",
    )
        tabela = _ranking(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.metrica, top_n)

        import altair as alt

        escolha = alt.selection_point(name="barra", fields=["chave"], on="click")
        evento_rank = st.altair_chart(
            graficos.ranking(
                tabela,
                rotulo=pack.rotulo(nav.metrica),
                cor=pack.cor(nav.metrica),
                selecao=escolha,
                altura=ALTURA_LINHA_1,
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
                st.rerun(scope="app")
            elif nav.nivel != "BR" and clicado != nav.mun:
                nomes = _municipios(nav.uf)
                if clicado in nomes:
                    nav.entrar_municipio(clicado, nome=nomes[clicado])
                    st.rerun(scope="app")


with direita:
    _painel_ranking()



st.divider()

@st.fragment
def _painel_evolucao() -> None:
    """Evolução temporal, isolada num fragmento.

    Os dois controles daqui — horizonte e casos+incidência — não saem deste
    painel. Antes, alternar entre "meses do ano" e "todos os anos" redesenhava
    o mapa, o ranking, a pirâmide e a composição junto.

    Não há navegação aqui, então nenhum `st.rerun` precisa escapar do escopo.
    """
    with resiliencia.painel("Evolução temporal"):
        # 3 para 2, e não 2 para 1: com um terço da largura o rótulo do
        # toggle quebrava em duas linhas e desalinhava a barra.
        controle_h, controle_d = st.columns([3, 2])
        horizonte = controle_h.radio(
            "Evolução temporal",
            ["meses", "anos"],
            format_func=lambda h: "Meses do ano" if h == "meses" else "Todos os anos",
            horizontal=True,
            key="horizonte",
            help=(
                "Meses do ano mostra o ano selecionado mês a mês; Todos os anos "
                "mostra a série histórica completa."
            ),
        )
        # Casos e incidência juntos é o gráfico que o original mostra para
        # tuberculose. Fica como opção, não como padrão, porque só faz sentido
        # para essas duas métricas.
        duplo = controle_d.toggle(
            "Casos + incidência",
            key="serie_dupla",
            help="Sobrepõe a contagem e a taxa, cada uma no seu eixo.",
        )

        if duplo:
            serie = _serie_dupla(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun, horizonte)
            figura_serie = graficos.evolucao_dupla(
                serie,
                altura=ALTURA_SERIE,
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
                    serie, rotulo=rotulo, cor=pack.cor(nav.metrica),
                    altura=ALTURA_SERIE,
                )
            else:
                figura_serie = graficos.evolucao_anual(
                    serie, rotulo=rotulo, cor=pack.cor(nav.metrica), ano=nav.ano,
                    altura=ALTURA_SERIE,
                )

        st.altair_chart(figura_serie, use_container_width=True)

        # A série mensal vem por notificação e os KPIs por residência — ver
        # docs/contrato-dados.md, armadilha 7. Avisar é melhor que deixar o
        # usuário descobrir somando as barras.
        if horizonte == "meses":
            st.caption(graficos.AVISO_NOTIFICACAO)


_painel_evolucao()


st.divider()

baixo_esq, baixo_dir = st.columns(2, gap="small")

@st.fragment
def _painel_piramide() -> None:
    """Pirâmide etária, isolada num fragmento.

    `tipo` (casos ou óbitos) e `taxa` (por 100 mil) são locais. Marcar "por
    100 mil habitantes" reconstruía o mapa inteiro, que é o exemplo que mais
    incomodava: dois cliques de leitura numa ponta da página custavam o
    redesenho da outra.
    """
    with resiliencia.painel("Pirâmide etária"):

        # Casos vêm do SINAN; óbitos, do SIM. Cura não tem quebra por idade em
        # nenhum parquet — a coluna existe só por sexo. Ver leitura.FONTE_PIRAMIDE.
        st.markdown(ui.titulo_painel("Pirâmide etária"), unsafe_allow_html=True)
        tipo = st.radio(
            "O que exibir",
            ["CASOS", "OBITOS"],
            format_func=lambda t: {"CASOS": "Casos novos", "OBITOS": "Óbitos"}[t],
            horizontal=True,
            key="tipo_piramide",
            help=(
                "Casos vêm do SINAN; óbitos, do SIM. Cura por faixa etária não "
                "existe em nenhuma das fontes disponíveis."
            ),
        )

        dados_pir = _piramide(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun, tipo)

        # Só casos trazem população, então só eles podem virar taxa. O
        # controle continua na tela desabilitado em vez de sumir: alternar
        # entre casos e óbitos fazia a pirâmide subir e descer, e um controle
        # que desaparece não explica por que desapareceu.
        por_100mil = st.toggle(
            "Por 100 mil habitantes",
            key="piramide_taxa",
            disabled=tipo != "CASOS",
            help=(
                "Desconta o tamanho de cada faixa etária na população. "
                "Indisponível para óbitos: eles vêm do SIM, que não traz "
                "população por faixa."
            ),
        )
        taxa = tipo == "CASOS" and por_100mil

        st.altair_chart(
            graficos.piramide(
                dados_pir,
                rotulo="Casos" if tipo == "CASOS" else "Óbitos",
                por_100mil=bool(taxa),
            ),
            use_container_width=True,
        )
        if tipo == "OBITOS" and not dados_pir.empty:
            st.caption(
                "Óbitos por faixa etária vêm do SIM, não do SINAN — o total pode "
                "divergir dos demais painéis."
            )


with baixo_esq:
    _painel_piramide()

@st.fragment
def _painel_composicao() -> None:
    """Composição por variável do SINAN, isolada num fragmento.

    São 24 variáveis no seletor, e trocar entre elas é a interação mais
    repetida do painel — quem investiga um recorte percorre várias. Cada troca
    reenviava o mapa.
    """
    with resiliencia.painel("Composição"):
        st.markdown(
            ui.titulo_painel("Composição por variável do SINAN"), unsafe_allow_html=True
        )

        _rotulos_var = pack.variaveis_planas()
        variavel = st.selectbox(
            "Variável",
            list(_rotulos_var),
            format_func=lambda c: f"{pack.grupo_da(c)} · {_rotulos_var[c]}",
            key="variavel_composicao",
        )

        composto = _composicao(pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun, variavel)
        st.altair_chart(
            graficos.composicao(
                composto, rotulo=_rotulos_var[variavel], cor=pack.cor(nav.metrica)
            ),
            use_container_width=True,
        )

        # Base pequena não vira percentual — a decisão vem de `leitura.composicao`,
        # aqui só se explica ao usuário por que o eixo mudou.
        if not composto.empty and composto["pct"].isna().all():
            st.caption(graficos.AVISO_BASE_PEQUENA.format(n=int(composto["total"].iloc[0])))


with baixo_dir:
    _painel_composicao()

st.divider()
with resiliencia.painel("Indicadores do programa"):
    st.markdown(
        ui.titulo_painel("Indicadores do programa de tuberculose"), unsafe_allow_html=True
    )

    indicadores = _indicadores_programa(
        pack.DOENCA, nav.ano, nav.nivel, nav.uf, nav.mun
    )
    colunas = st.columns(len(indicadores), gap="small")
    for coluna, ind in zip(colunas, indicadores):
        coluna.markdown(
            ui.indicador_programa(
                ind["rotulo"],
                ind["pct"],
                ind["numerador"],
                ind["denominador"],
                cor=ind["cor"],
                ajuda=ind["descricao"],
            ),
            unsafe_allow_html=True,
        )

    # Estes arquivos vêm de outra extração, com cobertura de ano própria: em
    # 2025 trazem 161.739 contatos identificados para 1.773 casos novos, o que
    # daria 91 contatos por caso. Em 2024, com os dois fechados, a razão é 2.
    # Recalculado aqui em vez de reaproveitar a variável da barra lateral:
    # depender de um nome atribuído 300 linhas acima quebra em silêncio se
    # alguém reordenar a página. A leitura é cacheada, então não custa.
    if _meses_com_dado(pack.DOENCA, nav.ano) < 12:
        st.caption(
            f"Estes dois indicadores vêm de uma extração separada, que pode "
            f"cobrir período diferente do resto do painel — e {nav.ano} ainda "
            f"não fechou. Não compare com os cartões do topo."
        )

# Procedência à vista, no formato que o Boletim Epidemiológico do MS usa sob
# cada figura. Não é formalidade: um painel de vigilância circula em captura de
# tela e em relatório, longe desta página, e dois números tirados em meses
# diferentes viram discussão sobre quem errou quando ninguém sabe de quando é
# cada um. O SINAN é atualizado retroativamente — o mesmo ano encolhe ou cresce
# conforme a data da extração.
st.caption(
    f"Fonte: Sinan/Ministério da Saúde; população IBGE. Óbitos: SIM. "
    f"Série exibida: {_anos()[0]}–{_anos()[-1]}. "
    f"Dados preliminares, sujeitos a alteração — o Sinan é atualizado "
    f"retroativamente.  \n"
    f"Conferido contra o Boletim Epidemiológico de Tuberculose 2026 "
    f"(Ministério da Saúde, março/2026): casos novos e incidência do Brasil "
    f"batem dentro de 1,4% em todos os anos de 2014 a 2024 — ver "
    f"tests/paridade/referencia_ms.json.  \n"
    f"Divergências conhecidas entre fontes de dados: ver docs/contrato-dados.md."
)
