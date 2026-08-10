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
from src.data import geo
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
# Clique no mapa (pydeck)
# ---------------------------------------------------------------------------
# O coroplético do Plotly não emite evento de clique — ver docs/mapa-clique.md.
# O `GeoJsonLayer` do deck.gl faz picking por GPU, e o evento do
# `st.pydeck_chart` traz a feição inteira, com as propriedades dela.


class _Evento:
    def __init__(self, selection):
        self.selection = selection


def _evento_com(props: dict):
    return _Evento({"objects": {"camada-0": [{"properties": props}]}})


def test_extrai_uf_do_clique() -> None:
    assert mapa.alvo_do_clique(_evento_com({"uf": "PE"})) == "PE"


def test_extrai_municipio_do_clique() -> None:
    props = {"cod_mun6": "261160", "nome_mun": "Recife", "uf": "PE"}
    assert mapa.alvo_do_clique(_evento_com(props)) == "261160"


def test_municipio_tem_precedencia_sobre_a_uf() -> None:
    """A feição de município também carrega `uf`; a chave mais específica vence."""
    props = {"uf": "PE", "cod_mun6": "261160"}
    assert mapa.alvo_do_clique(_evento_com(props)) == "261160"


def test_extrai_regiao_de_saude() -> None:
    assert mapa.alvo_do_clique(_evento_com({"regiao": "Sertão"})) == "Sertão"


@pytest.mark.parametrize(
    "evento",
    [
        None,
        _Evento(None),
        _Evento({}),
        _Evento({"objects": {}}),
        _Evento({"objects": {"camada-0": []}}),
        _Evento({"objects": {"camada-0": [{"properties": {}}]}}),
        _Evento({"objects": {"camada-0": ["texto solto"]}}),
        {"selection": {"objects": {"camada-0": [{"properties": {"uf": "SP"}}]}}},
    ],
)
def test_evento_estranho_nao_derruba_a_pagina(evento) -> None:
    """O formato do evento é detalhe interno do Streamlit e já mudou entre
    versões. Se vier algo inesperado, o mapa apenas não navega."""
    resultado = mapa.alvo_do_clique(evento)
    assert resultado is None or isinstance(resultado, str)


def test_evento_em_dicionario_tambem_funciona() -> None:
    bruto = {"selection": {"objects": {"c": [{"properties": {"uf": "BA"}}]}}}
    assert mapa.alvo_do_clique(bruto) == "BA"


# ---------------------------------------------------------------------------
# Legenda em HTML
# ---------------------------------------------------------------------------


def test_legenda_cobre_todas_as_classes() -> None:
    """O deck.gl não desenha legenda; ela é HTML, como os cards de KPI."""
    escala = mapa.escala_quantil(pd.Series(range(100)), RAMPA)
    html = mapa.legenda(escala, "Incidência")
    for rotulo in escala.rotulos:
        assert rotulo in html
    assert mapa.ROTULO_SEM_DADO in html
    assert "Incidência" in html


def test_legenda_escapa_o_titulo() -> None:
    escala = mapa.escala_quantil(pd.Series(range(10)), RAMPA)
    assert "<script>" not in mapa.legenda(escala, "<script>alert(1)</script>")


def test_deck_pinta_cada_feicao() -> None:
    from src.data import geo, leitura
    from src.data.escopo import Escopo

    camada = geo.municipios("PE")
    valores = leitura.valores_por_geografia(Escopo("TB", 2024, "UF", uf="PE"), "incid")
    desenho, escala = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=RAMPA, rotulo_metrica="Incidência"
    )
    assert len(desenho.layers) == 1
    assert escala.classes == mapa.CLASSES


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

#: Teto do JSON que o mapa manda ao navegador, em MB, no pior recorte que
#: temos — Minas Gerais, com 853 municípios.
#:
#: Medido em 0,71 MB depois de tirar a indentação. O teto de 1,0 MB dá folga
#: para a malha mudar sem alarme falso, e ainda assim pega uma regressão do
#: tamanho da que existia: com `indent=2` do pydeck eram 2,76 MB.
TETO_PAYLOAD_MB = 1.0


def _payload(uf: str) -> str:
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import tuberculose as pack

    camada = geo.municipios(uf)
    valores = leitura.valores_por_geografia(Escopo("TB", 2024, "UF", uf=uf), "incid")
    figura, _ = mapa.deck(
        camada,
        valores,
        chave="cod_mun6",
        rampa=pack.rampa_mapa("incid"),
        rotulo_metrica="Incidência",
        coluna_nome="nome_mun",
    )
    return figura.to_json()


def test_payload_do_mapa_cabe_no_teto() -> None:
    """O mosaico volta pela rede a cada navegação e a cada troca de métrica.

    As cores fazem parte do mesmo spec, então não é custo de primeira carga.
    Em localhost isso é invisível; sobre rede real dominava tudo.
    """
    tamanho = len(_payload("MG").encode("utf-8")) / 1e6
    assert tamanho < TETO_PAYLOAD_MB, (
        f"payload de MG em {tamanho:.2f} MB, teto {TETO_PAYLOAD_MB} MB. "
        f"A compactação de `mapa._compactar` provavelmente parou de valer."
    )


def test_payload_sai_sem_indentacao() -> None:
    """Regressão direta: `pydeck.serialize` usa `indent=2` por padrão.

    `_compactar` engole exceções de propósito, para uma mudança de API interna
    do pydeck não derrubar o mapa — o preço é que a falha seria silenciosa.
    Este teste é quem faz barulho.
    """
    texto = _payload("PE")
    assert '\n  "' not in texto, "voltou a indentar"
    assert ", " not in texto[:200], "separadores não estão compactos"


def _montar_features(uf: str, geometrias=None):
    import json

    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import tuberculose as pack

    camada = geo.municipios(uf)
    valores = leitura.valores_por_geografia(Escopo("TB", 2024, "UF", uf=uf), "incid")
    figura, _ = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=pack.rampa_mapa("incid"),
        rotulo_metrica="Incidência", coluna_nome="nome_mun", geometrias=geometrias,
    )
    return json.loads(figura.to_json())["layers"][0]["data"]["features"]


def test_geometria_pronta_nao_muda_o_desenho() -> None:
    """Reaproveitar a malha convertida não pode alterar o que é desenhado.

    A conversão custa 75 ms em MG e é o item mais caro de montar o mapa — mas
    o ganho não vale nada se servir geometria diferente.
    """
    convertidas = mapa.geometrias_geojson(geo.municipios("PE"))
    sem, com = _montar_features("PE"), _montar_features("PE", convertidas)

    assert len(sem) == len(com)
    for a, b in zip(sem, com):
        assert a["geometry"] == b["geometry"]
        assert a["properties"] == b["properties"]


def test_geometria_de_tamanho_errado_e_ignorada() -> None:
    """A guarda que impede servir a malha de outro recorte.

    Se a lista não corresponde à camada, `deck` volta ao caminho normal em vez
    de emparelhar geometria de um município com o dado de outro.
    """
    de_outro_estado = mapa.geometrias_geojson(geo.municipios("MG"))
    assert len(de_outro_estado) != len(geo.municipios("PE"))

    correto = _montar_features("PE")
    com_lista_errada = _montar_features("PE", de_outro_estado)
    assert [f["geometry"] for f in com_lista_errada] == [
        f["geometry"] for f in correto
    ], "a lista de tamanho errado foi usada em vez de descartada"
