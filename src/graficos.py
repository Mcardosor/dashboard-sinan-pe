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

def _px(token: str) -> int:
    """`"12px"` para `12`. O Altair quer número, o CSS quer unidade."""
    return int(token.rstrip("px"))


#: Altura padrão dos gráficos do painel direito.
ALTURA = 300

#: Faixa vertical por barra do ranking, na **área de plotagem**.
#:
#: Medido no navegador: a caixa do rótulo tem 16px de altura com a fonte de
#: 12px, e o Vega esconde um nome sim outro não assim que o passo entre eles
#: fica abaixo disso. Com 27 UFs em 512px de área útil o passo caía para
#: 15,3px — colidia por menos de um pixel, e metade dos nomes sumia.
#:
#: 22 deixa 6px de folga sobre a caixa, o bastante para a variação de métrica
#: de fonte entre navegadores.
ALTURA_BARRA_RANKING = 22

#: Altura que o eixo x, seu título e as margens comem antes de sobrar espaço
#: para as barras. Medido no navegador: 594px de gráfico davam 512px de área
#: de plotagem.
#:
#: Entra na conta porque a primeira tentativa de conserto reservou 22px por
#: barra sobre a altura **total** e continuou escondendo nomes — as faixas
#: recebiam 19px, não 22.
ALTURA_EIXO_RANKING = 82

#: Piso do ranking, para uma lista de 5 não virar uma tira.
ALTURA_MIN_RANKING = 180

#: Espaço para o nome no eixo do ranking, em pixels.
#:
#: **O critério não é estética, é identificação.** Cortado curto demais, dois
#: municípios diferentes da mesma UF viram o mesmo texto, e o ranking deixa de
#: dizer de quem é a barra. Medido sobre os 5.571 nomes, com a largura de
#: :data:`PX_POR_CARACTERE`:
#:
#: ====== ======== =========
#: limite cortados ambíguos
#: ====== ======== =========
#: 98         891        49
#: 120        429         4
#: **150**     23         0
#: 175          2         0
#: ====== ======== =========
#:
#: 98 era o que o Vega dava sozinho, e ali "São Domingos do Maranhão" e "São
#: Domingos do Azeitão" apareciam idênticos. 150 é o **menor** valor onde
#: nenhum par colide; os 23 que ainda cortam continuam únicos, e o nome
#: inteiro está no tooltip. Subir para 175 salvaria dois nomes e custaria 25px
#: de barra a todo mundo.
LARGURA_ROTULO_RANKING = 150

#: Largura média de um caractere do rótulo, medida no navegador com a fonte de
#: 12px do tema: "José Gonçalves de Minas" ocupa 132px em 23 caracteres.
#:
#: Serve para o teste conferir a propriedade de identificação sem abrir um
#: navegador. É aproximação — nome cheio de "i" ocupa menos que um de "m" —,
#: mas o erro é da ordem de um caractere e a margem entre 150 e o primeiro
#: valor que colide (120) é de seis.
PX_POR_CARACTERE = 5.74

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
            labelFontSize=_px(tokens.TEXTO_XS),
            titleFontSize=_px(tokens.TEXTO_XS),
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
            labelFontSize=_px(tokens.TEXTO_XS),
            titleFontSize=_px(tokens.TEXTO_XS),
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


def evolucao_mensal(dados: pd.DataFrame, *, rotulo: str, cor: str, altura: int = ALTURA) -> alt.Chart:
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
        ),
        altura=altura,
    )


def evolucao_anual(dados: pd.DataFrame, *, rotulo: str, cor: str, altura: int = ALTURA, ano: int) -> alt.Chart:
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
        ),
        altura=altura,
    )


def desfechos(
    dados: pd.DataFrame,
    *,
    cores: dict[str, str],
    rotulos: dict[str, str],
    ano: int,
    altura: int = ALTURA,
) -> alt.Chart:
    """Composição anual dos desfechos de tratamento, empilhada.

    No formato da Figura 22 do Boletim de TB 2026: uma barra por ano, as
    quatro fatias somando 100%. Responde à pergunta que a linha isolada de
    cura não responde — para onde foi o que deixou de curar.

    Barra empilhada e não área: o dado é anual e discreto, e a área sugere
    interpolação entre anos que não existe.

    A ordem das fatias vem de `rotulos`, e é fixa de propósito. Deixar o
    Altair ordenar por valor faria as faixas trocarem de lugar entre anos, e o
    gráfico deixaria de ser legível como composição.
    """
    if dados.empty:
        return sem_dado("Sem desfechos registrados para este recorte")

    ordem = list(rotulos)
    base = dados.assign(
        rotulo=dados["desfecho"].map(rotulos),
        atual=dados["ano"] == ano,
        ordem=dados["desfecho"].map(ordem.index),
    )
    dominio = [rotulos[nome] for nome in ordem]
    faixa = [cores[nome] for nome in ordem]

    return tema(
        alt.Chart(base)
        .mark_bar()
        .encode(
            x=alt.X("ano:O", title=None),
            y=alt.Y("pct:Q", title="% dos encerramentos", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "rotulo:N",
                scale=alt.Scale(domain=dominio, range=faixa),
                legend=alt.Legend(title=None),
                sort=dominio,
            ),
            # Ascendente põe a cura embaixo, encostada no eixo. É a fatia
            # que se lê contra uma linha de base; as outras flutuam, e flutuar
            # sobre uma base que se mexe já é difícil o bastante para a de
            # cima. Com `descending` a cura ia para o topo e a leitura
            # invertia.
            order=alt.Order("ordem:Q", sort="ascending"),
            # O ano selecionado fica opaco e os demais recuam, igual à série
            # anual ao lado.
            opacity=alt.condition(alt.datum.atual, alt.value(1.0), alt.value(0.55)),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("rotulo:N", title="Desfecho"),
                alt.Tooltip("pct:Q", title="Proporção", format=".1f"),
                alt.Tooltip("n:Q", title="Encerramentos", format=",.0f"),
            ],
        ),
        altura=altura,
    )


#: Aviso do empilhado de desfechos. O gráfico é honesto e ainda assim
#: comparável ao boletim só até certo ponto — dizer isso na tela é mais barato
#: que alguém citar o número numa reunião como se fosse o oficial.
#:
#: A segunda frase não é zelo: o degrau de 2018 é defeito de extração,
#: confirmado contra o SINAN bruto. Ver docs/contrato-dados.md, armadilha 16.
AVISO_DESFECHOS = (
    "Sobre **todos** os casos novos encerrados. O Boletim do MS publica a "
    "mesma composição só para tuberculose pulmonar confirmada por critério "
    "laboratorial, e chega a proporções de cura mais altas — os dados que "
    "recebemos não permitem isolar esse subgrupo.  \n"
    "**Há um degrau em 2018.** A categoria \"não informado\" deixou de ser "
    "extraída naquele ano, e sem ela o denominador encolhe: de 2018 em diante "
    "a cura aparece cerca de 1 ponto acima do real. A queda no período é um "
    "pouco maior do que o gráfico mostra, não menor."
)


def ranking(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    selecao: alt.Parameter,
    altura_minima: int = 0,
    escala=None,
) -> alt.Chart:
    """Barras horizontais das maiores geografias, clicáveis.

    Horizontal e não vertical: nome de município não cabe num eixo x sem
    rotacionar, e rótulo rotacionado é mais difícil de ler que uma barra a
    mais de altura.

    ``altura_minima`` é **piso, não teto**. Serve para o ranking dividir a
    linha com o mapa, que tem altura fixa: sem ela a coluna da direita termina
    antes e sobra um vão. Cada barra recebe :data:`ALTURA_BARRA_RANKING`, e o
    painel cresce quando a lista pede mais que o piso.

    Já foi sobrescrita, e era um teto disfarçado: com 484px fixos e 25
    municípios, cada faixa ficava com 19px e o Vega passava a esconder um
    rótulo sim, outro não — metade dos nomes sumia sem nenhum aviso. É uma
    forma de degradação silenciosa: o gráfico continua bonito e responde a
    perguntas erradas, porque a barra que se lê não é a que se pensa estar
    lendo.

    ``escala`` é a do mapa ao lado. Passando-a, cada barra recebe a cor do
    polígono correspondente, e os dois painéis viram uma leitura só: o
    Amazonas é o tom mais escuro nos dois lugares. Sem ela, todas as barras
    saem na cor da métrica — que é o que havia antes, e fazia o ranking
    parecer desligado do mapa.

    A cor é redundante com o comprimento, de propósito: não acrescenta
    informação, acrescenta **ligação**. Por isso a legenda fica desligada —
    a do mapa, logo abaixo, já explica as faixas e vale para os dois.
    """
    if dados.empty:
        return sem_dado("Sem dados para ranquear neste recorte")

    if escala is None:
        cor_da_barra = alt.value(cor)
    else:
        # Importado aqui e nao no topo: `graficos` nao depende de `mapa` em
        # nenhum outro ponto, e subir esse acoplamento para o modulo inteiro
        # por causa de uma funcao seria pagar caro por pouco.
        from . import mapa

        dados = dados.assign(classe=mapa.classificar(dados["valor"], escala))
        cor_da_barra = alt.Color(
            "classe:N",
            scale=alt.Scale(
                domain=list(escala.cores),
                range=list(escala.cores.values()),
            ),
            legend=None,
        )

    return tema(
        alt.Chart(dados)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            y=alt.Y(
                "nome:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=LARGURA_ROTULO_RANKING),
            ),
            x=alt.X("valor:Q", title=rotulo),
            color=cor_da_barra,
            # O item sob o cursor destaca; os demais recuam. Dá retorno de
            # que a barra é clicável sem precisar de instrução escrita.
            opacity=alt.condition(selecao, alt.value(1.0), alt.value(0.55)),
            tooltip=[
                alt.Tooltip("nome:N", title="Local"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.1f"),
            ],
        )
        .add_params(selecao),
        altura=max(
            altura_minima,
            ALTURA_MIN_RANKING,
            ALTURA_BARRA_RANKING * len(dados) + ALTURA_EIXO_RANKING,
        ),
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
    dados: pd.DataFrame,
    *,
    cor_barra: str,
    cor_linha: str,
    eixo_x: str,
    titulo_x: str | None = None,
    altura: int = ALTURA,
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

    return tema(alt.layer(barras, linha).resolve_scale(y="independent"), altura=altura)


#: Cores dos dois lados da pirâmide. Deliberadamente não é rosa e azul: a
#: convenção de gênero por cor é ruído num gráfico epidemiológico, e o azul
#: já está tomado pela métrica de mortalidade.
COR_HOMENS = "#1C5D99"
COR_MULHERES = "#B8860B"


def piramide(
    dados: pd.DataFrame, *, rotulo: str, por_100mil: bool = False
) -> alt.Chart:
    """Pirâmide etária: homens à esquerda, mulheres à direita.

    Escala única. A tentação é desenhar a população como barra de fundo, no
    estilo IBGE, mas população e casos diferem em três ordens de grandeza —
    o fundo só cabe junto com um segundo eixo x, e aí o comprimento de uma
    barra não diz nada sobre a outra. Quem quer o efeito da estrutura etária
    usa ``por_100mil``, que é a leitura correta e cabe num eixo só.
    """
    if dados.empty:
        return sem_dado("Sem dado por faixa etária para este recorte")

    base = dados.copy()
    if por_100mil:
        pop = pd.to_numeric(base["pop"], errors="coerce")
        base["valor"] = (base["valor"] / pop * 100_000).where(pop > 0)
        base = base.dropna(subset=["valor"])
        if base.empty:
            return sem_dado("Sem população para calcular a taxa")
        rotulo = f"{rotulo} por 100 mil hab."

    base["lado"] = base["sexo"].map({"M": -1, "F": 1}).fillna(1)
    base["sexo_rotulo"] = base["sexo"].map({"M": "Homens", "F": "Mulheres"})
    base["evento"] = base["valor"] * base["lado"]

    faixas = [f for _, f in sorted({(r.faixa_ord, r.faixa_etaria) for r in base.itertuples()})]
    formato = ",.1f" if por_100mil else ",.0f"

    # Domínio simétrico. Em tuberculose os homens somam quase o triplo das
    # mulheres, e sem isso o eixo cresce só para a esquerda: a pirâmide fica
    # torta e o excesso masculino, que é o achado, vira efeito de escala.
    limite = float(base["evento"].abs().max()) or 1.0
    dominio = [-limite, limite]

    grafico = (
        alt.Chart(base)
        .mark_bar()
        .encode(
            # Sem sinal no eixo: o lado já diz o sexo, e "-500 casos" não existe.
            x=alt.X(
                "evento:Q",
                title=rotulo,
                scale=alt.Scale(domain=dominio, nice=False),
                axis=alt.Axis(labelExpr=f"format(abs(datum.value), '{formato}')"),
            ),
            y=alt.Y(
                "faixa_etaria:N",
                sort=list(reversed(faixas)),
                title=None,
                # Sem isso o Altair rareia os rótulos e some com faixas.
                axis=alt.Axis(labelOverlap=False),
            ),
            color=alt.Color(
                "sexo_rotulo:N",
                scale=alt.Scale(
                    domain=["Homens", "Mulheres"], range=[COR_HOMENS, COR_MULHERES]
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("faixa_etaria:N", title="Faixa"),
                alt.Tooltip("sexo_rotulo:N", title="Sexo"),
                alt.Tooltip("valor:Q", title=rotulo, format=formato),
            ],
        )
    )
    return tema(grafico, altura=max(280, 30 * len(faixas)))


def composicao(dados: pd.DataFrame, *, rotulo: str, cor: str) -> alt.Chart:
    """Distribuição de uma variável do SINAN, em barras horizontais.

    Mostra percentual quando a base sustenta e contagem quando não — a
    decisão vem pronta da camada de dados, em ``leitura.composicao``, que
    anula ``pct`` abaixo do limiar. Aqui só se obedece.
    """
    if dados.empty:
        return sem_dado("Sem registro desta variável no recorte")

    base = dados.copy()
    percentual = "pct" in base.columns and base["pct"].notna().any()

    if percentual:
        base["valor"] = pd.to_numeric(base["pct"], errors="coerce")
        # Inteiro no eixo, decimal só no tooltip: com passo de 2% o eixo
        # ganhava 28 marcações e virava uma régua.
        titulo_x, formato = "% dos casos", ".0f"
    else:
        base["valor"] = pd.to_numeric(base["n"], errors="coerce")
        titulo_x, formato = "Casos", ",.0f"

    ordem = base.sort_values("valor", ascending=False)["categoria"].tolist()

    grafico = (
        alt.Chart(base)
        .mark_bar(color=cor, cornerRadiusTopRight=2, cornerRadiusBottomRight=2)
        .encode(
            x=alt.X(
                "valor:Q",
                title=titulo_x,
                axis=alt.Axis(format=formato, tickCount=6),
            ),
            y=alt.Y("categoria:N", sort=ordem, title=None,
                    axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            tooltip=[
                alt.Tooltip("categoria:N", title=rotulo),
                alt.Tooltip("n:Q", title="Casos", format=",.0f"),
            ] + ([alt.Tooltip("pct:Q", title="% dos casos", format=".1f")]
                 if percentual else []),
        )
    )
    return tema(grafico, altura=max(200, 34 * len(base)))


#: Aviso de base pequena. O texto evita "suprimido", que sugere censura: o
#: motivo é estatístico, e a contagem continua à vista.
AVISO_BASE_PEQUENA = (
    "Base pequena ({n} registros) — exibindo a contagem, não o percentual. "
    "Proporção sobre tão poucos casos não é interpretável."
)
