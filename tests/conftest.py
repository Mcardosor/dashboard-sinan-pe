"""Configuração da suíte.

Os dados não são versionados — são 892 MB — então um clone novo não tem como
rodar a maior parte dos testes. Sem isto, o pytest quebra na **coleta**, com um
`FileNotFoundError` vindo do topo de um módulo, e nem os testes que não
dependem de dado chegam a rodar.

Com isto, quem clona o repositório e roda `pytest` vê os testes de tema,
navegação e resiliência passarem, e uma mensagem dizendo exatamente o que
falta para os demais.
"""

from __future__ import annotations

from pathlib import Path

from src.data import config

#: Módulos que leem parquet, geometria ou os arquivos de apoio.
#: Os demais — tema, estado, resiliência — rodam em qualquer clone.
PRECISAM_DE_DADOS = (
    "test_composicao.py",
    "test_estados_vazios.py",
    "test_geo.py",
    "test_graficos.py",
    "test_mapa.py",
    "test_navegacao_mapa.py",
    "test_piramide.py",
    "test_publicacao.py",
    "test_recortes.py",
)


def _dados_presentes() -> bool:
    """Confere os três diretórios que a aplicação exige para funcionar."""
    dados = config.data_dir()
    return (
        (dados / "parquet" / "dashboard").is_dir()
        and (dados / "geo").is_dir()
        and (dados / "support" / "municipios.csv").is_file()
    )


collect_ignore: list[str] = []

if not _dados_presentes():
    collect_ignore = [*PRECISAM_DE_DADOS, "paridade"]
    print(
        f"\n[conftest] Dados ausentes em {config.data_dir()} — "
        f"{len(collect_ignore)} módulos ignorados.\n"
        f"           Coloque os parquets em data/parquet/dashboard/, "
        f"a geometria em data/geo/ e o apoio em data/support/,\n"
        f"           ou aponte SINAN_DATA_DIR. Ver README e docs/contrato-dados.md.\n"
    )


def pytest_report_header() -> str:
    # Sem parâmetro de propósito: o pytest exige que ele se chame `config`, e
    # esse nome já é o nosso módulo importado acima.
    origem = Path(config.data_dir())
    estado = "presentes" if _dados_presentes() else "AUSENTES"
    return f"dados: {estado} ({origem})"
