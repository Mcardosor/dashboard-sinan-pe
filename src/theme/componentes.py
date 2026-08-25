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

/* Havia aqui `.kpi-grid`, um grid CSS com quebras em 1240, 860 e 460px, e a
 * função `grade_kpis()` que o emitia. Saíram em 2026-08-20 sem uso: os cards
 * são dispostos por `st.columns` desde que os botões de navegação entraram, e
 * quem os faz quebrar é a regra `stHorizontalBlock:has(.kpi-card)` em
 * `css_layout`. O grid ficou declarado e nunca emitido. */

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
  /* Reserva exatamente uma linha, mesmo vazia: div sem conteúdo colapsa para
     zero e o desalinhamento voltaria.
     `line-height` e `min-height` são declarados juntos e com o mesmo valor de
     propósito — separados, eles divergem. A primeira tentativa usou 1.15em
     contra um line-height herdado de 1.6, e sobraram 5px de desalinhamento. */
  line-height: 1.6;
  min-height: 1.6em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.kpi-delta {{ margin-top: 5px; font-size: {tokens.TEXTO_XS}; font-weight: 800; }}
.kpi-bom  {{ color: {tokens.BOM}; }}
.kpi-ruim {{ color: {tokens.RUIM}; }}
.kpi-igual {{ opacity: {tokens.NEUTRO_OPACIDADE}; }}

/* Conteúdo redesenhado entra com fade, em vez de piscar no lugar.

   Isto só passou a fazer sentido depois dos fragmentos. Antes, qualquer
   clique redesenhava a página inteira e um fade universal seria ruído — tudo
   pulsando a cada interação. Agora só o painel que mudou é reconstruído, e o
   fade vira **informação**: marca onde a mudança aconteceu, que é o que a
   pessoa quer saber ao mexer num controle.

   180ms é curto de propósito. Acima de ~250ms a animação deixa de suavizar e
   passa a parecer lentidão, e este painel responde em menos de 20ms na camada
   de dados — não há espera real a disfarçar.

   Sem `transform`: mover o gráfico ao aparecer disputaria com a leitura do
   eixo. Só opacidade. */
@keyframes sinan-surgir {{
  from {{ opacity: 0; }}
  to   {{ opacity: 1; }}
}}
[data-testid="stVegaLiteChart"] {{
  animation: sinan-surgir .18s ease-out;
}}

/* O mapa entra crescendo de leve, e só ele.

   Ao navegar de Brasil para um estado, o Streamlit **remonta** o widget: a
   chave inclui `nivel` e `uf`. O Brasil some e o estado aparece já
   enquadrado, sem continuidade espacial nenhuma — parece troca de slide, não
   aproximação.

   O certo seria um `FlyToInterpolator` do deck.gl, mas ele exige que o
   componente sobreviva à navegação, ou seja, chave estável. E chave estável
   custa caro aqui: reabre o laço de rerun que a seleção anterior provoca, e
   quebra o clique repetido que abre o modo detalhe — com a seleção
   inalterada, o Streamlit nem dispara rerun. Ver `app.py`, na montagem do
   `st.pydeck_chart`.

   Então o que se faz é perceptivo, não espacial: 0,975 para 1 sugere
   aprofundamento sem prometer continuidade que não existe. Começou em 0,985 e
   subiu para 0,975 depois de olhar em tela — sutil demais para se notar.
   Abaixo de ~0,97 vira "pop" e chama atenção para si; acima de 0,99 não se
   percebe. O valor é de calibragem visual, não de cálculo.

   Duração maior que a dos gráficos (260ms contra 180ms) porque aqui há uma
   troca de contexto a acompanhar, não só um redesenho. `ease-out` para a
   chegada desacelerar, que é o que dá a sensação de assentar. */
/* **O mapa não anima.** A animação de entrada acima foi removida em
   24/ago/2026, e o comentário fica porque a razão vale para qualquer tentativa
   futura.

   Ela era `opacity: 0 -> 1` com escala, e o Streamlit **recria o contêiner e
   o canvas do deck a cada rerun** — inclusive quando a `key` do widget não
   muda, medido no navegador. Então a animação de entrada tocava a cada
   interação, e como o mapa nascia transparente sobre o branco da página, isso
   lia como piscada.

   O que se queria de verdade era outra coisa: a câmera deslizando da vista
   antiga para a nova. Isso o deck.gl faz com `transitionDuration` e
   `FlyToInterpolator`, e o pydeck emite os dois — mas eles não têm efeito
   aqui, porque sem instância anterior não há de onde partir. `initialViewState`
   é sempre inicial de fato.

   Entre uma piscada e nenhum movimento, nenhum movimento é melhor: o mapa
   simplesmente está no lugar novo, e o retorno ao clique é imediato. */

@media (prefers-reduced-motion: reduce) {{
  .kpi-card {{ transition: none !important; transform: none !important; }}
  /* Quem pediu menos movimento não recebe nem o fade. Vestibular é o motivo:
     animação repetida a cada interação é gatilho, e aqui ela é decoração.

     O mapa continua listado embora já não anime: se alguém reintroduzir
     movimento ali, ele nasce respeitando a preferência em vez de precisar
     lembrar deste bloco. */
  [data-testid="stVegaLiteChart"],
  [data-testid="stDeckGlJsonChart"] {{
    animation: none !important;
    transform: none !important;
  }}
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
    # A linha do subtítulo existe sempre, vazia quando não há texto.
    #
    # Só um card a usa hoje — "Proporção de cura" mostra "49.114 de 85.932" —
    # e isso o deixava 22px mais alto que os vizinhos, quebrando o alinhamento
    # da linha inteira. Reservar a altura é o mesmo tratamento que `.kpi-title`
    # já recebe para títulos de duas linhas.
    #
    # Esticar o card com `height: 100%` não funciona: a coluna do Streamlit
    # tem altura automática, então não há contra o que esticar.
    sub = f'<div class="kpi-sub">{escape(subtitulo) if subtitulo else ""}</div>'

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
   o conteúdo até os rótulos quebrarem no meio da palavra.

   Recolher a barra deixava o conteúdo preso a 66% da janela, com uma faixa
   morta à esquerda e os rótulos quebrando letra a letra — o mesmo defeito que
   a media query acima existe para evitar, por outro caminho.

   A causa: o Streamlit recolhe deslizando com `transform: translateX(-100%)`
   e **mantém `width: 300px` inline** na seção. O elemento some da vista mas
   continua reservando a largura. Sem uma regra que zere isso, o buraco fica —
   e o `min-width` fixo daqui só piorava, porque também vencia qualquer
   tentativa do próprio Streamlit de encolher.

   Por isso as duas regras. Prender a largura ao estado aberto evita que ela
   valha na barra recolhida; zerar explicitamente no estado fechado é o que de
   fato recupera o espaço. Medido: sem a segunda regra o conteúdo continua em
   66% da janela mesmo com a primeira aplicada. */
/* Conteúdo recalculando esmaece — mas só se demorar.

   O Streamlit marca `data-stale="true"` nos elementos enquanto o script
   roda. Sem estilo, a troca é seca: o valor antigo fica firme e é
   substituído de repente, sem sinal nenhum de que algo estava acontecendo.

   **O atraso é o ponto todo.** Trocar de ano custa 87 ms no servidor; um
   fade que comece imediatamente estaria ainda correndo quando o conteúdo já
   chegou, e faria a interação parecer mais lenta do que é. Com 150 ms de
   espera, tudo que responde rápido não pisca — o esmaecimento só aparece nos
   casos que realmente demoram, como entrar numa UF com centenas de
   municípios.

   A volta é imediata, sem atraso: assim que o dado chega, ele aparece.
   Esconder a chegada seria o inverso do que se quer.

   Isto substitui o overlay que cobre a tela por 3 s no painel em R — ver
   `excecoes.md` §4. O sinal existe, mas não bloqueia e não anuncia uma
   lentidão que não temos. */
[data-stale] {{
  transition: opacity .12s ease;
}}
[data-stale="true"] {{
  opacity: .45;
  transition-delay: .15s;
}}
@media (prefers-reduced-motion: reduce) {{
  [data-stale] {{ transition: none; }}
}}

/* Respiro da página. O padrão do Streamlit é `96px 80px 160px`, medida de
   página de documento: 144px de nada antes do título e 160px depois do último
   gráfico, num painel aberto para ler número. Os 80px laterais ainda custavam
   160px de largura, e largura é o que falta ao mapa.

   `!important` porque a regra que estamos sobrescrevendo é do próprio
   Streamlit e tem especificidade de classe gerada, que muda a cada versão. */
[data-testid="stMainBlockContainer"] {{
  padding: {tokens.PAGINA_TOPO} {tokens.PAGINA_LADOS} {tokens.PAGINA_BASE} !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{
    padding-left: {tokens.PAGINA_LADOS_ESTREITO} !important;
    padding-right: {tokens.PAGINA_LADOS_ESTREITO} !important;
  }}
}}

/* A mãozinha do deck.gl some sobre o fundo branco do mapa.

   O deck escreve `cursor: grab` inline no `#deckgl-wrapper` — mão aberta, que
   no Windows é branca com um contorno fino e desaparece contra a área vazia do
   painel. Ficou pior quando o painel passou de 430x460 para 715x530: sobrou
   muito mais branco em volta da geometria.

   O seletor casa a **string do style inline**, e só nos estados de arrastar
   (`grab` e `grabbing`). Assim o `pointer` que o deck põe ao passar sobre um
   polígono continua intacto — é ele que avisa que dá para clicar e entrar no
   recorte, que é a interação de verdade deste mapa.

   Vale a mesma razão de bloquear o zoom pela roda: arrastar desenquadra um
   mapa cujo enquadramento é calculado para caber, e sem volta a não ser
   recarregando. Não é affordance que queiramos anunciar. */
#deckgl-wrapper[style*="cursor: grab"] {{
  cursor: default !important;
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

/* Título de painel — o degrau que faltava entre o título da página e o
   corpo.

   Estas linhas ("Mapa — unidades da federação", "Ranking — UFs, por
   incidência") são o que identifica cada painel, mas saíam como `st.caption`:
   14px peso 400, exatamente o mesmo que um rótulo de widget e que a nota de
   rodapé. Sem contraste de peso, o olho não encontrava onde um painel começa
   e o outro termina — a página tinha seis blocos e nenhum cabeçalho.

   Peso, e não tamanho: subir para 16px ou 18px competiria com o valor dos
   KPIs, que é o que precisa saltar primeiro. Peso 700 com opacidade alta
   separa sem disputar.

   Caixa alta foi descartada: "Ranking — UFs, por incidência (por 100 mil
   hab.)" em maiúsculas fica pior de ler, e é justamente o rótulo mais longo. */
.titulo-painel {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .85;
  line-height: 1.3;
  margin: 0 0 6px;
}}

.sinan-intro {{
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 12px 14px 12px 22px;
  margin-bottom: {tokens.GAP};
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}
/* Acento na cor da doença, colado na borda esquerda.

   Reaproveita a linguagem que os cards de KPI já estabeleceram — barra
   colorida à esquerda, valor à direita. Sem ele a faixa era um retângulo
   cinza com uma palavra dentro, e não parecia parte do mesmo sistema.

   A cor entra por variável inline (`--intro-accent`), como em `--kpi-accent`:
   um bloco de CSS serve qualquer doença do pack. */
.sinan-intro::before {{
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  background: var(--intro-accent, currentColor);
}}

.sinan-intro-texto {{
  grid-column: 1;
  min-width: 0;
}}

/* Escopo do recorte, na própria faixa.

   Com a barra lateral recolhida — que é como o painel é projetado — não havia
   **nada na tela** dizendo de que ano e de que território eram os números. O
   mesmo layout serve Brasil/2024 e Pernambuco/2018, e uma captura de tela não
   se explicava sozinha. Num painel de vigilância isso é procedência, não
   enfeite.

   É dinâmico de propósito: vira "Pernambuco · 2018" ao navegar. Foi por isso
   que o título ficou só "Tuberculose" — pôr "nacional" nele seria mentira no
   instante em que alguém clica numa UF, que é a interação principal. */
.sinan-intro-escopo {{
  margin-top: 2px;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 400;
  opacity: .68;
  line-height: 1.35;
}}

/* O seletor precisa do `h1` e do ancestral: o título é um `<h1>`, e o
   Streamlit estiliza `.st-emotion-cache-… h1` com `font-size: 2.75rem`. Esse
   seletor tem especificidade (0,1,1) e vencia `.sinan-intro-titulo` (0,1,0) —
   o `clamp` abaixo estava declarado e nunca chegava à tela, com o título
   fixo em 44px contra os 30px de teto. Era o que fazia "Tuberculose" quebrar
   em duas ou três linhas em janela estreita.

   `.sinan-intro h1.sinan-intro-titulo` dá (0,2,1) e ganha com folga, sem
   precisar de `!important` — que aqui seria pior, porque calaria também
   qualquer ajuste futuro do próprio pack de doença. */
.sinan-intro h1.sinan-intro-titulo {{
  margin: 0;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_TITULO};
  font-weight: 900;
  line-height: 1.08;
  /* Negativo, e não positivo: em peso 900 o espaçamento aberto espalha a
     palavra e ela perde solidez. Fechar um pouco faz o título ler como bloco,
     que é o que se quer de um nome de painel. */
  letter-spacing: -.015em;
  text-align: left;
  text-wrap: balance;
  color: inherit;
}}
/* A marca é texto, não imagem.

   Era um JPEG sobre uma placa branca explícita. A placa existia porque JPEG
   não tem canal alfa: sem ela, o fundo branco do arquivo virava um bloco no
   tema escuro. Só que a placa resolvia um problema criando outro — um
   retângulo branco recortado contra a superfície da faixa, visível nos dois
   temas e mais chamativo que a própria marca.

   Como palavra, a marca não tem fundo para esconder: herda o tema, fica
   nítida em qualquer tamanho, não pesa no payload e não depende de arquivo
   presente em disco. As cores saem do próprio logotipo, amostradas do
   `assets/cenarios_logo_full.jpeg`: azul #0092C3 e o "+" em terracota
   #CA6F43. */
.sinan-intro-marca {{
  justify-self: end;
  align-self: center;
  font-family: var(--fonte);
  /* Degrau da escala, não número solto: `TEXTO_XL` é o mesmo do valor de KPI.
     Escrevi 22px aqui na primeira versão e o `test_nenhum_tamanho_de_fonte_fixo`
     pegou — que é o teste fazendo exatamente o trabalho dele. */
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  letter-spacing: -.005em;
  line-height: 1;
  white-space: nowrap;
  color: #0092C3;
}}
.sinan-intro-marca-mais {{
  color: #CA6F43;
  font-weight: 900;
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


def titulo_painel(texto: str) -> str:
    """Cabeçalho de um painel.

    Existe porque `st.caption` não distingue papéis: o mesmo 14px peso 400
    servia para identificar um painel, rotular um widget e escrever a nota de
    procedência no rodapé. Ver `.titulo-painel` em :func:`css_layout`.
    """
    return f'<div class="titulo-painel">{escape(texto)}</div>'


def faixa_intro(titulo: str, *, escopo: str, cor: str) -> str:
    """Faixa de identificação: título à esquerda, marca à direita.

    O original tinha três colunas, com a bandeira de Pernambuco à esquerda e o
    título ao centro. A bandeira saiu: os dados são nacionais e ela lia como
    recorte geográfico, não como emissor.

    A marca é **texto**, não imagem — ver o comentário de `.sinan-intro-marca`
    em :func:`css_layout`. Por isso a função não recebe mais `logo`: não há
    arquivo a carregar, nada a fazer se ele faltar, e o painel não tem mais um
    modo "sem logotipo".
    """
    return (
        f'<div class="sinan-intro" style="--intro-accent:{escape(cor)};">'
        '<div class="sinan-intro-texto">'
        f'<h1 class="sinan-intro-titulo">{escape(titulo)}</h1>'
        f'<div class="sinan-intro-escopo">{escape(escopo)}</div>'
        "</div>"
        '<span class="sinan-intro-marca">Cenários'
        '<span class="sinan-intro-marca-mais">+</span></span>'
        "</div>"
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


#: Os botoes de zoom do mapa. Sao controles do mapbox que o deck.gl monta
#: dentro do proprio wrapper, e por isso precisam ser realocados para fora --
#: ver `script_travar_zoom`.
SELETOR_CONTROLE_ZOOM = ".mapboxgl-ctrl-group"


def script_travar_zoom() -> str:
    """Trava a roda do mouse no mapa e isola os botoes de zoom dele.

    O caminho declarativo não existe: o ``DeckGlJsonChart`` do Streamlit passa
    ``controller={true}`` fixo para o ``<DeckGL>`` e descarta o que vier no
    JSON do pydeck. Sem isto, rolar a página com o cursor sobre o mapa aplica
    zoom, o enquadramento se perde e só recarregando volta — e o mapa ocupa
    metade da tela, então acontece o tempo todo.

    A interceptação é na fase de captura, antes de o evento descer até o
    deck.gl, e **sem** ``preventDefault``: a rolagem normal da página segue
    acontecendo. Só o zoom morre.

    **Os botoes de zoom precisam de outro remedio, pelo mesmo motivo de
    fundo.** Eles sao controles do mapbox que o deck monta **dentro** do
    ``#deckgl-wrapper``, e o deck escuta o ponteiro no wrapper, na fase de
    captura. Com um poligono debaixo do botao, o clique dava zoom e **entrava
    no municipio**: a pagina recarregava com o enquadramento inicial e o zoom
    sumia junto. Sem poligono embaixo funcionava, o que fazia o defeito
    parecer aleatorio.

    ``stopPropagation`` nao resolve, e as duas tentativas mostram por que:

    - na **captura**, do documento, o evento morre antes de chegar ao botao --
      troca "as vezes nao funciona" por "nunca funciona";
    - na **borbulha**, no proprio controle, o deck ja viu o evento na captura,
      la em cima -- o botao funciona e o mapa navega junto, que era o defeito
      original.

    O que resta e tirar o controle de dentro do wrapper. Ele vai para o
    contentor do grafico, posicionado no mesmo lugar, e o clique deixa de
    atravessar territorio do deck. Verificado no navegador: zooma e nao
    navega.

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

  // Os botoes de zoom saem de dentro do wrapper do deck.
  //
  // Mover, e nao barrar o evento: ver a docstring: o deck escuta na captura,
  // entao qualquer `stopPropagation` ou chega tarde demais ou mata o botao.
  function realocar() {{
    var grupo = doc.querySelector('{SELETOR_CONTROLE_ZOOM}');
    var caixa = doc.querySelector('{SELETOR_MAPA}');
    if (!grupo || !caixa || grupo.__realocado) return;

    // O grupo anterior morre junto com o mapa que o Streamlit remontou, mas
    // como ele agora mora fora do wrapper, o Streamlit nao o leva embora.
    var antigo = caixa.querySelector(':scope > [data-zoom-realocado]');
    if (antigo) antigo.remove();

    var r = grupo.getBoundingClientRect();
    var rc = caixa.getBoundingClientRect();
    grupo.__realocado = true;
    grupo.setAttribute('data-zoom-realocado', '1');
    grupo.style.position = 'absolute';
    grupo.style.left = (r.left - rc.left) + 'px';
    grupo.style.top = (r.top - rc.top) + 'px';
    grupo.style.margin = '0';
    grupo.style.zIndex = '5';
    caixa.appendChild(grupo);
  }}

  realocar();
  // O Streamlit remonta o mapa a cada rerun, e os controles voltam dentro.
  new window.parent.MutationObserver(realocar).observe(doc.body, {{
    childList: true, subtree: true
  }});
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
