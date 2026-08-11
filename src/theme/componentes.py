"""Componentes visuais em HTML, para injetar no Streamlit.

O CSS sai uma vez por sessão (:func:`css_base`); os componentes só emitem
marcação. A cor de cada card entra por variável CSS inline, então um único
bloco de estilo serve todas as métricas e todas as doenças.
"""

from __future__ import annotations

from html import escape

from . import cores

from . import tokens


def css_base() -> str:
    """Folha de estilo da aplicação. Injetar uma única vez, no início da página."""
    faixas = "\n".join(
        f"@media (max-width: {px}px) {{ .kpi-grid {{ grid-template-columns:"
        f" repeat(auto-fit, minmax({larg}, 1fr)); }} }}"
        for px, larg in tokens.GRID_KPI
        if px
    )
    return f"""
<style>
/* As superfícies são derivadas de `currentColor`, nunca declaradas.
 *
 * Um tema claro e um escuro exigiriam saber qual está ativo, e não há como
 * saber com segurança: `prefers-color-scheme` segue o sistema operacional, e
 * não o Streamlit — com o tema forçado para claro em `.streamlit/config.toml`
 * e o sistema em escuro, os cards ficariam escuros sobre uma página clara.
 * `st.context.theme` também não serve: erra no primeiro quadro e ao trocar de
 * tema (issue #11920 do Streamlit).
 *
 * Misturando a cor do texto com o fundo, a superfície acompanha o tema
 * sozinha — `currentColor` já vem invertido pelo Streamlit. Um só bloco de
 * CSS serve os dois temas, sem detecção nenhuma. */
:root {{
  --fonte: {tokens.FONTE};
  --borda: {tokens.BORDA};
  --sombra: {tokens.SOMBRA_REPOUSO};
  --sombra-hover: {tokens.SOMBRA_HOVER};
  --sombra-ativo: {tokens.SOMBRA_ATIVO};
  --superficie: color-mix(in srgb, currentColor {tokens.MISTURA_CARD}, transparent);
  --superficie-topo: color-mix(in srgb, currentColor {tokens.MISTURA_CARD_TOPO}, transparent);
}}

.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax({tokens.GRID_KPI[0][1]}, 1fr));
  gap: .75rem;
  align-items: stretch;
  width: 100%;
}}
{faixas}
@media (max-width: 460px) {{ .kpi-grid {{ grid-template-columns: 1fr; }} }}

.kpi-card {{
  --kpi-accent: #0F766E;
  position: relative;
  overflow: hidden;
  border-radius: {tokens.RAIO_CARD};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: var(--sombra);
  color: inherit;
  font-family: var(--fonte);
  transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}}
.kpi-card::after {{
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: {tokens.RAIO_CARD};
  opacity: 0;
  pointer-events: none;
  transition: opacity .14s ease;
  background:
    radial-gradient(220px 120px at 15% 10%,
      color-mix(in srgb, var(--kpi-accent) 22%, transparent), transparent 65%),
    radial-gradient(220px 120px at 85% 0%,
      color-mix(in srgb, var(--kpi-accent) 8%, transparent), transparent 55%);
}}
.kpi-card:hover {{
  border-color: color-mix(in srgb, currentColor 24%, transparent);
  box-shadow: var(--sombra-hover);
}}
.kpi-card:hover::after {{ opacity: 1; }}
.kpi-card.is-selected {{
  border-color: color-mix(in srgb, var(--kpi-accent) 60%, transparent);
  box-shadow: var(--sombra-ativo),
              0 0 0 2px color-mix(in srgb, var(--kpi-accent) 28%, transparent);
}}
.kpi-card.is-selected::after {{ opacity: 1; }}
.kpi-card:focus-visible {{
  outline: none;
  border-color: color-mix(in srgb, var(--kpi-accent) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--kpi-accent) 35%, transparent),
              var(--sombra-hover);
}}

.kpi-inner {{
  position: relative;
  z-index: 1;
  display: flex;
  gap: {tokens.GAP};
  align-items: center;
  padding: {tokens.PADDING};
  min-width: 0;
}}
.kpi-accent {{
  flex: 0 0 auto;
  width: 9px;
  height: 46px;
  border-radius: {tokens.RAIO_PILL};
  background: var(--kpi-accent);
}}
.kpi-text {{ min-width: 0; }}
/* O original usava `nowrap` + reticências, e cortava 28% de rótulos como
   "Taxa de mortalidade (por 100 mil hab.)". Aqui o título quebra em até duas
   linhas e a altura é reservada, para os cards não ficarem desalinhados. */
.kpi-title {{
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 3px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.25;
  min-height: 2.5em;
}}
/* O acento se ajusta ao tema sem media query. `prefers-color-scheme` segue o
   sistema operacional, e não o tema do Streamlit — com o app em claro e o
   sistema em escuro, pintaria o acento errado.
   Misturar com `currentColor` resolve pela própria página: no tema claro o
   texto é escuro e a cor escurece de leve; no escuro o texto é claro e ela
   clareia. Cinco métricas ficavam abaixo do mínimo de 3:1 para texto grande
   no fundo escuro — `incid`, a padrão, em 2,6. */
.kpi-value {{
  font-size: {tokens.TEXTO_XL};
  font-weight: 900;
  letter-spacing: -.2px;
  line-height: 1.03;
  color: color-mix(in srgb, var(--kpi-accent) 72%, currentColor 28%);
}}
.kpi-sub {{
  font-size: {tokens.TEXTO_XS};
  opacity: .70;
  margin-top: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.kpi-delta {{ margin-top: 5px; font-size: {tokens.TEXTO_XS}; font-weight: 800; }}
.kpi-bom  {{ color: {tokens.BOM}; }}
.kpi-ruim {{ color: {tokens.RUIM}; }}
.kpi-igual {{ opacity: {tokens.NEUTRO_OPACIDADE}; }}

@media (prefers-reduced-motion: reduce) {{
  .kpi-card {{ transition: none !important; transform: none !important; }}
}}
</style>
"""


def formatar_inteiro(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.0f}".replace(",", ".")


def formatar_decimal(valor: float | None, casas: int = 2) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def delta(
    atual: float | None,
    anterior: float | None,
    *,
    taxa: bool = False,
    bom_se_cai: bool = True,
    sufixo: str = "vs ano anterior",
) -> str:
    """Badge de variação contra o ano anterior.

    ``bom_se_cai`` inverte a semântica de cor. Para cura, queda é ruim; para
    casos, óbitos e incidência, queda é boa. Herdado do original.
    """
    if atual is None or anterior is None:
        return ""

    diferenca = atual - anterior
    if abs(diferenca) < 1e-9:
        return f'<div class="kpi-delta kpi-igual">≈ sem variação {escape(sufixo)}</div>'

    caiu = diferenca < 0
    classe = "kpi-bom" if caiu == bom_se_cai else "kpi-ruim"
    seta = "↓" if caiu else "↑"
    texto = formatar_decimal(abs(diferenca)) if taxa else formatar_inteiro(abs(diferenca))
    return f'<div class="kpi-delta {classe}">{seta} {texto} {escape(sufixo)}</div>'


def kpi_card(
    titulo: str,
    valor: str,
    *,
    cor: str,
    subtitulo: str | None = None,
    badge_delta: str = "",
    selecionado: bool = False,
    ajuda: str = "",
) -> str:
    """Card de KPI — indicador, e só.

    A cor entra como variável CSS inline (``--kpi-accent``), o que permite um
    único bloco de estilo servir todas as métricas.

    **Não é controle.** Já foi: um ``<button>`` transparente ficava esticado
    por cima para trocar a métrica do mapa. Saiu porque o card não avisava que
    era clicável — parecia indicador porque é indicador —, e a interação
    custou quatro rodadas de conserto. Quem troca a métrica agora é um
    controle próprio, ao lado do mapa, com teclado e foco nativos.

    ``selecionado`` continua existindo para o card espelhar a métrica ativa,
    o que é leitura, não interação.
    """
    classes = "kpi-card is-selected" if selecionado else "kpi-card"
    # A explicação vive no `title`, agora que não há botão para receber `help`.
    titulo_ajuda = f' title="{escape(ajuda)}"' if ajuda else ""
    sub = (
        f'<div class="kpi-sub">{escape(subtitulo)}</div>'
        if subtitulo
        else ""
    )
    return (
        f'<div class="{classes}" '
        f'style="--kpi-accent:{escape(cor)};'
        f'--kpi-accent-escuro:{escape(cores.para_fundo_escuro(cor))};"'
        f'{titulo_ajuda}>'
        f'<div class="kpi-inner">'
        f'<div class="kpi-accent"></div>'
        f'<div class="kpi-text">'
        f'<div class="kpi-title">{escape(titulo)}</div>'
        f'<div class="kpi-value">{escape(valor)}</div>'
        f"{sub}{badge_delta}"
        f"</div></div></div>"
    )


def grade_kpis(cards: list[str]) -> str:
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


def css_layout() -> str:
    """Estrutura da página: barra lateral, faixa de intro e as linhas.

    Separado de :func:`css_base` porque estas regras dependem de detalhes
    internos do Streamlit e tendem a precisar de manutenção a cada versão,
    enquanto os componentes acima são HTML próprio e estáveis.
    """
    return f"""
<style>
/* Barra lateral com a largura do original — mas só quando há espaço. O
   original fixava 380px sem media query, e em telas estreitas isso espremia
   o conteúdo até os rótulos quebrarem no meio da palavra. */
section[data-testid="stSidebar"] {{
  width: {tokens.LARGURA_SIDEBAR} !important;
  min-width: {tokens.LARGURA_SIDEBAR} !important;
}}
@media (max-width: 1200px) {{
  section[data-testid="stSidebar"] {{
    width: 300px !important;
    min-width: 300px !important;
  }}
}}

/* O `st.columns` é uma linha flex que não quebra. Deixando quebrar, e com um
   mínimo por coluna, recupera-se o comportamento do grid `auto-fit` do
   original — que a troca por colunas reais (necessária para os botões) havia
   custado. */
[data-testid="stHorizontalBlock"]:has(.kpi-card) {{
  flex-wrap: wrap;
}}
[data-testid="stHorizontalBlock"]:has(.kpi-card) > [data-testid="stColumn"] {{
  min-width: 200px;
}}

.sinan-intro {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 10px 12px;
  margin-bottom: {tokens.GAP};
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}
.sinan-intro-titulo {{
  margin: 0;
  grid-column: 1;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_TITULO};
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: .01em;
  text-align: left;
  text-wrap: balance;
  color: inherit;
}}
.sinan-intro-logo {{
  display: block;
  width: auto;
  object-fit: contain;
  max-height: 66px;
  max-width: min(33vw, 290px);
}}

/* Os arquivos de marca são JPEG, sem canal alfa: no tema escuro o fundo
   branco viraria um bloco. Em vez de recortar a transparência — que mexeria
   na marca e deixaria halo nas bordas —, a imagem ganha uma placa branca
   explícita, que é o tratamento padrão para logotipo sem alfa e fica igual
   nos dois temas. */
.sinan-intro-marca {{
  display: inline-flex;
  align-items: center;
  justify-self: end;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 10px;
  background: #FFFFFF;
  box-shadow: 0 2px 8px rgba(2,6,23,.10);
}}
.indicador-programa {{
  padding: 14px 16px;
  border-radius: {tokens.RAIO_CARD};
  border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
  background: color-mix(in srgb, currentColor 3%, transparent);
}}
.indicador-titulo {{
  font-size: {tokens.TEXTO_XS};
  font-weight: 600;
  opacity: .75;
  margin-bottom: 4px;
}}
.indicador-valor {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  line-height: 1.1;
  color: var(--ind-cor);
}}
/* A trilha usa `currentColor` para funcionar nos dois temas sem duplicar
   regra — no claro ela escurece o fundo, no escuro ela o clareia. */
.indicador-barra {{
  height: 6px;
  margin: 8px 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 12%, transparent);
  overflow: hidden;
}}
.indicador-barra > span {{
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ind-cor);
}}
.indicador-detalhe {{ font-size: {tokens.TEXTO_XS}; opacity: .65; }}

/* Sem logotipo não há segunda coluna: o título ocupa a faixa toda. */
.sinan-intro.marcas-0 {{ grid-template-columns: 1fr; }}

/* Linha principal: mapa à esquerda, gráficos à direita.
   O original travava `height` em 520px e 760px, o que quebra em telas baixas;
   aqui são mínimos. */
.sinan-painel {{
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
  padding: {tokens.PADDING};
  color: inherit;
  font-family: var(--fonte);
}}
.sinan-painel-mapa {{ min-height: {tokens.ALTURA_MIN_MAPA}; }}
.sinan-painel-graficos {{ min-height: {tokens.ALTURA_MIN_PAINEL}; }}
/* Legenda do mapa. O deck.gl não desenha uma, então ela é HTML — mesmo
   padrão dos cards de KPI. */
.mapa-legenda {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-top: 8px;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  color: inherit;
}}
.mapa-legenda-titulo {{
  flex-basis: 100%;
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 2px;
}}
.mapa-legenda-item {{ display: inline-flex; align-items: center; gap: 6px; }}
.mapa-legenda-item i {{
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
}}

.sinan-painel-vazio {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: {tokens.TEXTO_SM};
  opacity: .55;
}}
</style>
"""


def faixa_intro(titulo: str, logo: str | None = None) -> str:
    """Faixa de identificação: título à esquerda, logotipo à direita.

    O original tinha três colunas, com a bandeira de Pernambuco à esquerda e o
    título ao centro. A bandeira saiu: os dados são nacionais e ela lia como
    recorte geográfico, não como emissor. Sem ela sobra um cabeçalho, e sem
    logotipo nenhum o título ocupa a faixa toda.

    ``logo`` é um URI de dados (``data:image/...``).
    """
    classe = f"sinan-intro marcas-{1 if logo else 0}"
    titulo_html = f'<h1 class="sinan-intro-titulo">{escape(titulo)}</h1>'

    if not logo:
        return f'<div class="{classe}">{titulo_html}</div>'
    return (
        f'<div class="{classe}">{titulo_html}'
        f'<span class="sinan-intro-marca">'
        f'<img class="sinan-intro-logo" src="{escape(logo)}" alt=""></span></div>'
    )


def painel_vazio(titulo: str, aviso: str, *, mapa: bool = False) -> str:
    """Espaço reservado de um painel que ainda não existe."""
    variante = "sinan-painel-mapa" if mapa else "sinan-painel-graficos"
    return (
        f'<div class="sinan-painel {variante} sinan-painel-vazio">'
        f"<div><strong>{escape(titulo)}</strong><br>{escape(aviso)}</div></div>"
    )


#: Seletor do contêiner do mapa no DOM do Streamlit.
SELETOR_MAPA = '[data-testid="stDeckGlJsonChart"]'


def script_travar_zoom() -> str:
    """Impede a roda do mouse de dar zoom no mapa.

    O caminho declarativo não existe: o ``DeckGlJsonChart`` do Streamlit passa
    ``controller={true}`` fixo para o ``<DeckGL>`` e descarta o que vier no
    JSON do pydeck. Sem isto, rolar a página com o cursor sobre o mapa aplica
    zoom, o enquadramento se perde e só recarregando volta — e o mapa ocupa
    metade da tela, então acontece o tempo todo.

    A interceptação é na fase de captura, antes de o evento descer até o
    deck.gl, e **sem** ``preventDefault``: a rolagem normal da página segue
    acontecendo. Só o zoom morre.

    Precisa rodar via ``st.components.v1.html`` — o ``st.markdown`` remove
    ``<script>``. O componente vira um iframe de mesma origem, daí o
    ``window.parent``.
    """
    return f"""
<script>
(function () {{
  var doc = window.parent && window.parent.document;
  if (!doc || doc.__travaZoomMapa) return;   // idempotente: o Streamlit
  doc.__travaZoomMapa = true;                // reexecuta o script a cada rerun
  doc.addEventListener('wheel', function (e) {{
    var alvo = (e.target && e.target.closest) ? e.target : null;
    if (alvo && alvo.closest('{SELETOR_MAPA}')) {{
      e.stopPropagation();
    }}
  }}, {{ capture: true, passive: true }});
}})();
</script>
"""


def indicador_programa(
    rotulo: str,
    pct: float | None,
    numerador: float | None,
    denominador: float | None,
    *,
    cor: str,
    ajuda: str = "",
) -> str:
    """Card de indicador de programa: proporção, componentes e barra.

    A barra existe porque proporção sem referência visual não comunica: 22%
    e 81% viram só dois números parecidos numa lista. Deliberadamente **sem
    meta desenhada** — as metas do programa nacional existem, mas não vou
    cravar um número oficial que não verifiquei; a barra mostra a proporção
    contra o total, e quem conhece a meta a aplica de cabeça.
    """
    valor = "—" if pct is None else f"{formatar_decimal(pct, 1)}%"
    largura = 0.0 if pct is None else max(0.0, min(100.0, pct))
    detalhe = (
        "sem dado neste recorte"
        if numerador is None or denominador is None
        else f"{formatar_inteiro(numerador)} de {formatar_inteiro(denominador)}"
    )

    titulo = f' title="{escape(ajuda)}"' if ajuda else ""
    return (
        f'<div class="indicador-programa" style="--ind-cor:{escape(cor)};"{titulo}>'
        f'<div class="indicador-titulo">{escape(rotulo)}</div>'
        f'<div class="indicador-valor">{valor}</div>'
        f'<div class="indicador-barra"><span style="width:{largura:.1f}%"></span></div>'
        f'<div class="indicador-detalhe">{escape(detalhe)}</div>'
        f"</div>"
    )
