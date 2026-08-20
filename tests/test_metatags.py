"""A prévia de link precisa apontar para onde o painel realmente está.

Compartilhar o link mostrava só "Streamlit" e o domínio: o `page_title` entra
por JavaScript e nenhum rastreador de prévia espera o JS rodar. As metatags
são injetadas no build por `scripts/preparar_metatags.py`.

O modo de apodrecer é silencioso: alguém troca o subcaminho do painel e a
prévia passa a apontar para uma URL que dá 404 — a mensagem no WhatsApp
continua bonita, e o clique não leva a lugar nenhum.
"""

from __future__ import annotations

import io
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]
META = RAIZ / "scripts" / "preparar_metatags.py"
DOCKERFILE = RAIZ / "dockerfile" if (RAIZ / "dockerfile").exists() else RAIZ / "Dockerfile"


def _fonte(p: pathlib.Path) -> str:
    return io.open(p, encoding="utf-8").read()


def test_a_url_da_previa_bate_com_o_subcaminho_servido() -> None:
    """`og:url` e o `baseUrlPath` do container têm de contar a mesma história."""
    import re

    meta = _fonte(META)
    docker = _fonte(DOCKERFILE)

    caminho = re.search(r"--server\.baseUrlPath=([\w/-]+)", docker)
    assert caminho, "não achei `--server.baseUrlPath` no Dockerfile"
    subcaminho = caminho.group(1)

    url = re.search(r'^URL = "([^"]+)"', meta, re.M)
    assert url, "não achei a constante URL em preparar_metatags.py"

    assert subcaminho in url.group(1), (
        f"a prévia aponta para {url.group(1)!r}, mas o painel é servido em "
        f"{subcaminho!r} — o link do WhatsApp levaria a um 404"
    )


def test_a_imagem_da_previa_existe_e_tem_o_tamanho_declarado() -> None:
    """1200x630 não é capricho: é o que os rastreadores esperam recortar."""
    from PIL import Image

    img = RAIZ / "assets" / "preview.png"
    assert img.exists(), "assets/preview.png sumiu — a prévia ficaria sem imagem"

    with Image.open(img) as im:
        assert im.size == (1200, 630), f"esperado 1200x630, veio {im.size}"

    meta = _fonte(META)
    assert 'content="1200"' in meta and 'content="630"' in meta, (
        "as metas og:image:width/height precisam bater com o arquivo"
    )


def test_o_script_falha_alto_se_a_ancora_sumir() -> None:
    """Streamlit novo pode mudar o HTML; o build tem de quebrar, não seguir.

    Sem isto, uma atualização do Streamlit devolveria em silêncio uma imagem
    que se anuncia como "Streamlit" ao ser compartilhada.
    """
    meta = _fonte(META)
    assert "return 1" in meta, "o script precisa sair com erro quando não casar"
    assert "ANCORA" in meta
