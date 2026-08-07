"""Estado de navegação do dashboard.

Deliberadamente sem dependência do Streamlit: a máquina de estados é testada
sozinha, e a aplicação só guarda uma instância em ``st.session_state``.

O caminho de ida é ``BR → UF → município``, com um desvio exclusivo de PE que
passa por macrorregião e região de saúde. O ``voltar`` desfaz esse caminho um
passo por vez, replicando o ``mod_state.R`` do original.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import config, recortes
from .data.escopo import Escopo, mun6

#: Recortes do mapa no nível UF. ``MUN`` é o padrão; os outros dois são
#: exclusivos de Pernambuco e vêm dos shapefiles de apoio.
RECORTES = ("MUN", "MACRO", "MICRO")

#: Mantido para leitura; a verdade está no registro de `data/recortes.py`.
UF_COM_RECORTES = recortes.UF


@dataclass
class Navegacao:
    """Recorte corrente. Mutável — a aplicação guarda uma instância viva."""

    doenca: str = config.TUBERCULOSE
    ano: int = config.ANO_MAX - 1
    metrica: str = "incid"

    nivel: str = "BR"
    uf: str | None = None
    mun: str | None = None
    detalhe: bool = False

    recorte: str = "MUN"
    macro: str | None = None
    micro: str | None = None

    #: Rótulo do município corrente, só para exibição.
    nome_mun: str | None = None

    _historico: list[str] = field(default_factory=list, repr=False)

    # -- consultas ----------------------------------------------------------

    @property
    def escopo(self) -> Escopo:
        """Recorte no formato que a camada de dados consome."""
        return Escopo(
            doenca=self.doenca,
            ano=self.ano,
            nivel=self.nivel,
            uf=self.uf,
            mun=self.mun,
        )

    @property
    def tem_recortes_de_saude(self) -> bool:
        """A UF corrente tem macrorregião e região de saúde configuradas?

        Hoje só PE, mas a resposta vem do registro — acrescentar um estado não
        exige tocar aqui.
        """
        return recortes.configurada(self.uf)

    @property
    def pode_voltar(self) -> bool:
        return not (self.nivel == "BR" and not self.detalhe)

    # -- ida ----------------------------------------------------------------

    def entrar_uf(self, uf: str) -> None:
        self.uf = str(uf).strip().upper()
        self.nivel = "UF"
        self.mun = None
        self.nome_mun = None
        self.detalhe = False
        if not self.tem_recortes_de_saude:
            self.recorte = "MUN"
            self.macro = None
            self.micro = None

    def entrar_municipio(self, mun: str, nome: str | None = None) -> None:
        self.mun = mun6(mun)
        self.nome_mun = nome
        self.nivel = "MUN"
        self.detalhe = False

    def abrir_detalhe(self) -> None:
        if self.nivel != "MUN":
            raise ValueError("Detalhe só existe no nível de município.")
        self.detalhe = True

    def definir_recorte(self, recorte: str) -> None:
        """Troca entre município, macrorregião e região de saúde."""
        valor = str(recorte or "MUN").strip().upper()
        if valor not in RECORTES:
            raise ValueError(f"Recorte inválido: {recorte!r}. Esperado {RECORTES}.")
        if valor != "MUN" and not self.tem_recortes_de_saude:
            raise ValueError(
                f"{self.uf} não tem recorte de saúde. "
                f"Configuradas: {recortes.ufs_com_recorte()}."
            )
        self.recorte = valor
        # Trocar de recorte descarta a seleção do recorte anterior.
        if valor == "MUN":
            self.macro = self.micro = None
        elif valor == "MACRO":
            self.macro = self.micro = None
        else:
            self.micro = None

    def entrar_macro(self, macro: str) -> None:
        """Clicar numa macrorregião filtra as regiões de saúde dentro dela."""
        self.macro = str(macro).strip()
        self.recorte = "MICRO"
        self.micro = None

    def entrar_micro(self, micro: str) -> None:
        """Clicar numa região de saúde filtra os municípios dentro dela."""
        self.micro = str(micro).strip()
        self.recorte = "MUN"

    # -- volta --------------------------------------------------------------

    def voltar(self) -> None:
        """Desfaz um passo do caminho de ida.

        A ordem das regras importa e reproduz o ``mod_state.R``:

        1. município em detalhe → fecha o detalhe
        2. município → UF, voltando ao recorte de região de saúde se foi por lá
        3. UF vendo regiões de saúde de uma macro → volta a ver as macros
        4. UF → BR, limpando tudo
        5. BR → não faz nada
        """
        if self.nivel == "MUN" and self.detalhe:
            self.detalhe = False
            return

        if self.nivel == "MUN":
            self.nivel = "UF"
            self.mun = None
            self.nome_mun = None
            self.detalhe = False
            if self.micro is not None:
                self.micro = None
                self.recorte = "MICRO"
            return

        if self.nivel == "UF":
            if self.recorte == "MICRO" and self.macro is not None:
                self.macro = None
                self.recorte = "MACRO"
                return
            self.reset(manter_ano=True)
            return

    def reset(self, manter_ano: bool = True) -> None:
        """Volta ao Brasil, limpando todo o recorte geográfico."""
        self.nivel = "BR"
        self.uf = None
        self.mun = None
        self.nome_mun = None
        self.detalhe = False
        self.recorte = "MUN"
        self.macro = None
        self.micro = None
        if not manter_ano:
            self.ano = config.ANO_MAX - 1

    # -- exibição -----------------------------------------------------------

    def trilha(self) -> str:
        """Breadcrumb do recorte, no formato do original."""
        partes: list[str] = []

        if self.nivel == "BR":
            partes.append("Brasil")
        elif self.nivel == "UF":
            partes.append(f"UF {self.uf}")
            if self.recorte == "MACRO":
                partes.append("Macrorregiões")
            elif self.recorte == "MICRO":
                if self.macro:
                    partes.append(f"Macro: {self.macro}")
                partes.append("Regiões de saúde")
            elif self.micro:
                partes.append(f"Micro: {self.micro}")
                partes.append("Municípios")
        else:
            partes.append(str(self.uf or "—"))
            partes.append(f"Município: {self.nome_mun or self.mun or '—'}")
            if self.detalhe:
                partes.append("detalhe")

        partes.append(f"Ano: {self.ano}")
        return " • ".join(partes)
