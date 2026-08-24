# Inventário de funcionalidades

Checklist de paridade com o dashboard em R. Levantado a partir do código-fonte
original (`app_shell.R`, `mod_state.R`, `mod_kpis.R`, `mod_map.R`, `mod_charts.R`).

Marque conforme implementa. "Idêntico" significa esta lista inteira marcada.

> **Auditado em 2026-08-07** contra o código, item a item. A lista havia ficado
> para trás — mapa, KPIs e recortes de saúde estavam implementados e
> verificados em tela, mas seguiam desmarcados. Numa checklist de paridade
> isso é pior que inútil: apaga a diferença entre "não fizemos" e "não
> anotamos", e some com a lista curta do que falta de verdade.

> **Auditado de novo em 2026-08-23.** Sobraram 13 itens desmarcados, e
> **nenhum é trabalho parado do painel de tuberculose.** Eles se dividem em
> três baldes, que a checklist não distinguia:
>
> | Balde | Itens | Situação |
> |---|---:|---|
> | **Hanseníase** | 5 | Fora do escopo desta entrega. O painel é só de tuberculose, por decisão de 21/ago. Entram com o pack da doença, se ele existir |
> | **Bloqueado na origem** | 1 | Pirâmide de CURA. O dado chega zerado; é falha do pipeline da equipe parceira, confirmada contra o SINAN bruto |
> | **Superset** | 7 | Semana 7, adiada. É produto separado, não parte do painel |
>
> Do que é escopo nosso e depende só de nós: **nada em aberto.**
>
> **Revisto em 2026-08-11**, agora com o app rodando e medição no navegador.
> A seção de KPIs descrevia o card como clicável e navegável por teclado; isso
> saiu do código em 08/ago e a lista não acompanhou. O risco aqui é o inverso
> do de 08/ago: a checklist mandava reimplementar um comportamento que foi
> **removido de propósito**. Também entrou aqui o primeiro item marcado como
> declarado-mas-sem-efeito (o `clamp` do título), categoria que faltava —
> "está no código" e "chega na tela" não são a mesma coisa quando o CSS
> disputa especificidade com o Streamlit.

**Ainda aberto:** o mapa por clique tem um *zoom* travado de propósito (ver
Transversal), a pirâmide não tem CURA por falta de fonte, a decisão sobre a
metodologia do abandono depende da equipe parceira, e o `clamp` do título da
faixa de intro está declarado mas perde em especificidade para o Streamlit
(ver Faixa de intro).

## Sidebar (380px)

- [x] Título da doença
- [x] Slider de ano com *snap* — `st.select_slider` sobre `anos_disponiveis`, que lê os anos de disco (2010–2025)
- [ ] Filtro de grau de incapacidade — **é de Hanseníase**, não de TB; entra com o pack dela
- [x] Métrica ativa na barra lateral. **Divergência:** é legenda de texto, não *badge*
- [x] Botões Voltar / Reset
- [x] Breadcrumb de escopo — ex.: `Escopo: UF PE • Macrorregiões • Ano: 2024`

## Faixa de intro

- [x] Título · logotipo. **Divergência intencional:** o original tem três
  colunas, com a bandeira de Pernambuco à esquerda. Removida — os dados são
  nacionais, e ao lado de um mapa do Brasil a bandeira lia como recorte
  geográfico em vez de emissor. Sem logotipo, o título ocupa a faixa toda
- [x] Título com `clamp(24px, 2.1vw, 30px)` — **corrigido em 18/ago/2026.**
      Ficou declarado e sem efeito por semanas: o token existia
      (`tokens.TEXTO_TITULO`) e a regra `.sinan-intro-titulo` também, mas o
      elemento é um `<h1>` e o seletor do Streamlit (`.st-emotion-cache-… h1`,
      `2.75rem`) tinha especificidade maior e vencia — medido no navegador,
      44px contra os 30 de teto, e era o que fazia o título quebrar em telas
      estreitas. Resolvido subindo para `.sinan-intro h1.sinan-intro-titulo`.
      Fica registrado porque a armadilha vale para qualquer regra que dispute
      com o tema do Streamlit

## KPIs

Grid responsivo: `repeat(auto-fit, minmax(180px, 1fr))`, com quebras em 1240px,
860px e 460px.

- [x] `cases` — casos novos
- [x] `cases_0_14`
- [x] `taxa_det_0_14`
- [x] `incid` — incidência por 100 mil
- [x] `obitos` — do SIM, não do SINAN
- [x] `cura`
- [x] `pop`
- [x] `mortalidade`
- [x] `letalidade`
- [x] `hiv_pos_pct` (TB)
- [x] `interrupcao_trat_pct` (TB) — regra do R; ver armadilha 4

Comportamento:

- [x] `KPI_LAYOUT` do *disease pack* controla quais aparecem e em que ordem
- [x] Delta vs ano anterior
- [x] Semântica de cor **invertida para cura** — queda é ruim; nas demais, queda é boa
- [x] Acento lateral na cor da métrica, via `--kpi-accent` inline
- [x] Estados de hover e seleção — o card espelha a métrica ativa por
      `.is-selected`, o que é leitura, não interação
- [x] Troca da métrica do mapa. **Divergência intencional:** no original é o
      próprio card que é clicável; aqui quem troca é um `st.radio` ao lado do
      mapa (`app.py:374`). O card é um `<div>` sem `tabindex` nem `role` —
      não é focável e não responde a teclado. Decidido em 08/ago/2026, depois
      de quatro rodadas de conserto do `<button>` transparente que ficava
      esticado por cima. Ver a docstring de `componentes.card_kpi` e
      `excecoes.md` §4
- [x] Ajuda por card — atributo `title`, já que sem botão não há `help` do
      Streamlit para receber. **Limitação conhecida:** tooltip nativo não
      aparece em toque

## Mapa

- [x] Drill-down por clique: BR → UF → MUN
- [x] `fitBounds` ao trocar de nível — `mapa.enquadrar`
- [x] Modo "detalhe" do município
- [x] Escala em 6 classes — `mapa.escala_natural`, com colapso de cortes
      repetidos. **Divergência intencional:** o original usa quantil; aqui são
      quebras naturais, porque o quantil comprimia a cauda e o ranking herdava
      o problema. Ver `excecoes.md` §4
- [x] Legenda — em HTML, porque o deck.gl não desenha uma
- [x] `#F3F4F6` para valor ausente
- [x] Rampa do *disease pack*, com fallback gerado a partir da cor base
- [x] Toggle Município / Macrorregião / Região de saúde — genérico, hoje só PE tem malha
- [x] Drill macro → micro → município
- [x] Busca de município, rótulo `"Nome - Região de Saúde"` em PE
- [x] Hover box — tooltip do deck.gl
- [x] Botão de voltar dentro do mapa

## Gráficos

### Evolução temporal
- [x] Toggle *Meses do ano* / *Todos os anos*
- [x] Série dupla casos + incidência (TB)
- [ ] Quebra por grau (Hanseníase)
- [x] Reage à métrica ativa

### Ranking de municípios
- [x] Top N configurável
- [x] Alternância UF / MUN
- [x] Clique na barra navega o mapa

### Pirâmide etária
- [x] Pirâmide por sexo e faixa, com as onze faixas sempre presentes
- [x] Taxa por 100 mil habitantes — substitui a população de fundo do original.
      Sobrepor as duas exigiria dois eixos x, e aí o comprimento de uma barra
      não diz nada sobre a outra. A taxa usa a mesma população e cabe num eixo.
- [x] CASOS, de `piramides`
- [x] OBITOS, de `obitos_sim_faixa` (SIM) — mistura de fontes sinalizada na tela
- [ ] CURA — **sem fonte local.** `piramides` traz zerado para TB e nenhum outro
      parquet quebra cura por idade. Depende do banco.
      Ver contrato-dados, armadilha 9

### Fora das abas
- [x] Cultura em retratamento (TB) — **o original não exibe**, o dado estava sem uso
- [x] Contatos examinados (TB) — idem
- [ ] Classificação operacional (Hanseníase)
- [ ] Casos 0–14 + taxa de detecção (Hanseníase)
- [ ] `kpi_mb_prop` e `kpi_grau2_prop` (Hanseníase)

## Faixa de composição

- [x] Seletor + barras horizontais por variável do SINAN
- [x] **24 variáveis** em 5 grupos, contra 9 no painel de PE e 7 no nacional.
      O dado já está nos mesmos parquets; só entram as que dá para rotular
      com segurança. `AGRAVDROGAS` e `AGRAVTABACO`, que o pack listava, **não
      existem** nos dados — o catálogo antigo nunca tinha sido exercitado
- [x] Rótulos amigáveis do pack, agrupados no seletor
- [x] Filtragem por **código**, nunca por `valor_lbl`
- [x] Percentual suprimido abaixo de 5 registros — ver `leitura.composicao`

## Transversal

- [x] Tooltips de ajuda — nos 6 KPIs e nos controles ambíguos. Explicam sobretudo o **denominador**, que é onde mora a dúvida
- [x] Indicador de carregamento — o do próprio Streamlit, no canto.
      **Divergência intencional:** o original cobre a tela com "Carregando
      dados...", que bloqueia por volta de 3 s na carga inicial. Copiar isso
      seria anunciar uma lentidão que não temos; o indicador discreto do
      Streamlit basta porque as leituras vêm de parquet pré-agregado com cache
- [x] Tratamento de erro por componente — `src/resiliencia.py`; verificado injetando falha
- [x] Estados vazios (ano sem SIM, município sem caso) + aviso de ano incompleto, que o original também tem

## Além do original

Funcionalidade que o dashboard em R não tem. Ver `docs/analise-livre.md`.

### Aba de Análise Livre (Superset)
- [ ] Views curadas: `vw_incidencia`, `vw_serie_mensal`, `vw_obitos_sim`, `vw_sinan_variaveis`
- [ ] `trim()` e mapa canônico de doença aplicados dentro das views
- [ ] Conexão DuckDB registrada no Superset
- [ ] Iframe no mesmo domínio, subcaminho `/cenarios/superset/`
- [ ] Redirecionamento pós-login para o Explore de `vw_incidencia`
- [ ] Role Gamma para analistas
- [ ] Auto-cadastro restrito por domínio de e-mail institucional

## Além do original: tema

O dashboard em R não tem tema escuro. Aqui o **claro é o padrão** e o escuro é
a alternativa, pelo menu do Streamlit (⋮ → Settings → Appearance).

- [x] Claro por padrão, mesmo com o sistema operacional em escuro
- [x] Escuro disponível como alternativa
- [x] Componentes próprios acompanham o tema sem detectá-lo

## Deliberadamente fora

O original despeja um arquivo `.Rmd` de debug a cada render — havia ~90 acumulados
no diretório de logs. Não replicar.
