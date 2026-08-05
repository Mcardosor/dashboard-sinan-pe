# Cronograma

**Escopo:** Tuberculose · **Dedicação:** 40h/semana · **Equipe:** 1 dev
**Início:** 03/ago/2026 · **Entrega:** 25/set/2026 · **Duração:** 8 semanas

| Semana | Período | Fase |
|---|---|---|
| 1 | 03–07/ago | Fundação |
| 2 | 10–14/ago | Esqueleto + KPIs |
| 3 | 17–21/ago | Mapa |
| 4 | 24–28/ago | Gráficos |
| 5 | 31/ago–04/set | TB específico + composição |
| 6 | 07–11/set | Paridade + performance |
| 7 | 14–18/set | Análise livre (Superset) |
| 8 | 21–25/set | Polimento + deploy |

---

## Semana 1 — Fundação (03–07/ago)

### 1.1 Ambiente e dados
- [ ] Copiar `data/parquet/dashboard/` (888 MB, 2.814 arquivos) para o destino definitivo
- [ ] Copiar os arquivos de apoio de PE para `data/support/` — hoje eles vivem fora de `data/`, 6 níveis acima, e são a única fonte de macro/microrregião:
      `municipios.csv`, `PE MODIF.*`, `PEMacSAUD MODIF.*`, `PERGSAUDE MODIF.*`
- [ ] Criar venv e `requirements.txt`
- [ ] Validar leitura dos 11 datasets e conferir contagem de linhas contra `docs/contrato-dados.md`

### 1.2 Camada de dados (`src/data/`)
- [ ] Conexão DuckDB única em `st.cache_resource`
- [ ] Mapa canônico de doenças — resolve `DENG`/`DENGUE`, `HANS`/`HANSENIASE` entre datasets
- [ ] Normalizações: `trim()` no campo `valor`, padding de `cod_mun6`↔`cod_mun7`, sigla de UF
- [ ] Readers por dataset: `incidence`, `incidence_0_14`, `_cache_ts`, `piramides`,
      `sinan_landing`, `sinan_dict`, `cache_ts_sim_obitos`, `obitos_sim_faixa`,
      `cases_new`, `indicadores_tb_contatos`, `indicadores_tb_cultura_retratamento`
- [ ] Funções de KPI: `incid`, `mortalidade`, `letalidade`, `taxa_det_0_14`,
      `hiv_pos_pct`, `interrupcao_trat_pct`
- [ ] Ligar óbitos de TB ao SIM (`cache_ts_sim_obitos`) — `incidence.casos_obitos` é zero para TB em todos os anos

### 1.3 Harness de paridade (`tests/paridade/`)
- [ ] **Gate: decidir a metodologia do abandono** antes de fixar as referências.
      Regra do R = 11,89% · padrão MS = 14,75% (TB/PE/2024). Conversar com a equipe de R.
- [ ] Extrair ~30 valores de referência do dashboard em R (KPI × nível × ano × recorte)
- [ ] Suite pytest comparando os números com tolerância declarada
- [ ] `excecoes.md` — divergências intencionais, com justificativa

### 1.4 Sistema visual (`src/theme/`)
- [ ] `tokens.py` — cores, raios, sombras, tipografia, breakpoints
- [ ] Gerador de rampa a partir da cor base (mix com branco 35/55/72%, com preto 18/34/52%)
- [ ] `kpi_card()` — acento lateral, `--kpi-accent` inline, hover, foco, teclado
- [ ] `disease_pack` da Tuberculose

**Pronto quando:** o harness roda verde contra as referências e `kpi_card()` renderiza isolado.

---

## Semana 2 — Esqueleto + KPIs (10–14/ago)

### 2.1 Shell da aplicação
- [x] Layout: sidebar 380px + faixa de intro + linha de KPIs + linha principal + faixa de composição
- [x] CSS base injetado uma única vez
- [x] Faixa de intro (bandeira · título · logo) — com degradação graciosa: os
      dois arquivos **não vieram** na entrega do projeto em R, então hoje ela
      mostra só o título e a barra lateral avisa o que falta. Soltar os
      arquivos em `data/support/` passa a exibi-los, sem tocar em código.

### 2.2 Estado de navegação
- [x] `session_state`: uma `Navegacao` viva em `src/estado.py`, com nível, UF,
      município, detalhe, recorte, macro e micro
- [x] Breadcrumb de escopo
- [x] Botões Voltar/Reset — *step-back* do original em cinco regras encadeadas
- [x] Slider de ano com *snap* para os anos existentes em disco

A máquina de estados não depende do Streamlit e é testada sozinha; o teste que
importa percorre o desvio de PE inteiro (UF → macro → micro → município →
detalhe) e desfaz passo a passo, conferindo que se volta ao ponto de partida.

### 2.3 KPIs
- [x] Os 11 cards ligados à camada de dados. A TB exibe 6, que é a paridade
      com o original; os outros 5 servem às demais doenças e têm teste de
      renderização para o defeito não aparecer só quando a próxima entrar
- [x] Delta vs ano anterior, com semântica **invertida para cura** (queda = ruim)
- [x] Clique no card troca a métrica ativa e repinta o resto — `st.button`
      transparente sobre o card, dentro de `st.container(key=...)`
- [x] `KPI_LAYOUT` controlando quais aparecem e em que ordem

### 2.4 Pré-processamento de geometria (`scripts/`)
- [x] Script one-shot: simplificar os GeoJSON por UF com tolerância relativa (`bbox_x / 900`)
- [x] Exportar para GeoParquet + carregador em `src/data/geo.py`
- [x] Medir e registrar o ganho: 133,7 MB → 3,7 MB; carregar PE de 274 ms → 15 ms (18x)
- [x] Simplificação **topológica**, não por polígono — a do original rompe o
      mosaico (1,97% de fresta e 163 pares sobrepostos só no ES)

**Pronto quando:** navegação e KPIs funcionam ponta a ponta, sem mapa e sem gráficos.

---

## Semana 3 — Mapa (17–21/ago) ⚠️ semana de risco

> Componente mais difícil do projeto — 2.507 linhas no original. Se algo estourar
> o prazo, é aqui. A semana 8 existe como folga para isso.

### 3.1 Camada base
- [x] Biblioteca escolhida: **Plotly**. `st.plotly_chart` tem evento de clique
      nativo (`on_select`), o que dispensa `streamlit-folium` como dependência
      de terceiros; e o dashboard demográfico da casa já usa Plotly. Medido
      com dado real: pior caso (MG, 853 municípios) 176 ms somando
      serialização e figura, os dois cacheáveis
- [x] Carregar geometria pré-simplificada (`src/data/geo.py`)

### 3.2 Drill-down
- [x] BR → UF por clique
- [x] UF → MUN por clique
- [ ] Modo "detalhe" do município
- [x] Enquadramento ao trocar de nível

Feito em **pydeck**, não em Plotly: o coroplético do Plotly não emite evento
de clique, nem na versão maplibre nem na SVG. Ver `docs/mapa-clique.md`.

### 3.3 Escala de cor
- [x] Quantil k=6 sobre a métrica ativa, com quantis repetidos colapsados —
      sem isso, um recorte com muitos municípios zerados gera classes
      idênticas na legenda
- [x] Legenda horizontal, dentro da figura
- [x] `#F3F4F6` para valor ausente
- [x] Rampa vinda do `disease_pack`, com fallback gerado

### 3.4 Recortes de PE
- [x] Lookup `municipios.csv` → município ↔ macrorregião ↔ região de saúde
- [x] Agregação por macro e por micro, **somando componentes e recalculando a
      taxa** — média de taxas municipais pesaria Recife igual a um município
      de dois mil habitantes
- [x] Toggle Município / Macrorregião / Região de saúde
- [x] Drill macro → micro → município, por clique no mapa

### 3.5 Interação
- [ ] Busca de município (rótulo `"Nome - Região de Saúde"`)
- [ ] Hover box
- [ ] Botão de voltar dentro do mapa

**Pronto quando:** os três níveis e os três recortes navegam sem estado inconsistente.

---

## Semana 4 — Gráficos (24–28/ago)

### 4.1 Configuração visual comum
- [ ] Tooltip escuro `rgba(17,24,39,.96)`, raio 10px, `confine`
- [ ] Grid `left 52 / right 16 / top 26 / bottom 56` com `containLabel`
- [ ] Legenda scroll + duplo-clique para isolar série
- [ ] Paleta do `disease_pack` (barras e linhas separadas)

### 4.2 Evolução temporal
- [ ] Toggle *Meses do ano* / *Todos os anos*
- [ ] Série dupla casos + incidência (específico de TB)
- [ ] Reagir à métrica ativa

### 4.3 Ranking de municípios
- [ ] Top N configurável
- [ ] Alternância UF / MUN
- [ ] Clique na barra navega o mapa

### 4.4 Pirâmide etária
- [ ] População como fundo + casos sobrepostos (estilo IBGE)
- [ ] `ratio` por faixa
- [ ] Alternância entre `tipo` = CASOS / CURA / OBITOS

**Pronto quando:** as três abas renderizam e respondem a ano, escopo e métrica.

---

## Semana 5 — TB específico + composição (31/ago–04/set)

### 5.1 Indicadores de TB
- [ ] Cultura em casos de retratamento (`indicadores_tb_cultura_retratamento`)
- [ ] Contatos identificados vs examinados (`indicadores_tb_contatos`)

### 5.2 Painel de composição
- [ ] Grid de 2 colunas com barras por variável SINAN
- [ ] As 11 variáveis do pack de TB: `TRATAMENTO`, `HIV`, `FORMA`, `CS_RACA`,
      `AGRAVALCOO`, `SITUA_ENCE`, `POP_RUA`, `POP_SAUDE`, `AGRAVDROGAS`, `AGRAVTABACO`
- [ ] Rótulos amigáveis vindos do pack
- [ ] Usar o **código**, nunca o `valor_lbl` — os rótulos vêm reagrupados (óbito e abandono ambos como "Desfavorável")

### 5.3 Filtro de grau de incapacidade
- [ ] Descoberta das opções em runtime
- [ ] Propagação para KPIs, mapa e gráficos

### 5.4 Ajuda contextual
- [ ] Badges "i" com tooltip nos painéis

**Pronto quando:** o inventário de funcionalidades está integralmente marcado.

---

## Semana 6 — Paridade + performance (07–11/set)

### 6.1 Auditoria de paridade
- [ ] Rodar o harness completo em todos os níveis e anos
- [ ] Investigar e classificar cada divergência: bug vs exceção intencional
- [ ] Fechar `excecoes.md`

### 6.2 Performance
- [ ] Profiling: identificar o componente mais lento
- [ ] Tuning de `st.cache_data` (TTL, `max_entries`)
- [ ] Verificar partition pruning nas queries DuckDB
- [ ] Definir e bater um alvo de tempo de resposta por interação

### 6.3 Robustez
- [ ] Tratamento de erro por componente — um gráfico quebrado não derruba a página
- [ ] Estados vazios (ano sem dado, município sem caso)

**Pronto quando:** harness verde e alvo de performance batido.

---

## Semana 7 — Análise livre / Superset (14–18/set)

> Não se parte do zero: o **dashboard-tb-v4** já resolveu esta integração e está
> em produção. Ler `docs/analise-livre.md` e o `PLANO_SEMANA.md` do v4 **antes**
> de começar — os problemas difíceis (cookie `SameSite` no iframe, subcaminho no
> Flask, imagem com `duckdb-engine`) já têm solução registrada.

### 7.1 Views curadas
- [ ] `vw_incidencia` — `incidence` + `incidence_0_14` + `dim_geo`, larga (~325 k linhas)
- [ ] `vw_serie_mensal` — `_cache_ts` (1,2 M)
- [ ] `vw_obitos_sim` — `cache_ts_sim_obitos` + `obitos_sim_faixa` (122 k)
- [ ] `vw_sinan_variaveis` — `sinan_landing` + `sinan_dict` (28,9 M)
- [ ] Aplicar `trim()` no `valor` e o mapa canônico de doença **dentro das views** —
      é aqui que as armadilhas 2, 3 e 5 morrem para todo mundo
- [ ] Script reprodutível de criação (`docker exec ... python -c "import duckdb; ..."`),
      não pela UI do SQL Lab

### 7.2 Conexão no Superset
- [ ] Montar os parquets deste projeto no container como somente leitura (`:ro`)
- [ ] Arquivo DuckDB persistente `/app/superset_home/sinan_pe.duckdb` — nunca `:memory:`
- [ ] Cadastrar a URI `duckdb:////app/superset_home/sinan_pe.duckdb` via
      "Connect this database with a SQLAlchemy URI string"
- [ ] Habilitar `Allow DDL and DML` em *Advanced > SQL Lab*
- [ ] Registrar os 4 datasets e conferir tipos e rótulos das colunas

### 7.3 Aba no dashboard
- [ ] Iframe no mesmo domínio, subcaminho `/cenarios/superset/`
- [ ] Conferir `ENABLE_PROXY_FIX` **e** `APPLICATION_ROOT` — só um dos dois = tela preta
- [ ] nginx: estripar o prefixo no `proxy_pass` e rota `/static/` dedicada
- [ ] Redirecionamento pós-login para o Explore de `vw_incidencia`

### 7.4 Acesso e validação
- [ ] Role Gamma para analistas (leitura e exploração, sem acesso administrativo)
- [ ] Restringir o auto-cadastro por domínio de e-mail institucional — pendência
      herdada do v4, hoje é aberto a qualquer um na rede interna
- [ ] Trocar a senha de admin temporária — pendência herdada do v4
- [ ] Teste com um analista real montando um gráfico do zero

**Pronto quando:** um analista entra pela aba, monta um gráfico sobre
`vw_incidencia` e não esbarra em nenhuma das armadilhas do contrato de dados.

---

## Semana 8 — Polimento + deploy (21–25/set)

### 8.1 Acabamento visual
- [x] Responsivo — remover as alturas fixas de 760px e 520px do original *(feito em 2.1)*
- [x] Tema claro como padrão, escuro como alternativa *(antecipado da semana 8)*
- [ ] Escala tipográfica consistente
- [ ] Aumentar os tooltips (10,5px no original é pequeno demais)

### 8.2 Acessibilidade
- [ ] Navegação por teclado nos cards
- [ ] `aria-label` / `aria-pressed`
- [ ] Contraste
- [ ] `prefers-reduced-motion`

### 8.3 Entrega
- [ ] Deploy
- [ ] README de execução
- [ ] Registrar as divergências metodológicas para a equipe de R

---

## Fora do escopo desta entrega

Dengue, Zika e Hanseníase. Pela arquitetura de *disease pack*, entram depois como
configuração — estimativa de 3–4 dias para as três. Hanseníase é a única com
trabalho real (grau de incapacidade, classificação operacional, casos 0–14);
Dengue e Zika são quase idênticas entre si.

## Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Mapa com drill-down + recortes de PE estourar a semana 3 | Alto | Semana 8 reservada como folga |
| Divergência metodológica não resolvida cedo | Alto | Gate na semana 1, antes de fixar as referências |
| Painel de composição lento (28,9 M linhas em `sinan_landing`) | Médio | Partition pruning + cache; medir na semana 5, não na 6 |
| Biblioteca de mapa escolhida não suportar o drill-down | Médio | Provar com o nível BR logo em 3.1, antes de investir |
| Superset: auto-cadastro aberto e senha de admin temporária (herdado do v4) | Médio | Resolver em 7.4, antes de qualquer uso real continuado |
