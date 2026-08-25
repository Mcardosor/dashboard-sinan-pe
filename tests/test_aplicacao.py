"""Roda o `app.py` inteiro, de verdade.

**O buraco que este arquivo fecha.** O resto da suíte nunca executou o
`app.py`: importá-lo dispara o script, então `test_app.py` faz checagem
estática com `ast` — ver CLAUDE.md, armadilha 8. São 950 linhas de
orquestração que nenhum teste percorria, e é exatamente onde os erros deste
projeto têm acontecido: uma constante usada antes de existir, uma variável
definida depois do primeiro uso, um `zip` que trunca.

O `AppTest` do Streamlit resolve isso sem contradizer a armadilha: ele executa
o script num contexto controlado, em vez de importá-lo. A aplicação inteira
sobe em cerca de 1,5 s.

**O que se verifica em cada estado:** nenhuma exceção, e nenhum painel caído.
A segunda parte importa mais que parece — `resiliencia.painel` contém a falha
de um painel no próprio painel, o que é ótimo em produção e péssimo num teste
ingênuo: sem olhar o aviso, a página "sobe" com metade dos gráficos quebrados
e o teste passa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import resiliencia  # noqa: E402
from src.estado import Navegacao  # noqa: E402

#: Generoso porque a primeira execução paga a leitura de geometria; as demais
#: pegam cache. Um teste que falha por lentidão de máquina vira ruído.
LIMITE = 180

#: Caminho absoluto: o `AppTest` resolve relativo ao diretório do teste, não à
#: raiz do repositório.
APLICACAO = str(Path(__file__).resolve().parents[1] / "app.py")


def _rodar(**estado) -> AppTest:
    """Sobe a aplicação, opcionalmente com a navegação já posicionada.

    Entrar numa UF é clique no mapa, que o `AppTest` não alcança — o deck.gl é
    componente externo. Então o recorte é posto direto no estado, que é o
    mesmo objeto que o clique manipularia.
    """
    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE)
    if estado:
        nav = Navegacao(doenca="TUBERCULOSE", ano=estado.pop("ano", 2024))
        for chave, valor in estado.items():
            setattr(nav, chave, valor)
        at.session_state["nav"] = nav
    return at.run()


def _conferir(at: AppTest, contexto: str) -> None:
    assert not at.exception, (
        f"{contexto}: {[e.value for e in at.exception]}"
    )
    caidos = [w.value for w in at.warning if resiliencia.AVISO in w.value]
    assert not caidos, f"{contexto}: painel caído — {caidos}"


def test_a_aplicacao_sobe_no_brasil() -> None:
    """O caso mais simples, e o que pega erro de importação e de ordem."""
    at = _rodar()
    _conferir(at, "Brasil")
    assert at.markdown, "a página subiu vazia"


@pytest.mark.parametrize("metrica", ["incid", "casos", "mortalidade", "cura_pct"])
def test_toda_metrica_do_mapa_monta(metrica: str) -> None:
    """As quatro do seletor, no Brasil e dentro de uma UF.

    `cura_pct` é a que mais mudou de forma recentemente — trocou de
    denominador, ganhou supressão de base pequena e passou a sair de
    `SITUA_ENCE` em vez de `incidence`.
    """
    _conferir(_rodar(metrica=metrica), f"BR/{metrica}")
    _conferir(
        _rodar(metrica=metrica, nivel="UF", uf="PE"), f"PE/{metrica}"
    )


@pytest.mark.parametrize("recorte", ["MUN", "MACRO", "MICRO"])
def test_todo_recorte_de_saude_monta(recorte: str) -> None:
    """Os três recortes de PE, que é a única UF que os tem.

    Foi aqui que o `UnboundLocalError` do título do ranking apareceu: o mapa
    montava e o ranking caía, e a página seguia de pé por causa da resiliência
    — invisível para quem não olhasse o aviso.
    """
    _conferir(
        _rodar(nivel="UF", uf="PE", recorte=recorte), f"PE/{recorte}"
    )


@pytest.mark.parametrize("uf", ["PE", "MG", "RR", "SP"])
def test_a_aplicacao_sobe_em_ufs_de_tamanhos_diferentes(uf: str) -> None:
    """RR tem 15 municípios, MG tem 853, PE tem ilha oceânica.

    Tamanho muda o caminho: o enquadramento, o destaque de ilha e a
    classificação em quebras naturais reagem ao número de feições.
    """
    _conferir(_rodar(nivel="UF", uf=uf), f"UF {uf}")


def test_a_aplicacao_sobe_com_municipio_selecionado() -> None:
    """Nível de município, que tem painéis com dado escasso."""
    _conferir(
        _rodar(nivel="MUN", uf="PE", mun="261160", nome_mun="Recife"), "Recife"
    )


def test_a_aplicacao_sobe_com_municipio_destacado() -> None:
    """O destaque veio depois e mexe no mapa; nada mais pode sentir."""
    at = _rodar(nivel="UF", uf="PE", destacado="261160", nome_destacado="Recife")
    _conferir(at, "PE com destaque")
    assert any("destaque" in c.value for c in at.caption), (
        "a legenda do destaque sumiu"
    )


@pytest.mark.parametrize("ano", [2010, 2019, 2024])
def test_a_aplicacao_sobe_em_anos_extremos(ano: int) -> None:
    """2010 é o primeiro ano; 2019 é o último antes de o balde de
    "não informado" sumir da extração; 2024 é o último fechado."""
    _conferir(_rodar(ano=ano, nivel="UF", uf="PE"), f"PE/{ano}")


def test_a_aplicacao_avisa_quando_o_ano_esta_incompleto() -> None:
    """2025 tem 2% dos casos publicados. O aviso é o que separa "queda" de
    "ano pela metade", e é um `st.warning` como o de painel caído — então
    este teste também confere que os dois não se confundem."""
    at = _rodar(ano=2025)
    _conferir(at, "2025")
    assert any("incompleto" in w.value for w in at.warning), (
        "sumiu o aviso de ano incompleto"
    )


# ---------------------------------------------------------------------------
# Interação: os caminhos que só existem depois de alguém mexer num controle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vista", ["meses", "anos", "desfechos"])
def test_as_tres_vistas_da_evolucao_montam(vista: str) -> None:
    """Cada opção do painel de evolução desenha um gráfico diferente.

    O empilhado de desfechos entrou em 21/ago e nunca havia rodado em teste —
    só o leitor por baixo dele tinha cobertura.
    """
    at = _rodar(nivel="UF", uf="PE")
    _conferir(at, f"antes de escolher {vista}")

    horizonte = next(r for r in at.radio if "Evolução" in r.label)
    horizonte.set_value(vista).run()
    _conferir(at, f"evolução/{vista}")


def test_a_serie_dupla_monta() -> None:
    """Casos e incidência sobrepostos, cada um no seu eixo."""
    at = _rodar(nivel="UF", uf="PE")
    at.toggle[0].set_value(True).run()
    _conferir(at, "série dupla")


@pytest.mark.parametrize("tipo", ["Casos novos", "Óbitos"])
def test_as_duas_piramides_montam(tipo: str) -> None:
    """A de óbitos vem do SIM e tem cobertura de ano diferente da de casos."""
    at = _rodar(nivel="UF", uf="PE")
    piramide = next(r for r in at.radio if "exibir" in r.label)
    piramide.set_value(tipo).run()
    _conferir(at, f"pirâmide/{tipo}")


def test_toda_variavel_da_composicao_monta() -> None:
    """São 24 variáveis do SINAN, e cada uma tem rótulos e agrupamentos
    próprios. É o painel com mais chance de encontrar dado torto."""
    at = _rodar(nivel="UF", uf="PE")
    seletor = next(s for s in at.selectbox if "Variável" in s.label)

    for opcao in seletor.options:
        seletor.set_value(opcao).run()
        _conferir(at, f"composição/{opcao}")


def test_a_trilha_aparece_dentro_de_uma_regiao_de_saude() -> None:
    """A macro e a região de saúde são o que só o breadcrumb nomeia.

    Ele é omitido no Brasil e na UF, onde repetiria a faixa — então este é o
    único estado em que ele deve aparecer.
    """
    at = _rodar(nivel="UF", uf="PE", recorte="MICRO", macro="Metropolitana")
    _conferir(at, "PE/micro")
    assert any("Macro" in c.value for c in at.caption), "sumiu a trilha"


def test_entrar_numa_macrorregiao_nao_gira_a_pagina() -> None:
    """O controle de recorte é espelho da navegação, não dono dela.

    Com `key`, o widget reimpunha o valor antigo a cada rerun: entrar numa
    macrorregião muda o recorte para "regiões de saúde", o controle forçava
    de volta para "macrorregiões", `definir_recorte` limpava a macro
    recém-escolhida, e o clique persistido reentrava nela. A página girava sem
    parar.

    O `AppTest` executa até estabilizar, então um laço aparece aqui como
    estouro de tempo — que é o que este teste prende.
    """
    at = _rodar(nivel="UF", uf="PE", recorte="MICRO", macro="Metropolitana")
    _conferir(at, "PE dentro de uma macrorregião")

    assert at.session_state["nav"].recorte == "MICRO", (
        f"o recorte voltou para {at.session_state['nav'].recorte} — o controle "
        f"está brigando com a navegação de novo"
    )
    assert at.session_state["nav"].macro == "Metropolitana", (
        "a macrorregião foi limpa; era isso que alimentava o laço"
    )


def test_o_controle_de_recorte_segue_a_navegacao() -> None:
    """Trocar de recorte pelo controle continua funcionando.

    O contrapeso do teste acima: tirar a `key` não pode quebrar o caminho
    normal, que é o usuário escolhendo a divisão na barra.
    """
    at = _rodar(nivel="UF", uf="PE")
    controle = next(c for c in at.segmented_control if "Recorte" in c.label)
    assert controle.value == "MUN"

    controle.set_value("MACRO").run()
    _conferir(at, "após escolher macrorregiões")
    assert at.session_state["nav"].recorte == "MACRO"
