"""Testes do sistema visual."""

from __future__ import annotations

import pytest

from src.doencas import tuberculose as tb
from src.theme import componentes as c
from src.theme import cores


def luminancia(hexa: str) -> float:
    r, g, b = cores.hex_para_rgb(hexa)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@pytest.mark.parametrize("metrica", sorted(tb.CORES))
def test_rampa_gerada_escurece_monotonicamente(metrica: str) -> None:
    """Guarda contra o defeito do fallback do R — ver src/theme/cores.py."""
    rampa = cores.rampa(tb.cor(metrica))
    assert len(rampa) == 7
    lums = [luminancia(t) for t in rampa]
    assert lums == sorted(lums, reverse=True), (
        f"rampa de {metrica} não é monotônica: {rampa}"
    )


def test_paleta_explicita_tem_precedencia() -> None:
    assert tb.rampa_mapa("casos") == list(tb.PALETA_MAPA["casos"])
    assert tb.rampa_mapa("mortalidade") == cores.rampa(tb.cor("mortalidade"))


def test_misturar_nos_extremos() -> None:
    assert cores.misturar("#FF0000", "#0000FF", 0.0) == "#FF0000"
    assert cores.misturar("#FF0000", "#0000FF", 1.0) == "#0000FF"


def test_contraste_usa_luminancia_relativa() -> None:
    # Amarelo é claro apesar do brilho ingênuo sugerir o contrário.
    assert cores.contraste_texto("#FFFF00") == "#111827"
    assert cores.contraste_texto("#1D4ED8") == "#FFFFFF"


def test_formatacao_pt_br() -> None:
    assert c.formatar_inteiro(5246) == "5.246"
    assert c.formatar_decimal(54.995115) == "55,00"
    assert c.formatar_decimal(1234.5, 1) == "1.234,5"
    assert c.formatar_inteiro(None) == "—"


def test_delta_inverte_semantica_para_cura() -> None:
    """Queda em casos é boa; queda em cura é ruim."""
    assert "kpi-bom" in c.delta(100, 150, bom_se_cai=True)
    assert "kpi-ruim" in c.delta(100, 150, bom_se_cai=False)
    assert "kpi-ruim" in c.delta(150, 100, bom_se_cai=True)
    assert "kpi-bom" in c.delta(150, 100, bom_se_cai=False)


def test_delta_sem_referencia_nao_renderiza() -> None:
    assert c.delta(100, None) == ""
    assert c.delta(None, 100) == ""
    assert "sem variação" in c.delta(100, 100)


def test_card_escapa_html() -> None:
    html = c.kpi_card("<script>alert(1)</script>", "5", cor="#000000")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_card_e_apenas_apresentacao() -> None:
    """O card não finge ser um controle.

    No original era um `div` com `role="button"` e um handler de JS — uma
    parada de tabulação que o teclado não acionava. Aqui quem recebe o clique
    é um `<button>` de verdade (ver `kpi_clicavel`), e o card fica marcado
    como `aria-hidden` para o leitor de tela não anunciar o conteúdo duas
    vezes.
    """
    html = c.kpi_card("Casos novos", "5.246", cor="#C1440A", selecionado=True)
    assert 'aria-hidden="true"' in html
    assert "role=" not in html
    assert "tabindex" not in html
    assert "--kpi-accent:#C1440A" in html
    assert "is-selected" in html


def test_css_posiciona_o_botao_sobre_o_card() -> None:
    """Sem essa regra o botão aparece abaixo do card, e o clique não cobre."""
    css = c.css_base()
    assert '[class*="st-key-kpi-"]' in css
    assert "position: absolute" in css


def test_layout_kpi_so_referencia_metricas_conhecidas() -> None:
    for metrica in tb.LAYOUT_KPI:
        assert metrica in tb.CORES, f"{metrica} sem cor declarada"
        assert metrica in tb.ROTULOS, f"{metrica} sem rótulo declarado"


# ---------------------------------------------------------------------------
# Card clicável
# ---------------------------------------------------------------------------
# `kpi_clicavel` recebe o módulo `streamlit` por parâmetro justamente para
# poder ser exercitado com um dublê, sem subir a aplicação.


class _ContainerFalso:
    def __init__(self, registro, chave):
        registro.append(chave)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _StreamlitFalso:
    """Dublê mínimo: registra o que foi chamado e devolve o clique programado."""

    def __init__(self, clicado: bool = False):
        self.containers: list[str] = []
        self.markdown_html: list[str] = []
        self.botoes: list[dict] = []
        self._clicado = clicado

    def container(self, key=None):
        return _ContainerFalso(self.containers, key)

    def markdown(self, corpo, unsafe_allow_html=False):
        self.markdown_html.append(corpo)

    def button(self, rotulo, **kwargs):
        self.botoes.append({"rotulo": rotulo, **kwargs})
        return self._clicado


def _render(clicado=False, **kwargs):
    falso = _StreamlitFalso(clicado)
    resultado = c.kpi_clicavel(
        falso, "incid", "Incidência", "40,42", cor="#92400E", **kwargs
    )
    return falso, resultado


def test_container_usa_chave_que_o_css_alcanca() -> None:
    falso, _ = _render()
    assert falso.containers == ["kpi-incid"]


def test_chave_do_botao_nao_colide_com_a_do_container() -> None:
    """`st-key-kpi-` casaria com `st-key-kpi-btn-`, e o botão se ancoraria
    no próprio contêiner em vez de cobrir o card."""
    falso, _ = _render()
    chave = falso.botoes[0]["key"]
    assert not chave.startswith("kpi-")
    assert chave == "selkpi-incid"


def test_botao_recebe_a_metrica_no_callback() -> None:
    registrado = []
    falso, _ = _render(ao_clicar=registrado.append)
    botao = falso.botoes[0]
    assert botao["args"] == ("incid",)
    botao["on_click"](*botao["args"])
    assert registrado == ["incid"]


def test_botao_tem_rotulo_acessivel() -> None:
    """O card é aria-hidden; o nome acessível tem de vir do botão."""
    falso, _ = _render()
    assert "Incidência" in falso.botoes[0]["rotulo"]


def test_devolve_true_quando_clicado() -> None:
    _, resultado = _render(clicado=True)
    assert resultado is True
    _, resultado = _render(clicado=False)
    assert resultado is False


def test_estado_selecionado_chega_no_html() -> None:
    falso, _ = _render(selecionado=True)
    assert "is-selected" in falso.markdown_html[0]
    falso, _ = _render(selecionado=False)
    assert "is-selected" not in falso.markdown_html[0]


# ---------------------------------------------------------------------------
# Os 11 KPIs
# ---------------------------------------------------------------------------
# `LAYOUT_KPI` da tuberculose exibe 6, que é a paridade com o original. Os
# outros 5 existem para as demais doenças (hanseníase usa 0-14, por exemplo) e
# precisam renderizar mesmo sem estar no layout de hoje — senão o defeito só
# aparece quando a próxima doença entrar.

TODOS_OS_KPIS = (
    "casos",
    "obitos",
    "cura",
    "pop",
    "incid",
    "mortalidade",
    "letalidade",
    "casos_0_14",
    "taxa_det_0_14",
    "hiv_pos_pct",
    "interrupcao_trat_pct",
)


def test_pack_cobre_os_onze_kpis() -> None:
    from src.data.kpis import Kpis

    campos = {c for c in Kpis.__dataclass_fields__ if not c.startswith("_")}
    assert set(TODOS_OS_KPIS) <= campos, "métrica listada aqui não existe em Kpis"

    for metrica in TODOS_OS_KPIS:
        assert metrica in tb.CORES, f"{metrica} sem cor"
        assert metrica in tb.ROTULOS, f"{metrica} sem rótulo"


@pytest.mark.parametrize("metrica", TODOS_OS_KPIS)
def test_todos_os_kpis_renderizam(metrica: str) -> None:
    falso = _StreamlitFalso()
    valor = 12.345 if metrica in tb.TAXAS else 12345
    texto = (
        c.formatar_decimal(valor) if metrica in tb.TAXAS else c.formatar_inteiro(valor)
    )
    c.kpi_clicavel(
        falso,
        metrica,
        tb.rotulo(metrica),
        texto,
        cor=tb.cor(metrica),
        badge_delta=c.delta(valor, valor * 0.9, taxa=metrica in tb.TAXAS),
    )
    html = falso.markdown_html[0]
    assert tb.rotulo(metrica) in html
    assert texto in html
    assert tb.cor(metrica) in html


@pytest.mark.parametrize("metrica", TODOS_OS_KPIS)
def test_rampa_de_mapa_existe_para_todo_kpi(metrica: str) -> None:
    """O mapa da semana 3 pinta pela métrica ativa, qualquer que seja."""
    rampa = tb.rampa_mapa(metrica)
    assert len(rampa) == 7
    assert all(t.startswith("#") for t in rampa)


def test_taxas_e_contagens_formatam_diferente() -> None:
    assert c.formatar_decimal(1234.5) == "1.234,50"
    assert c.formatar_inteiro(1234.5) == "1.234"
    for metrica in TODOS_OS_KPIS:
        e_taxa = metrica in tb.TAXAS
        assert e_taxa == ("%" in tb.rotulo(metrica) or "por 100 mil" in tb.rotulo(metrica)), (
            f"{metrica}: rótulo e formatação discordam"
        )


# ---------------------------------------------------------------------------
# Layout e faixa de intro
# ---------------------------------------------------------------------------


def test_css_de_layout_fixa_a_largura_da_sidebar() -> None:
    from src.theme import tokens

    css = c.css_layout()
    assert tokens.LARGURA_SIDEBAR in css
    assert 'section[data-testid="stSidebar"]' in css


def test_paineis_usam_altura_minima_e_nao_fixa() -> None:
    """O original travava `height`, o que quebra em telas baixas.

    Procurar a substring `height: 520px` não serve: ela casa dentro de
    `min-height: 520px`, que é exatamente o que queremos. A checagem precisa
    exigir que nenhum `height` apareça sem um prefixo `min-`/`max-`/`line-`.
    """
    import re

    css = c.css_layout()
    assert "min-height" in css

    # A regra vale para os painéis, não para o CSS inteiro: o quadradinho de
    # cor da legenda tem altura fixa de propósito.
    blocos = re.findall(r"\.sinan-painel[^{]*\{([^}]*)\}", css)
    assert blocos, "não achei as regras de painel"
    nus = [
        achado
        for bloco in blocos
        for achado in re.findall(r"(?<![-\w])height\s*:\s*[^;]+;", bloco)
    ]
    assert not nus, f"altura fixa em painel: {nus}"


def test_faixa_de_intro_sem_imagens_ocupa_a_largura_toda() -> None:
    html = c.faixa_intro("Tuberculose")
    assert "marcas-0" in html
    assert "<img" not in html
    assert "Tuberculose" in html


def test_faixa_de_intro_com_logotipo() -> None:
    html = c.faixa_intro("Tuberculose", logo="data:image/jpeg;base64,BBB")
    assert "marcas-1" in html
    assert html.count("<img") == 1
    assert "sinan-intro-logo" in html


def test_bandeira_nao_volta_pela_porta_dos_fundos() -> None:
    """A bandeira de PE saiu porque os dados são nacionais.

    Ela ficava à esquerda do título, onde lia como recorte geográfico e não
    como emissor — ao lado de um mapa do Brasil, isso desmente o próprio
    painel. Como o arranjo veio copiado do projeto em R, este teste existe
    para o resquício não voltar junto com a próxima cópia.
    """
    assert not hasattr(c, "bandeira")
    assert "bandeira" not in c.css_layout()
    assert "bandeira" not in c.faixa_intro("Tuberculose", logo="data:b")


def test_placa_encolhe_ao_conteudo() -> None:
    """A célula do grid estica por padrão e sobrava branco ao lado da imagem."""
    import re

    bloco = re.search(r"\.sinan-intro-marca\s*\{([^}]*)\}", c.css_layout())
    assert bloco
    assert "justify-self: end" in bloco.group(1)
    assert "width: fit-content" in bloco.group(1)


def test_marca_sem_alfa_ganha_placa_branca() -> None:
    """Os arquivos são JPEG; no tema escuro o fundo branco viraria um bloco."""
    html = c.faixa_intro("T", logo="data:image/jpeg;base64,AAA")
    assert "sinan-intro-marca" in html
    assert "background: #FFFFFF" in c.css_layout()


@pytest.mark.parametrize(
    "kwargs,esperado,imagens",
    [
        ({"logo": "data:l"}, "marcas-1", 1),
        ({}, "marcas-0", 0),
    ],
)
def test_faixa_se_adapta_ao_logotipo(kwargs, esperado, imagens) -> None:
    """Sem logotipo não há segunda coluna para deixar vazia."""
    html = c.faixa_intro("Tuberculose", **kwargs)
    assert esperado in html
    assert html.count("<img") == imagens
    assert "Tuberculose" in html
    assert "<span></span>" not in html, "não deve sobrar célula vazia"


def test_faixa_de_intro_escapa_o_titulo() -> None:
    assert "<script>" not in c.faixa_intro("<script>alert(1)</script>")


def test_marcas_ausentes_sao_reportadas() -> None:
    """O arquivo não veio na entrega em R; o app avisa em vez de só omitir."""
    from src.theme import marcas

    disponiveis = marcas.disponiveis()
    assert set(disponiveis) == {"logo"}
    for nome, presente in disponiveis.items():
        assert isinstance(presente, bool)
    # `faltando` tem de ser coerente com `disponiveis`
    assert len(marcas.faltando()) == sum(1 for v in disponiveis.values() if not v)


# ---------------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------------
# Claro é o padrão (.streamlit/config.toml); escuro é a alternativa, pelo menu
# do Streamlit. Os componentes próprios não sabem qual está ativo: derivam a
# superfície de `currentColor`, que o Streamlit já inverte.


def _sem_comentarios(css: str) -> str:
    """Remove blocos `/* ... */` — as regras é que importam, não a prosa."""
    import re

    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_css_nao_tenta_detectar_o_tema() -> None:
    """`prefers-color-scheme` segue o sistema operacional, não o Streamlit.

    Com o tema forçado para claro e o sistema em escuro, uma regra dessas
    pintaria os cards de escuro sobre uma página clara. A única media query de
    esquema de cor permitida é a de movimento reduzido, que não é sobre cor.
    """
    regras = _sem_comentarios(c.css_base() + c.css_layout())
    esquemas = [
        linha.strip()
        for linha in regras.splitlines()
        if "prefers-color-scheme" in linha
    ]
    assert not esquemas, f"regra que segue o sistema, não o Streamlit: {esquemas}"


def test_superficies_derivam_da_cor_do_texto() -> None:
    """É o que faz o card acompanhar o tema sem detectá-lo."""
    css = c.css_base()
    assert "--superficie:" in css
    assert "currentColor" in css
    assert "color: inherit" in css


#: Seletores que podem ter cor opaca, com o motivo.
#: A placa da marca é branca de propósito: os arquivos de logotipo são JPEG,
#: sem canal alfa, e no tema escuro o fundo branco da própria imagem viraria
#: um bloco. Uma placa explícita é o tratamento padrão para logotipo sem alfa
#: e fica igual nos dois temas.
OPACOS_PERMITIDOS = (".sinan-intro-marca",)


def test_css_nao_fixa_fundo_claro_nem_escuro() -> None:
    """Qualquer cor opaca de superfície quebraria um dos dois temas.

    A checagem identifica **a qual seletor** a cor pertence, em vez de tentar
    recortar blocos por regex: assim uma exceção nova aparece nomeada na
    mensagem de falha, e não como um `#FFFFFF` solto sem contexto.
    """
    import re

    regras = _sem_comentarios(c.css_base() + c.css_layout())
    infratores = []
    for bloco in re.finditer(r"([^{}]+)\{([^}]*)\}", regras):
        seletor, corpo = bloco.group(1).strip(), bloco.group(2)
        if not re.search(r"background(?:-color)?\s*:\s*(#|rgb\()", corpo):
            continue
        if not any(p in seletor for p in OPACOS_PERMITIDOS):
            infratores.append(seletor[:60])
    assert not infratores, f"superfície opaca sem justificativa: {infratores}"


def test_config_do_streamlit_define_claro_como_padrao() -> None:
    import tomllib
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    assert caminho.exists(), "falta .streamlit/config.toml"

    cfg = tomllib.loads(caminho.read_text(encoding="utf-8"))
    tema = cfg["theme"]
    assert tema["base"] == "light"
    assert tema["backgroundColor"].upper() == "#FFFFFF"
    assert "dark" in tema, "o escuro precisa continuar disponível como alternativa"


def test_marca_vem_do_repositorio() -> None:
    """O logotipo é versionado em `assets/`, não em `data/`.

    É identidade visual, não dado: não muda quando o SINAN atualiza, e sem ele
    o dashboard fica descaracterizado em qualquer clone novo. `data/` é
    ignorado pelo git de propósito, por causa dos 888 MB.
    """
    from src.theme import marcas

    caminho = marcas.onde(marcas.LOGO)
    assert caminho, "logotipo ausente"
    assert caminho.parent.name == "assets", f"{caminho} fora de assets/"


def test_data_support_continua_valendo_como_alternativa() -> None:
    """É onde o projeto em R procurava, e para onde alguém copiaria."""
    from src.theme import marcas

    nomes = [d.name for d in marcas.diretorios()]
    assert nomes.index("assets") < nomes.index("support"), "assets tem precedência"
    assert "support" in nomes
