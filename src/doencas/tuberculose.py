"""Pacote de configuração da Tuberculose.

Segue o padrão de *disease pack* do projeto original: o core é único e cada
doença é só configuração. Cores, rótulos e ordem dos KPIs vêm daqui.
"""

from __future__ import annotations

from ..theme import cores

DOENCA = "TUBERCULOSE"
TITULO = "Tuberculose"

#: Cor por **métrica**, não por doença. As rampas do mapa saem daqui.
CORES = {
    "primary": "#ED853A",
    "secondary": "#A87D21",
    "casos": "#C1440A",
    "obitos": "#DC2626",
    "cura": "#16A34A",
    "pop": "#111827",
    "incid": "#92400E",
    "mortalidade": "#1D4ED8",
    "letalidade": "#6D28D9",
    "hiv_pos_pct": "#BE185D",
    "interrupcao_trat_pct": "#B45309",
    "casos_0_14": "#B45309",
    "taxa_det_0_14": "#92400E",
}

ROTULOS = {
    "casos": "Casos novos",
    "obitos": "Óbitos",
    "cura": "Curas",
    "pop": "População",
    "incid": "Incidência (por 100 mil hab.)",
    "mortalidade": "Taxa de mortalidade (por 100 mil hab.)",
    "letalidade": "Letalidade (%)",
    "casos_0_14": "Casos de 0 a 14 anos",
    "taxa_det_0_14": "Taxa de detecção 0–14 (por 100 mil hab.)",
    "hiv_pos_pct": "HIV positivo na testagem (%)",
    "interrupcao_trat_pct": "Interrupção de tratamento (%)",
}

#: Quais KPIs aparecem e em que ordem.
LAYOUT_KPI = (
    "incid",
    "casos",
    "mortalidade",
    "interrupcao_trat_pct",
    "hiv_pos_pct",
    "cura",
)

#: Métricas em que uma queda é boa. `cura` fica de fora de propósito.
BOM_SE_CAI = frozenset(
    {"casos", "obitos", "incid", "mortalidade", "letalidade",
     "casos_0_14", "taxa_det_0_14", "hiv_pos_pct", "interrupcao_trat_pct"}
)

#: Métricas exibidas com casas decimais.
TAXAS = frozenset(
    {"incid", "mortalidade", "letalidade", "taxa_det_0_14",
     "hiv_pos_pct", "interrupcao_trat_pct"}
)

#: Paletas explícitas do mapa, herdadas do original. Quando existem, têm
#: precedência sobre a rampa gerada a partir da cor da métrica.
PALETA_MAPA = {
    "casos": (
        "#F5A878", "#EF8450", "#E56028", "#D04010",
        "#B82E08", "#921800", "#5E0C00",
    ),
    "incid": (
        "#E8B87A", "#D49040", "#BA7018", "#9A5210",
        "#7A3808", "#5C2404", "#3A1400",
    ),
}

PALETA_BARRAS = (
    "#C1440A", "#DE501A", "#F07B42", "#A83208", "#E06030",
    "#902800", "#B84010", "#D86820", "#7A2100", "#601800",
)

PALETA_LINHAS = (
    "#ED853A", "#7C2D12", "#C2410C", "#98531B", "#EA580C",
    "#9A3412", "#B45309", "#D97706", "#A16207", "#431407",
)

#: Variáveis do SINAN exibidas no painel de composição.
VARIAVEIS_COMPOSICAO = (
    "TRATAMENTO", "HIV", "FORMA", "CS_RACA", "AGRAVALCOO",
    "SITUA_ENCE", "POP_RUA", "POP_SAUDE", "AGRAVDROGAS", "AGRAVTABACO",
)

ROTULOS_COMPOSICAO = {
    "TRATAMENTO": "Tipo de tratamento",
    "HIV": "Coinfecção HIV",
    "FORMA": "Forma clínica da tuberculose",
    "CS_RACA": "Raça/Cor",
    "AGRAVALCOO": "Agravo: alcoolismo",
    "SITUA_ENCE": "Situação de encerramento",
    "POP_RUA": "População em situação de rua",
    "POP_SAUDE": "Profissional de saúde",
    "AGRAVDROGAS": "Agravo: uso de drogas",
    "AGRAVTABACO": "Agravo: tabagismo",
}


def cor(metrica: str) -> str:
    return CORES.get(metrica, CORES["secondary"])


def rotulo(metrica: str) -> str:
    return ROTULOS.get(metrica, metrica)


def rampa_mapa(metrica: str) -> list[str]:
    """Rampa de 7 tons para o mapa.

    Usa a paleta explícita quando a métrica tem uma; senão deriva da cor base.
    """
    explicita = PALETA_MAPA.get(metrica)
    return list(explicita) if explicita else cores.rampa(cor(metrica))
