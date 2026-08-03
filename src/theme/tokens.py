"""Tokens de design.

Extraídos do dashboard em R, com três correções deliberadas — ver
docs/inventario-funcionalidades.md:

- alturas fixas viraram mínimos, para não quebrar em telas menores;
- escala tipográfica explícita, que o original não tinha;
- tema escuro, ausente no original.
"""

from __future__ import annotations

# --- Superfícies -----------------------------------------------------------
RAIO_CARD = "18px"
RAIO_PAINEL = "14px"
RAIO_PILL = "999px"

BORDA = "1px solid rgba(15,23,42,.10)"
BORDA_HOVER = "1px solid rgba(15,23,42,.16)"

SOMBRA_REPOUSO = "0 10px 26px rgba(2,6,23,.08)"
SOMBRA_HOVER = "0 18px 44px rgba(2,6,23,.12)"
SOMBRA_ATIVO = "0 22px 56px rgba(2,6,23,.14)"

FUNDO_CARD = "linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,255,255,.88))"
FUNDO_CARD_ESCURO = "linear-gradient(180deg, rgba(30,41,59,.96), rgba(15,23,42,.92))"

# --- Tipografia ------------------------------------------------------------
FONTE = (
    "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, "
    "'Apple Color Emoji', 'Segoe UI Emoji', sans-serif"
)

#: Escala tipográfica. O original usava tamanhos avulsos; aqui há uma razão fixa.
TEXTO_XS = "12px"
TEXTO_SM = "13px"
TEXTO_BASE = "14px"
TEXTO_LG = "17px"
TEXTO_XL = "24px"
TEXTO_TITULO = "clamp(18px, 2.1vw, 30px)"

# --- Semântica -------------------------------------------------------------
BOM = "#16A34A"
RUIM = "#B42318"
NEUTRO_OPACIDADE = ".74"

TEXTO_CLARO = "#0B1220"
TEXTO_ESCURO = "#E5E7EB"

# --- Espaçamento e layout --------------------------------------------------
GAP = "12px"
PADDING = "12px"
LARGURA_SIDEBAR = "380px"

#: No original eram alturas travadas (`height: 520px !important`). Viraram
#: mínimos para o layout sobreviver a telas baixas.
ALTURA_MIN_MAPA = "520px"
ALTURA_MIN_PAINEL = "560px"

#: Larguras do grid de KPIs por faixa de viewport.
GRID_KPI = (
    (0, "180px"),
    (1240, "210px"),
    (860, "200px"),
)

# --- Gráficos --------------------------------------------------------------
TOOLTIP_FUNDO = "rgba(17,24,39,.96)"
#: O original usava 10.5px, pequeno demais para leitura confortável.
TOOLTIP_TEXTO = "12px"
TOOLTIP_RAIO = "10px"

GRID_GRAFICO = {"left": 52, "right": 16, "top": 26, "bottom": 56, "containLabel": True}

#: Paleta categórica padrão, usada quando a doença não declara a sua.
PALETA_PADRAO = (
    "#0B8A8F",
    "#E39D00",
    "#1C5D99",
    "#4C9F70",
    "#6B3FA0",
    "#2E7D32",
    "#C62828",
    "#8C564B",
    "#546E7A",
    "#7F7F7F",
)
