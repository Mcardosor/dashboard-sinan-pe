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
:root {{
  --fonte: {tokens.FONTE};
  --texto: {tokens.TEXTO_CLARO};
  --fundo-card: {tokens.FUNDO_CARD};
  --borda: {tokens.BORDA};
  --sombra: {tokens.SOMBRA_REPOUSO};
  --sombra-hover: {tokens.SOMBRA_HOVER};
  --sombra-ativo: {tokens.SOMBRA_ATIVO};
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --texto: {tokens.TEXTO_ESCURO};
    --fundo-card: {tokens.FUNDO_CARD_ESCURO};
    --borda: 1px solid rgba(148,163,184,.18);
  }}
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
  background: var(--fundo-card);
  box-shadow: var(--sombra);
  color: var(--texto);
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
    radial-gradient(220px 120px at 85% 0%, rgba(255,255,255,.35), transparent 55%);
}}
.kpi-card:hover {{ border-color: rgba(15,23,42,.16); box-shadow: var(--sombra-hover); }}
.kpi-card:hover::after {{ opacity: 1; }}
.kpi-card.is-selected {{
  border-color: color-mix(in srgb, var(--kpi-accent) 60%, rgba(15,23,42,.18));
  box-shadow: var(--sombra-ativo),
              0 0 0 2px color-mix(in srgb, var(--kpi-accent) 28%, transparent);
}}
.kpi-card.is-selected::after {{ opacity: 1; }}
.kpi-card:focus-visible {{
  outline: none;
  border-color: color-mix(in srgb, var(--kpi-accent) 55%, rgba(15,23,42,.18));
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
.kpi-title {{
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
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
    """Card de KPI.

    A cor entra como variável CSS inline (``--kpi-accent``), o que permite um
    único bloco de estilo servir todas as métricas.
    """
    classes = "kpi-card is-selected" if selecionado else "kpi-card"
    sub = (
        f'<div class="kpi-sub">{escape(subtitulo)}</div>'
        if subtitulo
        else ""
    )
    return (
        f'<div class="{classes}" style="--kpi-accent:{escape(cor)};"'
        f' role="button" tabindex="0"'
        f' aria-pressed="{"true" if selecionado else "false"}"'
        f' aria-label="Selecionar métrica: {escape(titulo)}">'
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
