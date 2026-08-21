"""Comparação com o Boletim Epidemiológico do Ministério da Saúde.

Este harness é o irmão externo do `test_referencia_r.py`, e existe porque
aquele não é suficiente. Comparar com o painel da equipe parceira mede
**concordância**, não correção: em agosto de 2026 os dois painéis exibiam o
mesmo número errado, vindo do `sinan_landing` dobrado, e nenhuma comparação
entre eles teria como perceber. Fonte oficial e independente pega essa classe
de erro; paridade não pega.

Foi este harness que fechou a divergência mais antiga do projeto. Ver
`excecoes.md` §3.

**A tolerância é assimétrica, e isso é o ponto do arquivo.** O SINAN é
atualizado retroativamente: uma extração mais antiga tem *menos* casos que uma
mais nova, nunca mais. Nossos parquets são anteriores ao fechamento do
boletim, então ficar um pouco **abaixo** do oficial é o comportamento correto
— medido, de 0,13% a 1,36% nos onze anos. Ficar **acima** não tem explicação
benigna, e é exatamente o formato do defeito que inflou o painel em R em 31,8%.
Por isso o teto para cima é muito mais apertado que o piso para baixo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack

REFERENCIA = json.loads(
    (Path(__file__).parent / "referencia_ms.json").read_text(encoding="utf-8")
)

#: Quanto podemos ficar **abaixo** do boletim. Cobre a defasagem de extração
#: com folga: o pior ano medido é 2020, com −1,36%.
MARGEM_ABAIXO = 0.025

#: Quanto podemos ficar **acima**. Estar acima do oficial não tem causa
#: benigna — só arredondamento do coeficiente, que o boletim publica com uma
#: casa decimal. Qualquer coisa além disso é contagem inflada.
MARGEM_ACIMA = 0.005

IGNORADOS = {int(a) for a in REFERENCIA["anos_ignorados"]}


def _anos():
    for item in REFERENCIA["serie_brasil"]:
        ano = item["ano"]
        marca = pytest.mark.skipif(
            ano in IGNORADOS,
            reason=REFERENCIA["anos_ignorados"].get(str(ano), ""),
        )
        yield pytest.param(item, id=str(ano), marks=marca)


def _conferir(nome: str, nosso: float | None, oficial: float, ano: int) -> None:
    assert nosso is not None, f"{nome} não calculado para {ano}"

    desvio = (nosso - oficial) / oficial

    assert desvio <= MARGEM_ACIMA, (
        f"{ano} · {nome}: nosso {nosso:,.2f} está {desvio:+.2%} do boletim do MS "
        f"({oficial:,.2f}). **Acima do oficial não tem explicação benigna** — o "
        f"SINAN só cresce com o tempo, e nossa extração é anterior à do boletim. "
        f"Suspeitar de contagem dobrada (ver excecoes.md §2) ou de soma de tipos "
        f"de entrada que não são caso novo (foi o que inflou o painel em R)."
    )

    assert desvio >= -MARGEM_ABAIXO, (
        f"{ano} · {nome}: nosso {nosso:,.2f} está {desvio:+.2%} do boletim do MS "
        f"({oficial:,.2f}), abaixo da margem de {MARGEM_ABAIXO:.1%}. Defasagem de "
        f"extração explica cerca de 1%; muito além disso é filtro perdendo casos."
    )


@pytest.mark.parametrize("ref", _anos())
def test_casos_novos_conferem_com_o_boletim(ref: dict) -> None:
    nosso = calc.calcular(Escopo(pack.DOENCA, ref["ano"], "BR"))
    _conferir("casos novos", nosso.casos, ref["casos"], ref["ano"])


@pytest.mark.parametrize("ref", _anos())
def test_incidencia_confere_com_o_boletim(ref: dict) -> None:
    nosso = calc.calcular(Escopo(pack.DOENCA, ref["ano"], "BR"))
    _conferir("incidência", nosso.incid, ref["incid"], ref["ano"])


def test_estamos_sempre_abaixo_do_oficial_nunca_acima() -> None:
    """A direção do desvio é o sinal, e vale olhar a série inteira.

    Um ano isolado acima do oficial pode ser arredondamento. Vários anos acima
    é defeito sistemático — e é assim que a contagem dobrada do `sinan_landing`
    teria aparecido, se houvesse este teste na época.
    """
    acima = []
    for item in REFERENCIA["serie_brasil"]:
        if item["ano"] in IGNORADOS:
            continue
        nosso = calc.calcular(Escopo(pack.DOENCA, item["ano"], "BR"))
        if nosso.casos and nosso.casos > item["casos"] * (1 + MARGEM_ACIMA):
            acima.append((item["ano"], nosso.casos, item["casos"]))

    assert not acima, (
        "anos com mais casos que o boletim oficial do MS: "
        + ", ".join(f"{a}: {n:,.0f} vs {o:,}" for a, n, o in acima)
    )


def test_o_registro_nomeia_a_fonte() -> None:
    """Número de validação sem procedência não vale nada.

    Quem abrir este diretório daqui a um ano precisa saber de que documento
    saiu cada valor, e de quando ele é — o boletim é republicado todo ano e os
    números do ano anterior mudam entre edições.
    """
    fonte = REFERENCIA["_fonte"]
    for campo in ("documento", "emissor", "edicao", "figura", "lido_em"):
        assert fonte.get(campo), f"referencia_ms.json sem `_fonte.{campo}`"


# ---------------------------------------------------------------------------
# Interrupção de tratamento
# ---------------------------------------------------------------------------

#: Tabela 9 do boletim — "Indicadores operacionais de encerramento do
#: tratamento dos casos novos de tuberculose", Brasil, 2024. A tabela publica
#: três populações: TB (todos os casos novos), TB pulmonar, e TB pulmonar
#: confirmada por critério laboratorial. **A nossa é a primeira.**
#:
#: Confundi-las custou uma investigação: os 16,5% que pareciam nossa meta são
#: a terceira coluna, um subconjunto de 56.388 casos contra os 86.204 do
#: total.
MS_INTERRUPCAO_BR_2024 = 15.2

#: Quanto aceitamos divergir. Medido: `{2,10}` sobre todos os encerramentos dá
#: 15,52% aqui contra 15,20% publicados. A diferença é a mesma defasagem de
#: extração que separa nossos casos novos dos do boletim — nosso denominador
#: tem 75.404 encerramentos e as porcentagens do MS implicam 77.467, com a
#: diferença concentrada em "não avaliados".
MARGEM_INTERRUPCAO = 0.6


def test_a_regra_boletim_reproduz_a_tabela_9() -> None:
    """A regra "boletim" existe para render o número que o MS publica.

    Ela nasceu de um engano meu que quase virou estrago: eu ia **corrigir** a
    regra "ms" para bater com a Tabela 9, sem notar que as duas respondem
    perguntas diferentes. "ms" é o indicador de monitoramento do Ministério,
    que exclui os não avaliados do denominador — está documentado na armadilha
    4 do contrato de dados. A Tabela 9 é apresentação de distribuição, e ali
    cura, interrupção e "não avaliados" são três colunas da mesma base.

    Sobrescrever uma pela outra teria apagado uma escolha metodológica
    documentada e quebrado treze testes de referência. As duas convivem.
    """
    from src.data import kpis

    esc = Escopo(pack.DOENCA, 2024, "BR")
    nosso = kpis.interrupcao_trat_pct(esc, "boletim")
    assert nosso is not None

    desvio = abs(nosso - MS_INTERRUPCAO_BR_2024)
    assert desvio <= MARGEM_INTERRUPCAO, (
        f'a regra "boletim" dá {nosso:.2f}% contra {MS_INTERRUPCAO_BR_2024}% '
        f"da Tabela 9 ({desvio:.2f} pontos de diferença). Se o denominador "
        f'passou a excluir os não avaliados, virou a regra "ms" — que é outro '
        f"indicador, e dá ~17,2%."
    )


def test_as_tres_regras_nao_se_confundem() -> None:
    """"paridade" e "ms" precisam continuar dando números diferentes.

    Se convergirem, alguém igualou as duas sem querer — e aí o painel estaria
    exibindo uma regra achando que exibe a outra. A diferença é o abandono
    primário, código 10: quem nunca chegou a iniciar o tratamento também
    interrompeu, e o MS conta, o painel em R não.
    """
    from src.data import kpis

    esc = Escopo(pack.DOENCA, 2024, "BR")
    v = {r: kpis.interrupcao_trat_pct(esc, r) for r in ("paridade", "ms", "boletim")}
    assert all(x is not None for x in v.values())

    # As duas do MS somam o abandono primário, então superam a do R.
    assert v["boletim"] > v["paridade"], (
        f"esperado boletim > paridade, veio {v['boletim']:.2f} e {v['paridade']:.2f}"
    )
    # E "ms" supera "boletim" porque encolhe o denominador.
    assert v["ms"] > v["boletim"], (
        f"esperado ms > boletim, veio {v['ms']:.2f} e {v['boletim']:.2f}"
    )
    assert len({round(x, 2) for x in v.values()}) == 3, (
        f"as três regras convergiram — alguém igualou definições sem querer: {v}"
    )


# --- Tabela 9: desfechos de encerramento, Brasil 2024 -----------------------

TABELA_9 = REFERENCIA["tabela_9_brasil_2024"]

#: Quanto a cura e a interrupção podem ficar **acima** do boletim.
#:
#: Maior que `MARGEM_ACIMA`, e por um motivo conhecido, não por frouxidão: o
#: denominador do MS inclui casos sem SITUA_ENCE preenchido, que no nosso
#: agregado não existem como linha. Denominador menor dá proporção maior, e
#: medimos +1,73 ponto na cura e +0,32 na interrupção.
#:
#: 3 pontos deixa folga para a variação entre extrações sem deixar passar uma
#: mudança de regra: trocar o denominador para o total de casos novos jogaria
#: a cura para 58,3%, e voltar a contar só o abandono clássico a mudaria em
#: mais de meio ponto.
MARGEM_ACIMA_DESFECHO = 3.0

#: E quanto podem ficar abaixo. Apertado: ficar **abaixo** é o que não tem
#: explicação aqui, porque o efeito conhecido empurra para cima.
MARGEM_ABAIXO_DESFECHO = 0.5


@pytest.mark.parametrize("indicador", ["cura", "interrupcao"])
def test_desfechos_ficam_acima_do_boletim_e_dentro_da_folga(indicador: str) -> None:
    """Cura e interrupção do card, contra a Tabela 9.

    Não é paridade — é uma faixa, e a faixa é assimétrica de propósito. Ver
    `MARGEM_ACIMA_DESFECHO` e `excecoes.md` §5: a diferença é o denominador,
    e ela empurra os dois para cima.
    """
    esc = Escopo(pack.DOENCA, 2024, "BR")
    nosso = getattr(calc.calcular(esc), {"cura": "cura_pct", "interrupcao": "interrupcao_trat_pct"}[indicador])
    oficial = TABELA_9[indicador]

    assert nosso >= oficial - MARGEM_ABAIXO_DESFECHO, (
        f"{indicador}: {nosso:.2f}% contra {oficial}% do boletim. Ficar abaixo "
        f"não tem explicação — o denominador menor que o do MS empurra para cima."
    )
    assert nosso <= oficial + MARGEM_ACIMA_DESFECHO, (
        f"{indicador}: {nosso:.2f}% contra {oficial}% do boletim, acima da "
        f"folga de {MARGEM_ACIMA_DESFECHO} ponto. A regra mudou?"
    )


def test_o_denominador_do_ms_continua_maior_que_o_nosso() -> None:
    """Prende a causa da divergência, não só o efeito.

    Se um dia o `sinan_landing` passar a trazer os casos sem encerramento, a
    diferença some e este teste falha pedindo que a exceção saia de
    `excecoes.md`. É o mesmo desenho de `test_divergentes_continuam_divergindo`.
    """
    from src.data import leitura

    esc = Escopo(pack.DOENCA, 2024, "BR")
    com_encerramento = float(leitura.variavel_sinan(esc, "SITUA_ENCE")["n"].sum())
    # `TRATAMENTO` é preenchido para praticamente todo caso novo, e serve de
    # proxy do total: 85.936 contra os 86.204 que o boletim publica.
    casos_novos = float(leitura.variavel_sinan(esc, "TRATAMENTO")["n"].sum())

    sem_encerramento = casos_novos - com_encerramento
    assert sem_encerramento > 5_000, (
        f"só {sem_encerramento:,.0f} casos sem encerramento — se o dataset "
        f"passou a trazê-los, o denominador pode virar o do MS e a exceção de "
        f"excecoes.md §5 sai"
    )
