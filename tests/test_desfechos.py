"""Empilhado de desfechos do tratamento.

Cobre a regra de agrupamento e o leitor da série. As três coisas que este
arquivo prende foram achadas conferindo o dado contra o Boletim de TB 2026, e
nenhuma das três dá erro quando quebra — todas dão gráfico errado.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data import kpis
from src.data.escopo import Escopo

pytest.importorskip("duckdb")

leitura = pytest.importorskip("src.data.leitura")

BR = Escopo("TUBERCULOSE", 2024, "BR")
PE = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")
RECIFE = Escopo("TUBERCULOSE", 2024, "MUN", uf="PE", mun="261160")


def test_zero_a_esquerda_cai_no_grupo_certo() -> None:
    """`03` e `04` são óbito, não "outros".

    O dataset traz os dois formatos convivendo — só em 2018 e 2019, 177
    registros — e `trim` não normaliza isso. Sem `lstrip`, esses óbitos
    engordariam a fatia de "outros" nesses dois anos, e o gráfico mostraria um
    degrau que não existe.
    """
    assert kpis.grupo_do_desfecho("03") == "obito"
    assert kpis.grupo_do_desfecho("04") == "obito"
    assert kpis.grupo_do_desfecho(" 3") == "obito"


def test_codigo_desconhecido_nao_some() -> None:
    """A quarta fatia é complemento, não lista.

    Se um código novo aparecer no SINAN, ele tem de cair em "outros" e
    continuar somando 100%. Uma lista fechada o descartaria em silêncio, e o
    empilhado passaria a mentir sobre o total.
    """
    assert kpis.grupo_do_desfecho("99") == "outros"
    assert kpis.grupo_do_desfecho("") == "outros"


def test_zero_ignorado_nao_e_cura() -> None:
    """O código 0 existe até 2017 e chega a 2.711 num ano.

    Ele é "Ignorado". Tratá-lo como encerramento favorável inflaria a cura
    justamente nos anos mais antigos, que são a base da comparação temporal.
    """
    assert kpis.grupo_do_desfecho("0") == "outros"


def test_interrupcao_do_empilhado_segue_a_regra_do_card() -> None:
    """O gráfico e o KPI não podem contar abandono de jeitos diferentes.

    Se alguém trocar `REGRA_INTERRUPCAO`, os dois têm de se mover juntos — a
    tela mostraria 15,5% no card e outra coisa na barra do mesmo ano.
    """
    grupos = dict(kpis.GRUPOS_DESFECHO)
    assert grupos["interrupcao"] == kpis._ABANDONO[kpis.REGRA_INTERRUPCAO]


@pytest.mark.parametrize("esc", [BR, PE, RECIFE], ids=["BR", "PE", "Recife"])
def test_as_fatias_somam_cem_em_todo_ano(esc: Escopo) -> None:
    """Composição que não fecha em 100% não é composição."""
    serie = leitura.serie_desfechos(esc)
    assert not serie.empty, f"sem série para {esc.nivel}"
    soma = serie.groupby("ano")["pct"].sum()
    assert soma.round(6).eq(100).all(), f"anos que não fecham: {soma[soma.round(6) != 100]}"


@pytest.mark.parametrize("esc", [BR, PE, RECIFE], ids=["BR", "PE", "Recife"])
def test_todo_ano_tem_as_quatro_fatias(esc: Escopo) -> None:
    """Ano sem óbito registrado precisa aparecer com óbito zero.

    Sem a grade completa a legenda mudaria de tamanho de ano para ano, e a
    ordem das faixas junto.
    """
    serie = leitura.serie_desfechos(esc)
    nomes = {nome for nome, _ in kpis.GRUPOS_DESFECHO}
    for ano, bloco in serie.groupby("ano"):
        assert set(bloco["desfecho"]) == nomes, f"{ano} incompleto"


def test_ano_raso_fica_de_fora() -> None:
    """2025 tem 1.074 encerramentos contra 75.404 de 2024.

    A extração que recebemos mal começou o ano. Uma barra de 100% apoiada
    nisso fica com a mesma cara de solidez das outras.
    """
    assert 2025 not in set(leitura.serie_desfechos(BR)["ano"])
    assert 2024 in set(leitura.serie_desfechos(BR)["ano"])


def test_o_piso_e_relativo_e_nao_apaga_municipio() -> None:
    """Um piso absoluto que pegasse 2025 apagaria todo município.

    Recife encerra algumas centenas por ano, e são dados legítimos. Este teste
    existe porque a primeira versão usava 1.000 registros fixos.
    """
    recife = leitura.serie_desfechos(RECIFE)
    assert len(recife["ano"].unique()) >= 10, (
        "a série municipal encolheu — o piso voltou a ser absoluto?"
    )


def test_cura_do_empilhado_bate_com_o_kpi_de_interrupcao() -> None:
    """O mesmo denominador dos dois lados.

    O empilhado usa todos os encerramentos, que é o denominador da regra
    `boletim` do card de interrupção. Se um dos dois mudar de denominador, a
    barra de 2024 e o card param de concordar na fatia de interrupção.
    """
    serie = leitura.serie_desfechos(BR)
    do_grafico = float(
        serie[(serie["ano"] == 2024) & (serie["desfecho"] == "interrupcao")]["pct"].iloc[0]
    )
    do_card = kpis.calcular(BR).interrupcao_trat_pct
    assert do_grafico == pytest.approx(do_card, abs=0.01), (
        f"gráfico {do_grafico:.2f}% vs card {do_card:.2f}%"
    )


def test_serie_vazia_nao_explode() -> None:
    """Recorte sem encerramento devolve moldura vazia, não erro.

    `999999` e não `000000`: este último **existe** no dado, é o balde de
    município ignorado, e traz encerramentos de verdade.
    """
    vazio = leitura.serie_desfechos(
        Escopo("TUBERCULOSE", 2024, "MUN", uf="PE", mun="999999")
    )
    assert isinstance(vazio, pd.DataFrame)
    assert vazio.empty
    assert list(vazio.columns) == ["ano", "desfecho", "n", "pct"]
