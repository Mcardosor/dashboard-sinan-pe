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
    itens = leitura.indicadores_programa(esc, pack.INDICADORES_PROGRAMA)
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
        Escopo(pack.DOENCA, 2024, "MUN", uf="MG", mun="311280"),
        pack.INDICADORES_PROGRAMA,
    )
    assert len(itens) == 2
    assert all(i["pct"] is None for i in itens)


def test_nao_divide_por_zero() -> None:
    """Denominador zero ou ausente vira `None`, nunca exceção."""
    for esc in (Escopo(pack.DOENCA, 1999, "BR"), Escopo(pack.DOENCA, 2024, "MUN", uf="MG", mun="311280")):
        for item in leitura.indicadores_programa(esc, pack.INDICADORES_PROGRAMA):
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
        contatos = leitura.indicadores_programa(esc, pack.INDICADORES_PROGRAMA)[0]["denominador"]
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


def test_spec_dos_indicadores_vive_no_pack() -> None:
    """Rótulo, descrição e cor são específicos da doença.

    Estavam no core de leitura, contrariando o padrão de *disease pack* que o
    próprio projeto documenta. O core agora só resolve
    `numerador/denominador → proporção` a partir da tabela que o pack fornece.
    """
    assert not hasattr(leitura, "INDICADORES_PROGRAMA")
    for spec in pack.INDICADORES_PROGRAMA:
        assert {"chave", "leitor", "rotulo", "numerador", "denominador",
                "cor", "descricao"} <= set(spec)
        assert hasattr(leitura, spec["leitor"]), spec["leitor"]


def test_leitor_citado_por_string_existe_em_leitura() -> None:
    """Os leitores dos indicadores são resolvidos por nome, não importados.

    `leitura.indicadores_programa` faz `globals()[spec["leitor"]](esc)`, com o
    nome vindo do pack. Isso é o que permite uma doença nova declarar seus
    indicadores sem tocar no core — mas cria um vínculo que **nenhuma análise
    estática enxerga**.

    O risco é concreto, não hipotético. Numa varredura de código morto em
    2026-08-20, `indicador_tb_cultura` apareceu como "definida e nunca
    referenciada" e quase foi apagada junto com seis funções que de fato eram
    mortas. Só não foi porque um `grep` mostrou o nome dentro de uma string.

    Este teste é a trava: quem apagar um leitor ainda citado no pack quebra
    aqui, e não em produção quando alguém abrir o painel de indicadores.
    """
    faltando = [
        spec["leitor"]
        for spec in pack.INDICADORES_PROGRAMA
        if not callable(getattr(leitura, spec["leitor"], None))
    ]
    assert not faltando, (
        f"o pack cita leitores que não existem em `leitura`: {faltando}. "
        f"São chamados por nome em `indicadores_programa`, então análise "
        f"estática não os vê — confira antes de apagar."
    )


def test_todo_leitor_de_leitura_citado_no_pack_esta_coberto() -> None:
    """O contrário: nome no pack que ninguém mais cita continua vivo.

    Sem isto, a trava acima protegeria só o que já está declarado hoje. Aqui a
    lista sai do pack, então acrescentar um indicador novo passa a exigir que o
    leitor exista — a proteção acompanha o crescimento do *disease pack*.
    """
    nomes = {spec["leitor"] for spec in pack.INDICADORES_PROGRAMA}
    assert nomes, "o pack de tuberculose deixou de declarar indicadores"
    for nome in nomes:
        assert nome.startswith("indicador_"), (
            f"{nome!r} foge da convenção `indicador_*`, que é o que torna o "
            f"vínculo por string reconhecível numa busca"
        )
