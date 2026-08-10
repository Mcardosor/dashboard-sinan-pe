"""Indicadores de qualidade do programa de tuberculose.

Nenhum dos dois painéis em R exibe estes números — conferido na tela de
`TB_BR` e de `TB_PE`. O dado veio nos parquets e ficou sem uso, então isto é
ganho sobre o original, não paridade.
"""

from __future__ import annotations

import pytest

from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack
from src.theme import componentes as c

ESCOPOS = [
    Escopo(pack.DOENCA, 2024, "BR"),
    Escopo(pack.DOENCA, 2024, "UF", uf="PE"),
]


@pytest.mark.parametrize("esc", ESCOPOS, ids=lambda e: e.uf or "BR")
def test_devolve_os_dois_indicadores_com_proporcao(esc: Escopo) -> None:
    itens = leitura.indicadores_programa(esc)
    assert [i["chave"] for i in itens] == ["contatos", "cultura"]
    for item in itens:
        assert item["pct"] is not None, f"{item['chave']} sem proporção"
        assert 0 <= item["pct"] <= 100
        # A proporção precisa ser exatamente o que os componentes dizem.
        esperado = item["numerador"] / item["denominador"] * 100
        assert item["pct"] == pytest.approx(esperado)


def test_recorte_sem_dado_nao_some_da_lista() -> None:
    """Ausência é informação: o card aparece com "—", não desaparece."""
    itens = leitura.indicadores_programa(
        Escopo(pack.DOENCA, 2024, "MUN", uf="MG", mun="311280")
    )
    assert len(itens) == 2
    assert all(i["pct"] is None for i in itens)


def test_nao_divide_por_zero() -> None:
    """Denominador zero ou ausente vira `None`, nunca exceção."""
    for esc in (Escopo(pack.DOENCA, 1999, "BR"), Escopo(pack.DOENCA, 2024, "MUN", uf="MG", mun="311280")):
        for item in leitura.indicadores_programa(esc):
            assert item["pct"] is None or item["pct"] >= 0


def test_ano_dos_indicadores_diverge_do_resto() -> None:
    """A armadilha que motivou o aviso na tela.

    Estes arquivos vêm de outra extração. Em 2025 trazem 161.739 contatos
    identificados enquanto `incidence` registra 1.773 casos novos — 91
    contatos por caso. Em 2024, com os dois fechados, a razão fica em 2.
    """
    from src.data import kpis as calc

    def razao(ano: int) -> float:
        esc = Escopo(pack.DOENCA, ano, "BR")
        contatos = leitura.indicadores_programa(esc)[0]["denominador"]
        return contatos / calc.calcular(esc).casos

    assert razao(2024) < 5, "2024 deveria ser plausível"
    assert razao(2025) > 20, "2025 deveria denunciar a divergência de extração"


def test_card_sem_dado_mostra_travessao_e_barra_vazia() -> None:
    html = c.indicador_programa("Contatos", None, None, None, cor="#000")
    assert "—" in html
    assert "width:0.0%" in html
    assert "sem dado neste recorte" in html


def test_card_formata_milhar_em_portugues() -> None:
    html = c.indicador_programa("Contatos", 70.1, 118597, 169207, cor="#000")
    assert "70,1%" in html
    assert "118.597 de 169.207" in html


def test_barra_nao_estoura_com_proporcao_acima_de_cem() -> None:
    """Pode acontecer se numerador e denominador vierem de recortes distintos."""
    html = c.indicador_programa("X", 140.0, 14, 10, cor="#000")
    assert "width:100.0%" in html
