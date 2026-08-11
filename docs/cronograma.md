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
- [x] Copiar `data/parquet/dashboard/` (888 MB, 2.814 arquivos) para o destino definitivo
- [x] Copiar os arquivos de apoio de PE para `data/support/` — hoje eles vivem fora de `data/`, 6 níveis acima, e são a única fonte de macro/microrregião:
      `municipios.csv`, `PE MODIF.*`, `PEMacSAUD MODIF.*`, `PERGSAUDE MODIF.*`
- [x] Criar venv e `requirements.txt`
- [x] Validar leitura dos 11 datasets e conferir contagem de linhas contra `docs/contrato-dados.md`

### 1.2 Camada de dados (`src/data/`)
- [x] Conexão DuckDB única em `st.cache_resource`
- [x] Mapa canônico de doenças — resolve `DENG`/`DENGUE`, `HANS`/`HANSENIASE` entre datasets
- [x] Normalizações: `trim()` no campo `valor`, padding de `cod_mun6`↔`cod_mun7`, sigla de UF
- [x] Readers por dataset: `incidence`, `incidence_0_14`, `_cache_ts`, `piramides`,
      `sinan_landing`, `sinan_dict`, `cache_ts_sim_obitos`, `obitos_sim_faixa`,
      `cases_new`, `indicadores_tb_contatos`, `indicadores_tb_cultura_retratamento`
- [x] Funções de KPI: `incid`, `mortalidade`, `letalidade`, `taxa_det_0_14`,
      `hiv_pos_pct`, `interrupcao_trat_pct`
- [x] Ligar óbitos de TB ao SIM (`cache_ts_sim_obitos`) — `incidence.casos_obitos` é zero para TB em todos os anos

### 1.3 Harness de paridade (`tests/paridade/`)
- [ ] **Gate: decidir a metodologia do abandono** — Regra do R = 11,89% ·
      padrão MS = 14,75% (TB/PE/2024). **Bloqueado na equipe de R.** As duas
      regras estão implementadas e testadas; falta a decisão de qual vale.
- [x] Extrair valores de referência do dashboard em R **rodando** — feito
      em 2026-08-07, dos dois painéis, em `tests/paridade/referencia_r.json`
- [x] Suite pytest comparando os números com tolerância declarada
- [x] `excecoes.md` — divergências intencionais, com justificativa

### 1.4 Sistema visual (`src/theme/`)
- [x] `tokens.py` — cores, raios, sombras, tipografia, breakpoints
- [x] Gerador de rampa a partir da cor base (mix com branco 35/55/72%, com preto 18/34/52%)
- [x] `kpi_card()` — acento lateral, `--kpi-accent` inline, hover, foco, teclado
- [x] `disease_pack` da Tuberculose

**Pronto quando:** o harness roda verde contra as referências e `kpi_card()` renderiza isolado.

Fechada, com duas pendências que não dependem de código — ambas na equipe de R.
Os itens acima foram conferidos contra o código em 03/ago, não marcados de
memória.

---

## Semana 2 — Esqueleto + KPIs (10–14/ago)

### 2.1 Shell da aplicação
- [x] Layout: sidebar 380px + faixa de intro + linha de KPIs + linha principal + faixa de composição
- [x] CSS base injetado uma única vez
- [x] Faixa de intro (título · logo) — **completa**. O logotipo não veio na
      entrega do projeto em R e foi reposto depois; a degradação graciosa
      continua valendo para quem clonar sem ele. A bandeira de PE do original
      foi removida: os dados são nacionais e ela lia como recorte geográfico.

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
- [x] Biblioteca: **pydeck**. A escolha começou no Plotly, por ele ter evento
      de clique nativo na assinatura — mas ter e disparar são coisas
      diferentes, e o coroplético do Plotly não dispara. O `GeoJsonLayer` do
      deck.gl faz *picking* por GPU e resolveu, sem dependência nova.
      Ver `docs/mapa-clique.md`
- [x] Carregar geometria pré-simplificada (`src/data/geo.py`)

### 3.2 Drill-down
- [x] BR → UF por clique
- [x] UF → MUN por clique
- [x] Modo "detalhe" do município — clicar de novo no município já selecionado
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
- [x] Busca de município, com a região de saúde no rótulo em PE
- [x] Hover box — tooltip do pydeck, com nome e valor formatado
- [x] Botão de voltar dentro do mapa

**Pronto quando:** os três níveis e os três recortes navegam sem estado inconsistente.

Verificado em `tests/test_navegacao_mapa.py`, que percorre todas as
combinações de nível, recorte e métrica pintável, e três percursos completos
do Brasil até o detalhe — conferindo que cada passo tem geometria e valores, e
que o `voltar` devolve ao ponto de partida sem estado preso.

---

## Semana 4 — Gráficos (24–28/ago)

### 4.1 Configuração visual comum
- [x] Biblioteca: **Altair**, não ECharts. `st.altair_chart` tem evento de
      clique nativo — verificado com clique real antes de escolher, não só
      pela assinatura — e vem com o Streamlit, sem componente de terceiros.
      O ranking (4.3) precisa desse evento
- [x] `tema()` aplicado a todo gráfico, para a linguagem não divergir entre
      eles como divergia no original
- [x] Cor herdada de `currentColor`, mesmo mecanismo dos cards
- [x] Estado vazio com recado, no lugar de painel em branco

### 4.2 Evolução temporal
- [x] Toggle *Meses do ano* / *Todos os anos*
- [x] Série dupla casos + incidência (específico de TB) — eixos independentes,
      cada um na cor da sua série. Num eixo só, a linha da taxa vira uma reta
      colada no zero: casos estão em milhares e incidência em dezenas
- [x] Reagir à métrica ativa, com as taxas recalculadas mês a mês. Repetir a
      taxa anual nos meses esconderia a sazonalidade, que é o que o gráfico
      existe para mostrar

O toggle troca de **fonte**, não só de agregação: a série mensal vem de
`_cache_ts`, por notificação, e a anual de `incidence`, por residência — que é
o critério dos KPIs. Enquanto não houver série mensal por residência, o modo
mensal avisa que os totais não fecham, em vez de deixar o usuário descobrir
somando as barras.

### 4.3 Ranking de municípios
- [x] Top N configurável (5 a 30)
- [x] Alternância UF / MUN — segue o nível do escopo, como o mapa: no Brasil
      ranqueia UFs, numa UF ranqueia os municípios dela
- [x] Clique na barra navega o mapa

Lê da **mesma fonte do mapa**, com teste que confere valor a valor. Ler de
lugares diferentes é como o card e a série temporal, que divergem justamente
por isso.

### 4.4 Pirâmide etária
- [x] Pirâmide por sexo e faixa, escala única e domínio simétrico
- [x] Taxa por 100 mil habitantes, no lugar da população de fundo
- [x] CASOS (`piramides`) e OBITOS (`obitos_sim_faixa`, do SIM)
- [ ] CURA — sem fonte local, depende do banco

**Pronto quando:** os tipos disponíveis renderizam e respondem a ano e escopo.
Fechado com dois de três: cura não tem quebra por idade em nenhum parquet.

---

## Semana 5 — TB específico + composição (31/ago–04/set)

### 5.1 Indicadores de TB
- [x] Cultura em casos de retratamento (`indicadores_tb_cultura_retratamento`)
- [x] Contatos identificados vs examinados (`indicadores_tb_contatos`)
- [x] **Ganho sobre o original:** nenhum dos dois painéis em R exibe estes
      indicadores — conferido na tela de `TB_BR` e de `TB_PE`. O dado veio nos
      parquets e estava sem uso

### 5.2 Painel de composição — **feito, adiantado da semana 5**
- [x] Seletor agrupado + barras horizontais por variável do SINAN
- [x] 24 variáveis, contra 9 do painel de PE — o dado já estava em disco
- [x] Rótulos amigáveis vindos do pack
- [x] Usar o **código**, nunca o `valor_lbl` — os rótulos vêm reagrupados (óbito e abandono ambos como "Desfavorável")
- [x] Supressão do percentual em base pequena, na camada de dados

### 5.3 Filtro de grau de incapacidade
- [ ] Descoberta das opções em runtime
- [ ] Propagação para KPIs, mapa e gráficos

### 5.4 Ajuda contextual — **feito, antecipado**
- [x] Tooltips nos 6 KPIs e nos controles ambíguos. Explicam sobretudo o
      **denominador**: "Interrupção de tratamento (%)" não dizia percentual
      sobre o quê, e a resposta muda o número em quase 4 pontos

**Pronto quando:** o inventário de funcionalidades está integralmente marcado.

---

## Semana 6 — Paridade + performance (07–11/set)

### 6.1 Auditoria de paridade
- [x] Rodar o harness completo em todos os níveis e anos — 57 checagens, 16 anos, 3 níveis
- [x] Investigar e classificar cada divergência: bug vs exceção intencional
- [x] Fechar `excecoes.md` — reorganizado em idêntico / intencional / aberto, com teste prendendo o registro ao código

### 6.2 Performance
- [x] Profiling: o mais lento era montar o mapa (112 ms em MG), dos quais 75 ms eram converter a malha
- [x] Tuning de `st.cache_data` — TTL de 10 min para 24 h (dado imutável entre publicações) e teto para o cache de geometria, que estava sem limite
- [ ] Verificar partition pruning nas queries DuckDB
- [ ] Definir e bater um alvo de tempo de resposta por interação — **depende de medir pela rede**, ver docs/performance.md

### 6.3 Robustez — **feito, antecipado**
- [x] Tratamento de erro por componente — `src/resiliencia.py`. Verificado
      injetando falha na pirâmide: ranking e composição seguiram de pé
- [x] Estados vazios (ano sem SIM, município sem caso), mais o aviso de ano
      incompleto — 2025 mostrava incidência 0,83 contra 40,42 sem dizer que
      o ano estava pela metade

**Pronto quando:** harness verde e alvo de performance batido.

---

## Semana 7 — Análise livre / Superset (14–18/set) — **ADIADA**

> Decidido em 08/ago/2026: passa a ser a última prioridade, e pode não entrar.
> O que sustentava o bloco era ser a única coisa além do original; isso deixou
> de valer — o painel já entrega indicadores do programa, pirâmide de óbitos,
> 24 variáveis de composição e aviso de ano incompleto, nenhum deles presente
> nos painéis em R.
>
> O plano fica registrado abaixo e em `docs/analise-livre.md`. Nada foi
> começado, então adiar não deixa ponta solta.

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
- [x] Escala tipográfica — três degraus, todos em uso. Havia seis, dos quais dois nunca foram usados; os componentes contornavam com `font-size` fixo (11px, 12px, 28px)
- [x] Tooltips em 12px — registrado como divergência visual em `excecoes.md`

### 8.2 Acessibilidade
- [x] Navegação por teclado nos cards — `<button>` nativo, e não um `div` com `role="button"` como no original
- [x] `aria-pressed` e `aria-label` nos cards — remendo no DOM, porque o botão é do Streamlit. Reaplica a cada rerun
- [x] Contraste — cinco métricas ficavam abaixo de 3:1 no tema escuro, `incid` entre elas com 2,6. O acento passa a se misturar a `currentColor`, o que segue o tema do Streamlit e não o do sistema
- [x] `prefers-reduced-motion`

### 8.3 Entrega
- [ ] Deploy
- [x] README de execução
- [x] Registrar as divergências metodológicas — `excecoes.md` e `perguntas-equipe-r.md`

---

## Aberto — decidido em 08/ago/2026

### Separar leitura de controle nos KPIs — **FEITO**

**Decisão:** o card de KPI volta a ser **só leitura**, e a métrica ativa passa
a ter um controle explícito — segmentado ou rádio horizontal, acima do mapa,
ao lado do cabeçalho "Mapa — unidades da federação".

**Por quê.** O card clicável veio do painel em R e nunca foi examinado. Ele
custou quatro rodadas de conserto: o botão transparente por cima, o rótulo
vazando sobre o título, a área de clique saindo com o dobro do card, e
`aria-pressed`/`aria-label` remendados no DOM. Tudo isso para uma interação
que `st.radio` entrega nativamente, com teclado e leitor de tela incluídos.

E o defeito de fundo não era nenhum desses: **o card não avisa que é
clicável**. Parece um indicador porque é um indicador. A única pista é o
realce no hover, que não existe em toque. Pagamos caro por uma interação que
boa parte dos usuários nunca encontra.

**Resolve de graça** o problema dos dois KPIs sem mapa (abaixo): um controle
explícito lista só as métricas que funcionam, e não há card morto para clicar.

**O que sai:**
- `componentes.kpi_clicavel` e o bloco CSS de `[class*="st-key-kpi-"]`
- `componentes.script_estado_kpis` — `aria-pressed` passa a ser nativo
- os testes que existem só para vigiar o botão invisível

**O que fica:** `kpi_card`, sem `aria-hidden`, porque passa a ser o conteúdo
de verdade e não um enfeite atrás de um botão.

Registrar em `excecoes.md` como divergência visual intencional.

## Aberto — encontrado em 08/ago/2026

### Mapa e ranking não cobrem dois dos seis KPIs

`interrupcao_trat_pct` e `hiv_pos_pct` devolvem zero linhas em
`valores_por_geografia` e em `ranking`. Clicar nesses cards leva ao estado
vazio "ainda não é pintável no mapa". Confirmado no Brasil, 2024: os outros
quatro devolvem 27 UFs, esses dois devolvem nada.

**Causa.** Os quatro que funcionam saem de coluna direta do `incidence`, que
já vem por geografia (`_COLUNA_DIRETA` tem `casos`, `cura`, `incid`, `pop`;
`mortalidade` deriva de óbitos). Os dois que faltam são calculados a partir
do `sinan_landing`, e `variavel_sinan` filtra **uma** geografia por vez —
serve para o card, não para pintar 27 UFs de uma vez.

**Correção.** Um leitor que agrupe em vez de filtrar: `sinan_landing` tem
`uf` e `geo_id`, então dá para `GROUP BY` a chave geográfica aplicando as
mesmas regras dos KPIs — positivos sobre positivos mais negativos para o HIV,
código 2 sobre todos os encerramentos para a interrupção. Atenção a
`sexo = 'TOTAL'` (armadilha 11) e ao critério por **código** e nunca por
rótulo (armadilha 5).

Cuidado ao ligar: no nível de município a base fica pequena, e o mesmo limiar
de `MINIMO_PARA_PERCENTUAL` que protege o painel de composição deveria valer
aqui — um município com dois encerramentos não pode virar uma cor no mapa.

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
