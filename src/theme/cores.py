"""Manipulação de cor e geração de rampas.

O original em R gera a rampa do mapa a partir de uma única cor base, misturando
com branco e preto em proporções fixas. Isso é o que faz o sistema escalar: a
doença declara uma cor por métrica e todo o resto sai daí.
"""

from __future__ import annotations

Rgb = tuple[float, float, float]

#: Proporções de mistura, na ordem em que compõem a rampa. Os valores são os
#: do dashboard em R, mas o lado escuro é aplicado ao contrário do original.
#:
#: No R, o fallback faz ``mix("#000000", base, t)`` com t crescente — ou seja,
#: t é o peso da *base*, então 0.18 dá quase preto e 0.52 clareia de volta. A
#: rampa resultante não é monotônica: sobe, cai para quase preto, e sobe de
#: novo. O defeito passou despercebido porque a TB declara paletas explícitas
#: e o fallback nunca roda para ela. Aqui t é o peso do preto, que escurece
#: progressivamente como uma escala sequencial exige.
_CLAROS = (0.35, 0.55, 0.72)
_ESCUROS = (0.18, 0.34, 0.52)

BRANCO = "#FFFFFF"
PRETO = "#000000"

#: Cinza usado onde não há dado. Precisa ser distinguível de qualquer tom da rampa.
SEM_DADO = "#F3F4F6"


def hex_para_rgb(cor: str) -> Rgb:
    texto = str(cor or "").strip().lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    if len(texto) != 6:
        raise ValueError(f"Cor hexadecimal inválida: {cor!r}")
    return tuple(int(texto[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_para_hex(rgb: Rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def misturar(a: str, b: str, t: float) -> str:
    """Interpola linearmente entre duas cores. ``t=0`` devolve ``a``, ``t=1`` devolve ``b``."""
    ra, rb = hex_para_rgb(a), hex_para_rgb(b)
    return rgb_para_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))  # type: ignore[arg-type]


def rampa(base: str) -> list[str]:
    """Rampa sequencial de 7 tons a partir de uma cor base.

    A base fica no meio; antes dela três tons progressivamente mais claros,
    depois três progressivamente mais escuros.
    """
    claros = [misturar(BRANCO, base, t) for t in _CLAROS]
    escuros = [misturar(base, PRETO, t) for t in _ESCUROS]
    return [*claros, base.upper(), *escuros]


def contraste_texto(fundo: str) -> str:
    """Preto ou branco, o que tiver mais contraste sobre o fundo dado.

    Usa luminância relativa (WCAG), não o brilho ingênuo — a diferença importa
    nos tons de verde e amarelo, onde o cálculo simples erra.
    """

    def canal(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in hex_para_rgb(fundo))
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#111827" if luminancia > 0.179 else "#FFFFFF"
