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


def test_card_marca_acessibilidade() -> None:
    html = c.kpi_card("Casos novos", "5.246", cor="#C1440A", selecionado=True)
    assert 'role="button"' in html
    assert 'tabindex="0"' in html
    assert 'aria-pressed="true"' in html
    assert "--kpi-accent:#C1440A" in html
    assert "is-selected" in html


def test_layout_kpi_so_referencia_metricas_conhecidas() -> None:
    for metrica in tb.LAYOUT_KPI:
        assert metrica in tb.CORES, f"{metrica} sem cor declarada"
        assert metrica in tb.ROTULOS, f"{metrica} sem rótulo declarado"
