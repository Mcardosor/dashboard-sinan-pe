"""Componentes visuais em HTML, para injetar no Streamlit.

O CSS sai uma vez por sessão (:func:`css_base`); os componentes só emitem
marcação. A cor de cada card entra por variável CSS inline, então um único
bloco de estilo serve todas as métricas e todas as doenças.
"""

from __future__ import annotations

from html import escape

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
.kpi-value {{
  font-size: {tokens.TEXTO_XL};
  font-weight: 900;
  letter-spacing: -.2px;
  line-height: 1.03;
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

/* Slot clicável -----------------------------------------------------------
   O card é HTML injetado e não consegue falar de volta com o Python. A
   solução é um `st.button` real, transparente, esticado por cima do card
   dentro de um `st.container(key=...)`.

   Ganho sobre o original: lá o card era um `div` com `role="button"` e um
   handler de JS — um controle falso. Aqui o controle é um `<button>` de
   verdade, então foco, teclado e leitor de tela funcionam sem nada extra.

   O botão usa a chave `selkpi-<metrica>`, e não `kpi-btn-<metrica>`, de
   propósito: `[class*="st-key-kpi-"]` casaria também com o contêiner do
   próprio botão, que viraria a âncora do posicionamento absoluto e prenderia
   o botão a si mesmo em vez de esticá-lo sobre o card. */
[class*="st-key-kpi-"] {{ position: relative; }}
[class*="st-key-kpi-"] .stButton {{
  position: absolute;
  inset: 0;
  margin: 0;
  z-index: 3;
}}
[class*="st-key-kpi-"] [data-testid="stElementContainer"]:has(.stButton) {{
  position: static;
}}
[class*="st-key-kpi-"] .stButton > button {{
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: transparent;
  box-shadow: none;
  border-radius: {tokens.RAIO_CARD};
  cursor: pointer;
}}
/* O foco aparece no card, não no botão invisível. */
[class*="st-key-kpi-"] .stButton > button:focus-visible {{ outline: none; }}
[class*="st-key-kpi-"]:has(.stButton > button:focus-visible) .kpi-card {{
  border-color: color-mix(in srgb, var(--kpi-accent) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--kpi-accent) 35%, transparent),
              var(--sombra-hover);
}}
[class*="st-key-kpi-"]:hover .kpi-card {{
  border-color: color-mix(in srgb, currentColor 24%, transparent);
  box-shadow: var(--sombra-hover);
}}
[class*="st-key-kpi-"]:hover .kpi-card::after {{ opacity: 1; }}

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
) -> str:
    """Card de KPI — apenas apresentação.

    A cor entra como variável CSS inline (``--kpi-accent``), o que permite um
    único bloco de estilo servir todas as métricas.

    Deliberadamente **sem** ``role="button"`` ou ``tabindex``: quem torna o
    card clicável é :func:`kpi_clicavel`, com um ``<button>`` de verdade por
    cima. Um `div` fingindo ser botão, como no original, engana o leitor de
    tela e cria uma parada de tabulação que não funciona com o teclado.
    """
    classes = "kpi-card is-selected" if selecionado else "kpi-card"
    sub = (
        f'<div class="kpi-sub">{escape(subtitulo)}</div>'
        if subtitulo
        else ""
    )
    return (
        f'<div class="{classes}" style="--kpi-accent:{escape(cor)};" aria-hidden="true">'
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


def kpi_clicavel(
    st,
    chave: str,
    titulo: str,
    valor: str,
    *,
    cor: str,
    subtitulo: str | None = None,
    badge_delta: str = "",
    selecionado: bool = False,
    ao_clicar=None,
) -> bool:
    """Renderiza um card de KPI que seleciona a métrica ao ser clicado.

    Recebe o módulo ``streamlit`` por parâmetro para este módulo continuar
    testável sem subir a aplicação.

    O card é HTML e não consegue devolver evento ao Python. Quem captura o
    clique é um ``st.button`` transparente esticado por cima, dentro de um
    ``st.container(key=...)`` — a chave vira uma classe no DOM
    (``st-key-kpi-<chave>``) que o CSS usa para posicionar o botão.

    Devolve ``True`` se foi clicado nesta execução.
    """
    with st.container(key=f"kpi-{chave}"):
        st.markdown(
            kpi_card(
                titulo,
                valor,
                cor=cor,
                subtitulo=subtitulo,
                badge_delta=badge_delta,
                selecionado=selecionado,
            ),
            unsafe_allow_html=True,
        )
        return st.button(
            f"Selecionar {titulo}",
            key=f"selkpi-{chave}",
            on_click=ao_clicar,
            args=(chave,) if ao_clicar else None,
            use_container_width=True,
        )


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
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
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
  grid-column: 2;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_TITULO};
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: .01em;
  text-align: center;
  text-wrap: balance;
  color: inherit;
}}
.sinan-intro-bandeira, .sinan-intro-logo {{
  display: block;
  width: auto;
  object-fit: contain;
}}
.sinan-intro-bandeira {{ max-height: 54px; max-width: min(18vw, 140px); }}
.sinan-intro-logo {{ max-height: 66px; max-width: min(33vw, 290px); justify-self: end; }}

/* Sem as imagens, o título ocupa a faixa inteira em vez de ficar deslocado
   para o meio de um grid vazio. */
.sinan-intro.sem-marcas {{ grid-template-columns: 1fr; }}
.sinan-intro.sem-marcas .sinan-intro-titulo {{ grid-column: 1; }}

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


def faixa_intro(titulo: str, bandeira: str | None = None, logo: str | None = None) -> str:
    """Faixa de identificação: bandeira · título · logo.

    ``bandeira`` e ``logo`` são URIs de dados (``data:image/...``). Quando
    faltam — que é o caso hoje, os arquivos não vieram na entrega do projeto
    em R — a faixa mostra só o título, ocupando a largura toda.
    """
    marcas = bool(bandeira or logo)
    classe = "sinan-intro" if marcas else "sinan-intro sem-marcas"

    esquerda = (
        f'<img class="sinan-intro-bandeira" src="{escape(bandeira)}" alt="">'
        if bandeira
        else "<span></span>" if marcas else ""
    )
    direita = (
        f'<img class="sinan-intro-logo" src="{escape(logo)}" alt="">'
        if logo
        else "<span></span>" if marcas else ""
    )
    return (
        f'<div class="{classe}">{esquerda}'
        f'<h1 class="sinan-intro-titulo">{escape(titulo)}</h1>'
        f"{direita}</div>"
    )


def painel_vazio(titulo: str, aviso: str, *, mapa: bool = False) -> str:
    """Espaço reservado de um painel que ainda não existe."""
    variante = "sinan-painel-mapa" if mapa else "sinan-painel-graficos"
    return (
        f'<div class="sinan-painel {variante} sinan-painel-vazio">'
        f"<div><strong>{escape(titulo)}</strong><br>{escape(aviso)}</div></div>"
    )
