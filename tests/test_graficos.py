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


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _ranking(nivel="BR", uf=None, metrica="incid", top_n=15):
    return leitura.ranking(Escopo("TUBERCULOSE", 2024, nivel, uf=uf), metrica, top_n)


def test_ranking_no_brasil_lista_ufs() -> None:
    r = _ranking()
    assert len(r) == 15
    assert r["chave"].str.len().eq(2).all(), "no Brasil a chave é a sigla da UF"


def test_ranking_numa_uf_lista_municipios_com_nome() -> None:
    r = _ranking("UF", "PE")
    assert r["chave"].str.len().eq(6).all()
    assert (r["nome"] != r["chave"]).all(), "o nome deve ser resolvido, não o código"


def test_ranking_vem_ordenado_do_maior() -> None:
    valores = _ranking("UF", "PE")["valor"]
    assert valores.is_monotonic_decreasing


def test_empate_e_desempatado_pelo_nome() -> None:
    """Sem critério estável, a ordem varia entre execuções e confunde."""
    r1 = _ranking("UF", "PE", "casos", 30)
    r2 = _ranking("UF", "PE", "casos", 30)
    assert r1["chave"].tolist() == r2["chave"].tolist()


@pytest.mark.parametrize("top_n", [5, 15, 30])
def test_top_n_e_respeitado(top_n: int) -> None:
    assert len(_ranking("UF", "PE", top_n=top_n)) == top_n


def test_ranking_usa_a_mesma_fonte_do_mapa() -> None:
    """Ler de lugares diferentes é como o card e a série, que divergem."""
    escopo = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")
    do_mapa = leitura.valores_por_geografia(escopo, "incid")
    do_ranking = _ranking("UF", "PE", "incid", 5)
    for linha in do_ranking.itertuples():
        assert do_mapa[linha.chave] == pytest.approx(linha.valor)


def test_metrica_sem_suporte_devolve_ranking_vazio() -> None:
    r = _ranking("BR", metrica="hiv_pos_pct")
    assert r.empty
    assert list(r.columns) == ["chave", "nome", "valor"]


def test_grafico_de_ranking_vazio_mostra_recado() -> None:
    import altair as alt

    g = graficos.ranking(
        pd.DataFrame(columns=["chave", "nome", "valor"]),
        rotulo="Casos",
        cor=COR,
        selecao=alt.selection_point(name="barra"),
    )
    assert g.mark["type"] == "text"


def test_grafico_de_ranking_cresce_com_o_numero_de_barras() -> None:
    """Altura fixa espremeria 30 municípios num espaço de 5."""
    import altair as alt

    def altura(n):
        return graficos.ranking(
            _ranking("UF", "PE", top_n=n),
            rotulo="Casos",
            cor=COR,
            selecao=alt.selection_point(name="barra"),
        ).height

    assert altura(30) > altura(5)


# --- clique na barra --------------------------------------------------------


class _Evento:
    def __init__(self, selection):
        self.selection = selection


def test_extrai_a_chave_da_barra_clicada() -> None:
    ev = _Evento({"barra": [{"chave": "AM", "nome": "AM", "valor": 94.5}]})
    assert graficos.alvo_do_clique(ev, "barra") == "AM"


@pytest.mark.parametrize(
    "evento",
    [
        None,
        _Evento(None),
        _Evento({}),
        _Evento({"barra": []}),
        _Evento({"barra": [{}]}),
        _Evento({"barra": ["texto solto"]}),
        _Evento({"outra": [{"chave": "AM"}]}),
        {"selection": {"barra": [{"chave": "BA"}]}},
    ],
)
def test_evento_estranho_nao_derruba_a_pagina(evento) -> None:
    resultado = graficos.alvo_do_clique(evento, "barra")
    assert resultado is None or isinstance(resultado, str)
