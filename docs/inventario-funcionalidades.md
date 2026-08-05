# Inventário de funcionalidades

Checklist de paridade com o dashboard em R. Levantado a partir do código-fonte
original (`app_shell.R`, `mod_state.R`, `mod_kpis.R`, `mod_map.R`, `mod_charts.R`).

Marque conforme implementa. "Idêntico" significa esta lista inteira marcada.

## Sidebar (380px)

- [x] Título da doença
- [ ] Slider de ano 2010–2025, com *snap* para os anos existentes em disco
- [ ] Filtro de grau de incapacidade (TB e Hanseníase), opções descobertas em runtime
- [ ] Badge da métrica ativa
- [x] Botões Voltar / Reset
- [x] Breadcrumb de escopo — ex.: `Escopo: UF PE • Macrorregiões • Ano: 2024`

## Faixa de intro

- [x] Grid de 3 colunas: bandeira · título · logo — sem as imagens, que não vieram na entrega, o título ocupa a faixa toda
- [x] Título com `clamp(18px, 2.1vw, 30px)`

## KPIs

Grid responsivo: `repeat(auto-fit, minmax(180px, 1fr))`, com quebras em 1240px,
860px e 460px.

- [ ] `cases` — casos novos
- [ ] `cases_0_14`
- [ ] `taxa_det_0_14`
- [ ] `incid` — incidência por 100 mil
- [ ] `obitos`
- [ ] `cura`
- [ ] `pop`
- [ ] `mortalidade`
- [ ] `letalidade`
- [ ] `hiv_pos_pct` (TB)
- [ ] `interrupcao_trat_pct` (TB)

Comportamento:

- [x] `KPI_LAYOUT` do *disease pack* controla quais aparecem e em que ordem
- [x] Card clicável troca a métrica ativa, repintando mapa e gráficos
- [x] Delta vs ano anterior
- [x] Semântica de cor **invertida para cura** — queda é ruim; nas demais, queda é boa
- [x] Acento lateral na cor da métrica, via `--kpi-accent` inline
- [x] Estados de hover, foco e seleção
- [x] Navegação por teclado (Enter / Espaço) — via `<button>` nativo, e não
      um `div` com `role="button"` como no original

## Mapa

- [ ] Drill-down por clique: BR → UF → MUN
- [ ] `fitBounds` ao trocar de nível
- [ ] Modo "detalhe" do município
- [ ] Escala por quantil k=6
- [ ] Legenda
- [ ] `#F3F4F6` para valor ausente
- [ ] Rampa do *disease pack*, com fallback gerado a partir da cor base
- [ ] Toggle Município / Macrorregião / Região de saúde (exclusivo de PE)
- [ ] Drill macro → micro → município
- [ ] Busca de município, rótulo `"Nome - Região de Saúde"`
- [ ] Hover box
- [ ] Botão de voltar dentro do mapa

## Gráficos

### Evolução temporal
- [ ] Toggle *Meses do ano* / *Todos os anos*
- [ ] Série dupla casos + incidência (TB)
- [ ] Quebra por grau (Hanseníase)
- [ ] Reage à métrica ativa

### Ranking de municípios
- [ ] Top N configurável
- [ ] Alternância UF / MUN
- [ ] Clique na barra navega o mapa

### Pirâmide etária
- [ ] População como fundo + casos sobrepostos (estilo IBGE)
- [ ] `ratio` por faixa
- [ ] Alternância `tipo` = CASOS / CURA / OBITOS — **CURA e OBITOS estão vazios
      para TB**; a pirâmide de óbitos tem de sair de `obitos_sim_faixa`.
      Ver contrato-dados, armadilha 9

### Fora das abas
- [ ] Cultura em retratamento (TB)
- [ ] Contatos examinados (TB)
- [ ] Classificação operacional (Hanseníase)
- [ ] Casos 0–14 + taxa de detecção (Hanseníase)
- [ ] `kpi_mb_prop` e `kpi_grau2_prop` (Hanseníase)

## Faixa de composição

- [ ] Grid de 2 colunas, barras por variável SINAN
- [ ] Variáveis do pack de TB: `TRATAMENTO`, `HIV`, `FORMA`, `CS_RACA`,
      `AGRAVALCOO`, `SITUA_ENCE`, `POP_RUA`, `POP_SAUDE`, `AGRAVDROGAS`, `AGRAVTABACO`
- [ ] Rótulos amigáveis do pack
- [ ] Filtragem por **código**, nunca por `valor_lbl`

## Transversal

- [ ] Tooltips de ajuda (badge "i")
- [ ] Overlay de carregamento
- [ ] Tratamento de erro por componente — um gráfico quebrado não derruba a página
- [ ] Estados vazios (ano sem dado, município sem caso)

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
