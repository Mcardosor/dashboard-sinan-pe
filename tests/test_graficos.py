"""Gráficos do painel direito.

Altair e não ECharts: `st.altair_chart` tem evento de clique nativo, o que o
ranking precisa para navegar o mapa. Verificado com clique real antes da
escolha — ter na assinatura e disparar são coisas diferentes, lição da
semana 3.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import graficos
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import tuberculose as tb

ESCOPO = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")
COR = tb.cor("casos")


def _mensal():
    return leitura.serie_mensal(ESCOPO).rename(columns={"casos": "valor"})


def test_serie_mensal_cobre_o_ano() -> None:
    assert len(_mensal()) == 12


def test_serie_anual_cobre_a_historia() -> None:
    serie = leitura.serie_anual(ESCOPO, "casos")
    assert len(serie) >= 15
    assert serie["ano"].is_monotonic_increasing


def test_mensal_e_anual_divergem_por_criterio_geografico() -> None:
    """`_cache_ts` é por notificação e `incidence` por residência.

    Medido no SINAN bruto — ver contrato-dados, armadilha 7. O teste fixa a
    divergência: se um dia os dois passarem a bater, é porque a fonte mudou e
    o aviso na tela deixou de ser necessário.
    """
    mensal = _mensal()["valor"].sum()
    anual = leitura.serie_anual(ESCOPO, "casos").query("ano == 2024")["valor"].iloc[0]
    assert mensal != anual, "se convergiram, revisar o aviso na interface"
    assert abs(mensal - anual) / anual < 0.01, "divergência maior que o esperado em PE"


def test_grafico_mensal_usa_a_cor_da_metrica() -> None:
    g = graficos.evolucao_mensal(_mensal(), rotulo="Casos", cor=COR)
    assert g.mark["type"] == "bar"
    assert g.mark["color"] == COR


def test_grafico_anual_destaca_o_ano_selecionado() -> None:
    serie = leitura.serie_anual(ESCOPO, "casos")
    g = graficos.evolucao_anual(serie, rotulo="Casos", cor=COR, ano=2024)
    # O destaque é por opacidade: o ano ativo opaco, o histórico recuado.
    assert "opacity" in g.encoding.to_dict()


@pytest.mark.parametrize("construtor", ["mensal", "anual"])
def test_serie_vazia_mostra_recado_em_vez_de_painel_branco(construtor: str) -> None:
    vazio = pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"])
    g = (
        graficos.evolucao_mensal(vazio, rotulo="Casos", cor=COR)
        if construtor == "mensal"
        else graficos.evolucao_anual(vazio, rotulo="Casos", cor=COR, ano=2024)
    )
    assert g.mark["type"] == "text"


def test_tema_nao_pinta_fundo() -> None:
    """O painel já tem superfície própria; fundo opaco brigaria com o tema."""
    import altair as alt

    g = graficos.tema(
        alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    )
    assert g.config.view.fill is None


def test_tema_herda_a_cor_do_texto() -> None:
    """Igual aos cards: `currentColor` acompanha o tema sem detectá-lo."""
    import altair as alt

    g = graficos.tema(
        alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    )
    assert g.config.axis.labelColor == "currentColor"


def test_aviso_de_notificacao_existe_e_explica() -> None:
    assert "notificação" in graficos.AVISO_NOTIFICACAO
    assert "residência" in graficos.AVISO_NOTIFICACAO
