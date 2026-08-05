"""Recortes de saúde de Pernambuco.

A junção é por **nome** de região entre duas fontes independentes — o
`municipios.csv` e os shapefiles — e a agregação precisa recalcular taxas em
vez de tirar média delas. São os dois pontos onde isto quebra em silêncio.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data import geo, leitura, pernambuco
from src.data.escopo import Escopo

ESCOPO = Escopo("TUBERCULOSE", 2024, "UF", uf="PE")


def test_lookup_cobre_todos_os_municipios_de_pe() -> None:
    tabela = pernambuco.lookup()
    assert len(tabela) == 185
    assert tabela["cod_mun6"].is_unique
    assert tabela["cod_mun6"].str.fullmatch(r"\d{6}").all()


def test_codigo_e_arredondado_e_nao_truncado() -> None:
    """Oito dos 185 municípios estão gravados com erro de ponto flutuante.

    São Vicente Férrer aparece como 2613799.9999999995 no CSV. Truncar dá
    261379 em vez de 261380, o município deixa de casar com os dados e some da
    agregação por região — sem erro nenhum, só um total menor.
    """
    codigos = set(pernambuco.lookup()["cod_mun6"])
    assert "261380" in codigos, "São Vicente Férrer truncado"
    assert "261460" in codigos, "Tabira truncado"
    assert "261379" not in codigos
    assert "261459" not in codigos


def test_lookup_casa_com_os_dados_sem_sobra() -> None:
    """Qualquer município fora da junção seria caso desaparecendo do mapa."""
    componentes = leitura.componentes_municipais(ESCOPO)
    codigos_lookup = set(pernambuco.lookup()["cod_mun6"])
    assert set(componentes.index) == codigos_lookup


def test_nomes_de_regiao_batem_com_a_geometria() -> None:
    """Duas fontes independentes; um acento a mais quebraria a junção."""
    for nivel, coluna in (("macro", "macro"), ("micro", "micro")):
        do_csv = {pernambuco._chave(v) for v in pernambuco.lookup()[coluna]}
        da_malha = {pernambuco._chave(v) for v in geo.regioes_pe(nivel)["regiao"]}
        assert do_csv == da_malha, f"{nivel}: {do_csv ^ da_malha}"


def test_quatro_macros_e_doze_regioes_de_saude() -> None:
    assert len(pernambuco.macros()) == 4
    assert len(pernambuco.micros()) == 12


def test_micros_filtradas_por_macro() -> None:
    assert pernambuco.micros("Agreste") == ["Caruaru", "Garanhuns"]
    todas = {m for macro in pernambuco.macros() for m in pernambuco.micros(macro)}
    assert todas == set(pernambuco.micros())


def test_municipios_de_uma_regiao() -> None:
    recife = pernambuco.municipios_de(micro="Recife")
    assert "261160" in recife
    soma = sum(len(pernambuco.municipios_de(macro=m)) for m in pernambuco.macros())
    assert soma == 185, "todo município pertence a exatamente uma macro"


# ---------------------------------------------------------------------------
# Agregação
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nivel", ["macro", "micro"])
@pytest.mark.parametrize("metrica", ["casos", "cura", "pop", "obitos"])
def test_contagens_fecham_com_a_uf(nivel: str, metrica: str) -> None:
    componentes = leitura.componentes_municipais(ESCOPO)
    por_regiao = leitura.valores_por_regiao(ESCOPO, metrica, nivel)
    assert por_regiao.sum() == pytest.approx(componentes[metrica].sum())


@pytest.mark.parametrize("nivel", ["macro", "micro"])
def test_taxa_e_recalculada_e_nao_promediada(nivel: str) -> None:
    """Média de taxas municipais pesaria Recife igual a um município de 2 mil.

    A incidência de uma região tem de sair de `casos/pop` somados, o que dá
    resultado diferente da média simples das incidências municipais.
    """
    componentes = leitura.componentes_municipais(ESCOPO)
    coluna = "macro" if nivel == "macro" else "micro"
    tabela = pernambuco.lookup().set_index("cod_mun6")[[coluna]]
    juncao = componentes.join(tabela, how="inner")

    correto = leitura.valores_por_regiao(ESCOPO, "incid", nivel)
    somas = juncao.groupby(coluna).sum(numeric_only=True)
    esperado = somas["casos"] / somas["pop"] * 100_000
    assert correto.reindex(esperado.index).to_numpy() == pytest.approx(
        esperado.to_numpy()
    )

    # E tem de diferir da média simples, senão o teste não prova nada.
    juncao["incid_mun"] = juncao["casos"] / juncao["pop"].replace(0, pd.NA) * 100_000
    media = juncao.groupby(coluna)["incid_mun"].mean()
    assert not correto.reindex(media.index).to_numpy() == pytest.approx(
        media.to_numpy()
    )


def test_metrica_sem_componentes_devolve_vazio() -> None:
    componentes = leitura.componentes_municipais(ESCOPO)
    assert pernambuco.agregar(componentes, "hiv_pos_pct", "macro").empty


def test_agregacao_com_entrada_vazia_nao_quebra() -> None:
    vazio = pd.DataFrame(columns=["casos", "pop"], index=pd.Index([], name="cod_mun6"))
    assert pernambuco.agregar(vazio, "casos", "macro").empty


def test_indice_da_agregacao_e_o_nome_da_regiao() -> None:
    """A geometria identifica a região pelo nome; o índice tem de bater."""
    valores = leitura.valores_por_regiao(ESCOPO, "casos", "macro")
    assert set(valores.index) == set(geo.regioes_pe("macro")["regiao"])
