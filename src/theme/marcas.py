"""Bandeira e logotipo da faixa de intro.

Ficam em ``assets/``, versionados — e não em ``data/``, que é ignorado pelo
git. São identidade visual, não dado: não mudam quando o SINAN atualiza, e sem
eles o dashboard fica descaracterizado em qualquer máquina nova. São 77 KB.

``data/support/`` continua sendo consultado depois, porque é onde o projeto em
R os procurava e é para onde alguém tenderia a copiá-los.

Os dois **não vieram** na entrega do projeto em R — o código de lá, não
achando, renderizava a faixa sem imagem nenhuma, em silêncio. Aqui
:func:`disponiveis` diz o que falta, para a aplicação avisar em vez de só
omitir.
"""

from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

from ..data import config

#: Nomes procurados, na ordem de preferência. Os dois primeiros são os do
#: original; os demais são variações razoáveis de quem for repor os arquivos.
BANDEIRA = ("bandeira_pe.png", "Bandeira_de_Pernambuco.jpeg", "bandeira_pe.jpeg")
LOGO = ("cenarios_logo_full.jpeg", "cenarios_logo.png", "logo.png")


def diretorios() -> tuple[Path, ...]:
    """Onde procurar, em ordem: o repositório primeiro, os dados depois."""
    return (config.PROJECT_ROOT / "assets", config.support_dir())


def _achar(nomes: tuple[str, ...]) -> Path | None:
    for base in diretorios():
        for nome in nomes:
            caminho = base / nome
            if caminho.is_file():
                return caminho
    return None


def _data_uri(caminho: Path) -> str:
    tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
    dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
    return f"data:{tipo};base64,{dados}"


@lru_cache(maxsize=1)
def bandeira() -> str | None:
    caminho = _achar(BANDEIRA)
    return _data_uri(caminho) if caminho else None


@lru_cache(maxsize=1)
def logo() -> str | None:
    caminho = _achar(LOGO)
    return _data_uri(caminho) if caminho else None


def disponiveis() -> dict[str, bool]:
    """O que foi encontrado. Serve para a aplicação avisar o que falta."""
    return {"bandeira": bandeira() is not None, "logo": logo() is not None}


def faltando() -> list[str]:
    """Nomes esperados do que não foi encontrado."""
    ausentes = []
    if bandeira() is None:
        ausentes.append(BANDEIRA[0])
    if logo() is None:
        ausentes.append(LOGO[0])
    return ausentes


def onde(nomes: tuple[str, ...]) -> Path | None:
    """Caminho do arquivo encontrado, para diagnóstico."""
    return _achar(nomes)
