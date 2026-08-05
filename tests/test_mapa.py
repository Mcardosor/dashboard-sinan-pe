"""Testes da escala do mapa.

A escala por quantil é o que faz um coroplético epidemiológico ser legível:
poucos municípios concentram o volume, e uma escala linear jogaria quase todos
na mesma cor. Os casos difíceis não são os dados bem-comportados — são os
recortes onde metade dos municípios tem zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import mapa
from src.doencas import tuberculose as tb

RAMPA = tb.rampa_mapa("casos")


def test_escala_divide_em_classes_de_igual_frequencia() -> None:
    valores = pd.Series(range(600))
    escala = mapa.escala_quantil(valores, RAMPA)

    assert escala.classes == mapa.CLASSES
    contagem = mapa.classificar(valores, escala).value_counts()
    assert contagem.max() - contagem.min() <= 1, "as classes têm de ficar equilibradas"


def test_toda_classe_tem_cor() -> None:
    escala = mapa.escala_quantil(pd.Series(range(100)), RAMPA)
    for rotulo in escala.rotulos:
        assert rotulo in escala.cores
    assert escala.cores[mapa.ROTULO_SEM_DADO] == mapa.SEM_DADO


def test_valor_minimo_entra_na_primeira_classe() -> None:
    """`pd.cut` exclui o limite inferior por padrão — o menor viraria "sem dado"."""
    valores = pd.Series([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    escala = mapa.escala_quantil(valores, RAMPA)
    classes = mapa.classificar(valores, escala)
    assert classes.iloc[0] != mapa.ROTULO_SEM_DADO


def test_maioria_zerada_nao_gera_classes_vazias() -> None:
    """Recorte pequeno: 70 municípios sem caso e 30 com.

    Sem colapsar quantis repetidos, vários cortes cairiam em zero e a legenda
    mostraria classes "0,0 a 0,0" idênticas.
    """
    valores = pd.Series([0] * 70 + list(range(1, 31)))
    escala = mapa.escala_quantil(valores, RAMPA)

    assert len(set(escala.rotulos)) == len(escala.rotulos), "há classes repetidas"
    classes = mapa.classificar(valores, escala)
    assert classes.notna().all()
    assert set(classes.unique()) <= set(escala.rotulos) | {mapa.ROTULO_SEM_DADO}


def test_valor_unico_produz_uma_classe() -> None:
    escala = mapa.escala_quantil(pd.Series([7.0] * 20), RAMPA)
    assert escala.classes == 1
    classes = mapa.classificar(pd.Series([7.0] * 20), escala)
    assert (classes != mapa.ROTULO_SEM_DADO).all()


def test_serie_vazia_nao_quebra() -> None:
    escala = mapa.escala_quantil(pd.Series([], dtype=float), RAMPA)
    assert escala.classes == 0
    classes = mapa.classificar(pd.Series([1.0, 2.0]), escala)
    assert (classes == mapa.ROTULO_SEM_DADO).all()


@pytest.mark.parametrize("ruim", [np.nan, np.inf, -np.inf, None])
def test_valores_invalidos_viram_sem_dado(ruim) -> None:
    valores = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, ruim], dtype=float)
    escala = mapa.escala_quantil(valores, RAMPA)
    classes = mapa.classificar(valores, escala)
    assert classes.iloc[-1] == mapa.ROTULO_SEM_DADO


def test_cor_de_sem_dado_nao_colide_com_a_rampa() -> None:
    """Cinza tem de ser distinguível de qualquer tom, senão some no mapa."""
    escala = mapa.escala_quantil(pd.Series(range(100)), RAMPA)
    tons = {v.upper() for k, v in escala.cores.items() if k != mapa.ROTULO_SEM_DADO}
    assert mapa.SEM_DADO.upper() not in tons


def test_rotulos_em_portugues() -> None:
    escala = mapa.escala_quantil(pd.Series([0.0, 1234.5, 2000.0] * 5), RAMPA)
    assert any("," in r for r in escala.rotulos), "decimal tem de ser vírgula"


# ---------------------------------------------------------------------------
# Enquadramento
# ---------------------------------------------------------------------------


def test_enquadrar_centraliza_no_bbox() -> None:
    quadro = mapa.enquadrar((-40.0, -10.0, -30.0, -5.0))
    assert quadro["center"]["lon"] == pytest.approx(-35.0)
    assert quadro["center"]["lat"] == pytest.approx(-7.5)


def test_recorte_menor_recebe_zoom_maior() -> None:
    from src.data import geo

    pais = mapa.enquadrar(tuple(geo.pais().total_bounds))
    estado = mapa.enquadrar(tuple(geo.municipios("PE").total_bounds))
    assert estado["zoom"] > pais["zoom"]


def test_zoom_fica_dentro_de_limites_usaveis() -> None:
    minusculo = mapa.enquadrar((-35.0, -8.0, -35.0001, -8.0001))
    enorme = mapa.enquadrar((-180.0, -90.0, 180.0, 90.0))
    assert 2.0 <= minusculo["zoom"] <= 11.0
    assert 2.0 <= enorme["zoom"] <= 11.0


def test_bbox_degenerado_nao_quebra() -> None:
    quadro = mapa.enquadrar((-35.0, -8.0, -35.0, -8.0))
    assert quadro["zoom"] > 0
    assert quadro["center"]["lon"] == pytest.approx(-35.0)


# ---------------------------------------------------------------------------
# Figura
# ---------------------------------------------------------------------------


def _figura(nivel: str, uf: str | None):
    import json

    from src.data import geo, leitura
    from src.data.escopo import Escopo

    camada = geo.ufs() if nivel == "BR" else geo.municipios(uf)
    chave = "uf" if nivel == "BR" else "cod_mun6"
    valores = leitura.valores_por_geografia(Escopo("TB", 2024, nivel, uf=uf), "incid")
    return mapa.figura(
        camada,
        json.loads(camada.to_json()),
        valores,
        chave=chave,
        rampa=RAMPA,
        rotulo_metrica="Incidência",
        coluna_nome="uf" if nivel == "BR" else "nome_mun",
    ), camada


def test_figura_no_nivel_de_uf() -> None:
    """No Brasil a chave e a coluna de nome são ambas `uf`.

    Selecionar a mesma coluna duas vezes fazia `dados[chave]` devolver um
    DataFrame, e `.map()` quebrava com "the first argument must be callable".
    """
    fig, camada = _figura("BR", None)
    assert len(camada) == 27
    assert len(fig.data) > 1, "a legenda precisa ter mais de uma classe"


def test_figura_no_nivel_de_municipio() -> None:
    fig, camada = _figura("UF", "PE")
    assert len(camada) == 185
    assert len(fig.data) > 1


def test_figura_traz_nome_e_valor_no_hover() -> None:
    fig, _ = _figura("UF", "PE")
    modelo = fig.data[0].hovertemplate
    assert "customdata[0]" in modelo, "falta o nome"
    assert "customdata[1]" in modelo, "falta o valor formatado"
    assert "Incidência" in modelo


def test_figura_nao_pinta_fundo() -> None:
    """O painel já tem superfície própria; fundo opaco brigaria com o tema."""
    fig, _ = _figura("UF", "PE")
    assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"


def test_metrica_sem_suporte_devolve_serie_vazia() -> None:
    """Melhor um mapa vazio e honesto do que colorido com a métrica errada."""
    from src.data import leitura
    from src.data.escopo import Escopo

    vazio = leitura.valores_por_geografia(Escopo("TB", 2024, "BR"), "hiv_pos_pct")
    assert vazio.empty


@pytest.mark.parametrize("metrica", ["incid", "casos", "cura", "pop", "mortalidade", "letalidade"])
def test_metricas_pintaveis_cobrem_todas_as_ufs(metrica: str) -> None:
    from src.data import leitura
    from src.data.escopo import Escopo

    valores = leitura.valores_por_geografia(Escopo("TB", 2024, "BR"), metrica)
    assert len(valores) == 27
    assert valores.index.is_unique
