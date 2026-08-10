"""Varredura do harness em todos os anos e níveis.

O item da semana 6 é rodar a paridade inteira, não uma amostra. Estes testes
percorrem os 16 anos disponíveis e os três níveis, checando invariantes que
não dependem de referência externa: se a camada de dados e o gerador de
referências partirem da mesma premissa errada, os dois concordam — é para
essa classe de erro que a varredura serve.
"""

from __future__ import annotations

import pytest

from src.data import conexao, config, leitura
from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import tuberculose as pack

ANOS = leitura.anos_disponiveis(pack.DOENCA)
#: Amostra de UFs com perfis diferentes: a maior, a menor, o alvo e uma do Norte.
UFS = ["SP", "RR", "PE", "AM"]


def test_ha_anos_para_varrer() -> None:
    assert len(ANOS) >= 15, f"esperava a série histórica inteira, veio {ANOS}"


@pytest.mark.parametrize("ano", ANOS)
def test_totais_fecham_entre_os_tres_niveis(ano: int) -> None:
    """BR tem de ser a soma das UFs e a soma dos municípios.

    Divergência aqui significaria que o mapa e os KPIs contam populações
    diferentes — e o usuário veria um total que não bate com o que somou na
    tela.
    """
    con = conexao.conectar()

    def soma(nivel: str) -> tuple[float, float]:
        # `caminho()` e não glob da raiz: os arquivos de `nivel=BR` não têm a
        # coluna `uf` e os de `MUN` não têm a mesma que os de `UF`. Um glob
        # amplo faz o DuckDB unir tudo pelo esquema do primeiro arquivo e
        # sumir com colunas — é a armadilha 8, e este teste caiu nela.
        fonte = conexao.caminho(
            "incidence", doenca=pack.DOENCA, nivel=nivel, ano=ano
        )
        return con.execute(
            f"SELECT sum(casos_total), sum(pop_total) "
            f"FROM read_parquet('{fonte}', hive_partitioning=true)"
        ).fetchone()

    br, uf, mun = soma("BR"), soma("UF"), soma("MUN")
    assert br == uf, f"{ano}: BR {br} != soma das UFs {uf}"
    assert br == mun, f"{ano}: BR {br} != soma dos municípios {mun}"


@pytest.mark.parametrize("ano", ANOS)
def test_metricas_derivadas_batem_com_seus_componentes(ano: int) -> None:
    """`incid`, `mortalidade` e `letalidade` são razões — têm de fechar."""
    k = calc.calcular(Escopo(pack.DOENCA, ano, "BR"))

    if k.incid is not None and k.pop:
        assert k.incid == pytest.approx(k.casos / k.pop * 1e5, rel=1e-6)
    if k.mortalidade is not None and k.pop:
        assert k.mortalidade == pytest.approx(k.obitos / k.pop * 1e5, rel=1e-6)
    if k.letalidade is not None and k.casos:
        assert k.letalidade == pytest.approx(k.obitos / k.casos * 100, rel=1e-6)


@pytest.mark.parametrize("ano", ANOS)
def test_percentuais_ficam_no_intervalo(ano: int) -> None:
    """Proporção fora de 0–100 denuncia denominador errado."""
    k = calc.calcular(Escopo(pack.DOENCA, ano, "BR"))
    for nome in ("hiv_pos_pct", "interrupcao_trat_pct", "letalidade"):
        valor = getattr(k, nome)
        if valor is not None:
            assert 0 <= valor <= 100, f"{ano}: {nome} = {valor}"


@pytest.mark.parametrize("uf", UFS)
def test_uf_fecha_com_seus_municipios(uf: str) -> None:
    """A soma dos municípios de uma UF tem de dar o total dela."""
    con = conexao.conectar()
    fonte_uf = conexao.caminho("incidence", doenca=pack.DOENCA, nivel="UF", ano=2024)
    fonte_mun = conexao.caminho("incidence", doenca=pack.DOENCA, nivel="MUN", ano=2024)

    total = con.execute(
        f"SELECT sum(casos_total) FROM read_parquet('{fonte_uf}', "
        f"hive_partitioning=true) WHERE uf = ?",
        [uf],
    ).fetchone()[0]
    partes = con.execute(
        f"SELECT sum(casos_total) FROM read_parquet('{fonte_mun}', "
        f"hive_partitioning=true) WHERE substr(cod_mun6, 1, 2) = ?",
        [config.codigo_uf(uf)],
    ).fetchone()[0]
    assert total == partes, f"{uf}: total {total} != soma dos municípios {partes}"


@pytest.mark.parametrize("uf", UFS)
def test_kpis_da_uf_nao_tem_buraco(uf: str) -> None:
    """Nenhuma UF pode ficar sem os KPIs que a tela exibe."""
    k = calc.calcular(Escopo(pack.DOENCA, 2024, "UF", uf=uf))
    for chave in pack.LAYOUT_KPI:
        assert getattr(k, chave) is not None, f"{uf}: {chave} sem valor em 2024"
