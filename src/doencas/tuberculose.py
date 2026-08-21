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
    "cura_pct": "#16A34A",
    # Cinza médio e não quase-preto: `pop` em #111827 dava 2,4:1 de contraste
    # no tema escuro. Não é exibido como card hoje, mas a rampa do mapa usa a
    # cor da métrica.
    "pop": "#6B7280",
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
    "cura_pct": "Proporção de cura (%)",
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
    "cura_pct",
)

#: KPIs de proporção que mostram a fração de onde saem, sob o valor.
#:
#: "Curas: 49.114 ↓ 6.004 vs ano anterior" engana sem o denominador — os casos
#: também caíram. Com a fração à vista, o card diz a proporção e não esconde os
#: absolutos, que é o que o card antigo entregava.
FRACAO_KPI = {"cura_pct": ("cura", "casos")}

#: Métricas que o mapa e o ranking sabem desenhar.
#:
#: Ficam de fora `interrupcao_trat_pct` e `hiv_pos_pct`: as duas vêm do
#: `sinan_landing`, que o leitor consulta uma geografia por vez — serve para o
#: card, não para pintar 27 UFs de uma vez. Enquanto isso não mudar, elas não
#: entram no seletor, porque oferecer uma opção que leva a um painel vazio é
#: pior que não oferecer.
#: Métricas oferecidas no mapa.
#:
#: `cura_pct` e não `cura`: coroplético pinta **área**, e área não tem relação
#: com população. Com a contagem crua, São Paulo ficava no tom mais escuro por
#: ser São Paulo — o mapa de curas era, na prática, um mapa de população.
#: Proporção é comparável entre lugares de tamanhos diferentes, que é a razão
#: de existir de um coroplético. A contagem continua no card, com denominador.
METRICAS_MAPA = ("incid", "casos", "mortalidade", "cura_pct")


#: Métricas em que uma queda é boa. `cura` fica de fora de propósito.
BOM_SE_CAI = frozenset(
    {"casos", "obitos", "incid", "mortalidade", "letalidade",
     "casos_0_14", "taxa_det_0_14", "hiv_pos_pct", "interrupcao_trat_pct"}
)

#: Métricas exibidas com casas decimais.
TAXAS = frozenset(
    {"incid", "mortalidade", "letalidade", "taxa_det_0_14",
     "hiv_pos_pct", "interrupcao_trat_pct", "cura_pct"}
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

def cor(metrica: str) -> str:
    return CORES.get(metrica, CORES["secondary"])


#: Rótulos curtos, para controles onde o nome inteiro não cabe.
#:
#: Só existem os que precisam: no seletor de métrica do mapa, "Taxa de
#: mortalidade (por 100 mil hab.)" empurrava os quatro botões para duas linhas.
#: A unidade não se perde — ela aparece na legenda do mapa e no título do
#: ranking, que é onde o número de fato é lido.
ROTULOS_CURTOS = {
    "incid": "Incidência",
    "mortalidade": "Mortalidade",
    "cura_pct": "Cura",
}


def rotulo(metrica: str) -> str:
    return ROTULOS.get(metrica, metrica)


def rotulo_curto(metrica: str) -> str:
    """Nome enxuto para botão; cai no completo quando não há versão curta."""
    return ROTULOS_CURTOS.get(metrica, rotulo(metrica))


def rampa_mapa(metrica: str) -> list[str]:
    """Rampa de 7 tons para o mapa.

    Usa a paleta explícita quando a métrica tem uma; senão deriva da cor base.
    """
    explicita = PALETA_MAPA.get(metrica)
    return list(explicita) if explicita else cores.rampa(cor(metrica))


#: Variáveis do SINAN oferecidas no painel de composição, agrupadas.
#:
#: O painel em R expõe nove; aqui são vinte e quatro, porque o dado já está
#: nos mesmos parquets e não custa nada a mais. Só entram as que dá para
#: rotular com segurança — errar o nome de uma variável de saúde é pior que
#: omiti-la.
#:
#: Ficam de fora, de propósito:
#: - ``NU_COMU_EX`` (contatos examinados) e ``EXTRAPUL_O``: numéricas, com 141
#:   e 1.587 valores distintos. O painel deles mostra a primeira; viraria uma
#:   parede de barras.
#: - ``BACILOSC_1``..``BACILOSC_6``: baciloscopia de acompanhamento mês a mês,
#:   redundante com ``BACILOSC_E``.
#: - ``MIGRADO_W``, ``NDUPLIC_N``, ``MUN_TRANSF``, ``AGRAVOUTDE``: controle do
#:   sistema, ou volume pequeno demais para significar algo.
#: - ``IN_VINCULA``: rótulos ambíguos ("vinculado"/"não vinculado") sem
#:   documentação que permita explicar ao usuário o que está sendo contado.
VARIAVEIS: dict[str, dict[str, str]] = {
    "Perfil": {
        "CS_RACA": "Raça/cor",
        "CS_ESCOL_N": "Escolaridade",
        "CS_GESTANT": "Gestante",
    },
    "Populações específicas": {
        "POP_RUA": "População em situação de rua",
        "POP_LIBER": "População privada de liberdade",
        "POP_IMIG": "População imigrante",
        "POP_SAUDE": "Profissional de saúde",
        "BENEF_GOV": "Beneficiário de programa do governo",
    },
    "Agravos associados": {
        "AGRAVAIDS": "Agravo: aids",
        "AGRAVALCOO": "Agravo: alcoolismo",
        "AGRAVDIABE": "Agravo: diabetes",
        "AGRAVDOENC": "Agravo: doença mental",
        "AGRAVOUTRA": "Agravo: outro",
    },
    "Clínica e diagnóstico": {
        "FORMA": "Forma clínica",
        "HIV": "Coinfecção HIV",
        "BACILOSC_E": "Baciloscopia de escarro",
        "CULTURA_ES": "Cultura de escarro",
        "RAIOX_TORA": "Raio-X de tórax",
        "HISTOPATOL": "Histopatologia",
    },
    "Tratamento e desfecho": {
        # No SINAN o campo é o tipo de *entrada* — as categorias são "Caso
        # novo", "Pós-óbito", "Não sabe". O painel em R chama de "Tipo de
        # tratamento", que descreve mal o que está ali.
        "TRATAMENTO": "Tipo de entrada",
        "TRATSUP_AT": "Tratamento diretamente observado",
        "SITUA_ENCE": "Situação de encerramento",
        "DOENCA_TRA": "Doença relacionada ao trabalho",
        "TRANSF": "Transferência",
    },
}


def variaveis_planas() -> dict[str, str]:
    """``código -> rótulo``, na ordem dos grupos."""
    return {c: r for grupo in VARIAVEIS.values() for c, r in grupo.items()}


def grupo_da(codigo: str) -> str:
    """Grupo a que a variável pertence, para agrupar o seletor."""
    for grupo, itens in VARIAVEIS.items():
        if codigo in itens:
            return grupo
    return "Outras"


#: Explicação de cada KPI, mostrada ao passar o cursor.
#:
#: O que se explica aqui é sobretudo o **denominador**, que é onde mora a
#: ambiguidade: "Interrupção de tratamento (%)" não diz percentual sobre o
#: quê, e a resposta muda o número em quase quatro pontos. Os textos saem das
#: fórmulas em `src/data/kpis.py` — mudou lá, muda aqui.
DESCRICOES = {
    "incid": (
        "Casos novos por 100 mil habitantes, por UF de residência. "
        "Permite comparar lugares de tamanhos diferentes."
    ),
    "casos": "Total de casos novos notificados no ano, por UF de residência.",
    "obitos": "Óbitos com a doença como causa básica, vindos do SIM.",
    "cura": "Encerramentos por cura no ano.",
    "cura_pct": (
        "Encerramentos por cura sobre os casos novos do mesmo ano. "
        "É aproximação: o tratamento leva cerca de seis meses, então parte "
        "dos casos de um ano só encerra no seguinte. O boletim do MS usa "
        "coorte fechada e publica 65,5% para 2024, sobre um subconjunto — "
        "só os casos confirmados por critério laboratorial."
    ),
    "pop": "População estimada do recorte.",
    "mortalidade": (
        "Óbitos por 100 mil habitantes. A fonte é o SIM, não o SINAN — "
        "`casos_obitos` do dataset de incidência é zero para tuberculose."
    ),
    "letalidade": "Óbitos como percentual dos casos: dos que adoeceram, quantos morreram.",
    "casos_0_14": "Casos novos em menores de 15 anos.",
    "taxa_det_0_14": "Casos de 0 a 14 anos por 100 mil habitantes dessa faixa.",
    "hiv_pos_pct": (
        "Percentual de HIV positivo entre os **testados** — o denominador é "
        "positivos mais negativos. Quem não fez o teste ou está em andamento "
        "fica de fora, então isto mede positividade, não cobertura de testagem."
    ),
    "interrupcao_trat_pct": (
        "Percentual de abandono sobre **todos os encerramentos**, incluindo os "
        "não avaliados. Reproduz a regra do painel em R. Pelo critério do "
        "Ministério da Saúde — somando abandono primário e tirando os não "
        "avaliados do denominador — o valor sobe cerca de 4 pontos. "
        "Ver docs/contrato-dados.md."
    ),
}


def descricao(metrica: str) -> str | None:
    return DESCRICOES.get(metrica)


#: Indicadores de qualidade do programa, com tudo que a tela precisa.
#:
#: Vive aqui e não no core de leitura porque rótulo, descrição e cor são
#: específicos da doença — é o padrão de *disease pack*. O core só resolve
#: `numerador/denominador → proporção` a partir desta tabela.
INDICADORES_PROGRAMA = (
    {
        "chave": "contatos",
        "leitor": "indicador_tb_contatos",
        "rotulo": "Contatos examinados",
        "numerador": "examinados",
        "denominador": "identificados",
        "cor": CORES["cura"],
        "descricao": (
            "Dos contatos identificados de casos novos, quantos foram "
            "efetivamente examinados. Mede busca ativa: contato não examinado "
            "é transmissão que segue invisível."
        ),
    },
    {
        "chave": "cultura",
        "leitor": "indicador_tb_cultura",
        "rotulo": "Cultura em retratamento",
        "numerador": "cultura",
        "denominador": "retratamento",
        "cor": CORES["incid"],
        "descricao": (
            "Dos casos em retratamento, quantos tiveram cultura realizada. "
            "É o exame que identifica resistência a medicamento, e retratamento "
            "é justamente onde a resistência é mais provável."
        ),
    },
)
