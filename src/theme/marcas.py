"""Bandeira e logotipo da faixa de intro.

Os dois arquivos **não vieram** na entrega do projeto em R: o código de lá os
procura dois níveis acima da pasta de dados e, não achando, renderiza a faixa
sem imagem nenhuma — em silêncio.

Aqui o comportamento é o mesmo, mas explícito: :func:`disponiveis` diz o que
falta, para a aplicação poder avisar em vez de só omitir. Basta soltar os
arquivos em ``data/support/`` e a faixa passa a exibi-los, sem tocar em código.
"""

from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

from ..data import config

#: Nomes procurados, na ordem de preferência. Os dois primeiros são os do
#: original; os demais são variações razoáveis de quem for repor os arquivos.
BANDEIRA = ("Bandeira_de_Pernambuco.jpeg", "bandeira_pe.jpeg", "bandeira_pe.png")
LOGO = ("cenarios_logo_full.jpeg", "cenarios_logo.png", "logo.png")


def _achar(nomes: tuple[str, ...]) -> Path | None:
    base = config.support_dir()
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
