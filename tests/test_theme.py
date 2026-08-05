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
