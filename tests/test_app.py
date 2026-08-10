"""Checagens estáticas do `app.py`.

A suíte não importa o `app.py` — importar dispara `st.set_page_config` e o
resto do script. O preço disso ficou visível quando o ajuste de cache colocou
`TTL_DADOS` **depois** do primeiro decorador que o usa: o app quebrava na
importação com `NameError` e os 629 testes continuavam verdes.

Estes testes leem o módulo com `ast`, sem executá-lo.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
ARVORE = ast.parse(APP.read_text(encoding="utf-8"))


def _definidos_ate(linha: int) -> set[str]:
    """Nomes atribuídos ou importados no nível do módulo antes de `linha`."""
    nomes: set[str] = set()
    for no in ARVORE.body:
        if no.lineno >= linha:
            break
        if isinstance(no, ast.Assign):
            nomes.update(
                alvo.id for alvo in no.targets if isinstance(alvo, ast.Name)
            )
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            nomes.add(no.target.id)
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            nomes.update(a.asname or a.name.split(".")[0] for a in no.names)
        elif isinstance(no, (ast.FunctionDef, ast.ClassDef)):
            nomes.add(no.name)
    return nomes


def test_decorador_nao_usa_nome_definido_depois() -> None:
    """Decorador roda na importação, de cima para baixo.

    Foi exatamente assim que `TTL_DADOS` quebrou o app: a constante estava
    definida umas 150 linhas abaixo do primeiro `@st.cache_data` que a lia.
    """
    problemas: list[str] = []
    for no in ARVORE.body:
        if not isinstance(no, (ast.FunctionDef, ast.ClassDef)):
            continue
        disponiveis = _definidos_ate(no.lineno)
        for dec in no.decorator_list:
            for usado in ast.walk(dec):
                if isinstance(usado, ast.Name) and usado.id not in disponiveis:
                    problemas.append(
                        f"linha {no.lineno}: decorador de `{no.name}` usa "
                        f"`{usado.id}`, definido depois"
                    )
    assert not problemas, "\n".join(problemas)


def test_constantes_de_cache_existem() -> None:
    nomes = _definidos_ate(10**9)
    for c in ("TTL_DADOS", "ENTRADAS_LEVES", "ENTRADAS_MEDIAS",
              "ENTRADAS_PESADAS", "ENTRADAS_GEOMETRIA"):
        assert c in nomes, f"{c} sumiu do app.py"


def test_app_compila() -> None:
    compile(APP.read_text(encoding="utf-8"), str(APP), "exec")
