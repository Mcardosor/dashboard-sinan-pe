# Contrato de dados

Levantado a partir do projeto original em R, validado com queries DuckDB direto
nos parquets. Todos os números abaixo foram conferidos, não inferidos.

## Origem

`data/parquet/dashboard/` — 888 MB, 2.814 arquivos parquet, particionamento Hive.
Cobertura 2010–2025 (Zika a partir de 2016; 2025 parcial). Nacional: BR, 27 UFs,
5.570 municípios.

Os arquivos de apoio de Pernambuco (`municipios.csv`, `PE MODIF.*`,
`PEMacSAUD MODIF.*`, `PERGSAUDE MODIF.*`) **não** ficam em `data/parquet/` no
projeto original — vivem seis níveis acima na árvore de diretórios. São a única
fonte de macrorregião e região de saúde. Copie para `data/support/`.

## Datasets

| Dataset | Linhas | Partições | Conteúdo |
|---|---|---|---|
| `incidence` | 325 k | `doenca/nivel/ano` | KPIs anuais: casos, óbitos, cura, população, incidência — com corte M/F |
| `incidence_0_14` | 325 k | `doenca/nivel/ano` | Mesmas métricas para a faixa 0–14 anos |
| `_cache_ts` | 1,2 M | `nivel/doenca/ano` | Série mensal: `mes`, `casos`, `casos_obitos`, `casos_cura`, `incid_100k` |
| `piramides` | 13,2 M | `nivel/tipo/doenca/ano` | Pirâmide etária. `tipo` ∈ CASOS, CURA, OBITOS. Campos `valor`, `pop`, `ratio` |
| `sinan_landing` | 28,9 M | `doenca/nivel/ano` | Variáveis SINAN em formato longo: `variavel`, `valor`, `valor_lbl`, `n` |
| `sinan_dict` | 4,5 k | — | Dicionário de código → rótulo |
| `cache_ts_sim_obitos` | 65 k | `doenca/nivel/ano` | Óbitos do SIM, mensais |
| `obitos_sim_faixa` | 57 k | `doenca/nivel/ano` | Óbitos do SIM por sexo e faixa etária |
| `cases_new` | 205 k | `doenca/ano` | Casos novos por `cod_mun6` |
| `indicadores_tb_contatos` | 54 k | — | TB: contatos identificados vs examinados |
| `indicadores_tb_cultura_retratamento` | 27 k | — | TB: cultura em casos de retratamento |
| `_geo_cache/` | 652 MB | `municipios/uf=XX/` | GeoJSON por UF + `municipios_centroids.parquet` |

## Fórmulas dos KPIs

```
incid_100k    = casos / pop * 100000
mortalidade   = obitos / pop * 100000
letalidade    = obitos / casos * 100
taxa_det_0_14 = casos_0_14 / pop_0_14 * 100000
hiv_pos_pct   = positivo / (positivo + negativo) * 100
interrupcao   = SITUA_ENCE = 2 / total de encerramentos * 100
```

`hiv_pos_pct` exclui "não realizado" e "em andamento" do denominador.
Sobre `interrupcao`, ver a armadilha 4.

## Armadilhas

### 1. `casos_obitos` é zero para tuberculose

Em `incidence`, todos os anos de 2010 a 2025. Calcular mortalidade ou letalidade
a partir desse campo dá zero. Os óbitos reais estão em `cache_ts_sim_obitos`
(73.409 óbitos por TB entre 2010 e 2024). São fontes distintas — SINAN vs SIM — e
o merge é responsabilidade da aplicação.

### 2. O código da doença muda entre datasets

| Dataset | Hanseníase | Dengue |
|---|---|---|
| `incidence`, `_cache_ts`, `piramides`, `cases_new` | `HANSENIASE` | `DENG` |
| `sinan_landing` | **`HANS`** | `DENG` |
| `cache_ts_sim_obitos`, `obitos_sim_faixa` | `HANSENIASE` | **`DENGUE`** |

Os dois datasets do SIM ainda trazem `CHIKUNGUNYA`, ausente em todos os outros.
Qualquer join precisa passar pelo mapa canônico em `src/data/`.

### 3. `valor` vem com espaço à esquerda

Em `sinan_landing`, os códigos têm comprimento 2 com espaço à esquerda —
verificado em hexadecimal: `" 1"` = `0x2031`, `" 2"` = `0x2032`. A exceção é
`"10"`, que não tem espaço. Sem `trim()`, todo filtro por código retorna zero
silenciosamente. O `sinan_dict` agrava: registra `" 3"` e `"03"` como entradas
distintas.

### 4. O indicador de interrupção diverge do padrão do MS

O projeto em R conta apenas `SITUA_ENCE = 2` (abandono) e usa **todos** os
encerramentos no denominador, incluindo `5` (transferência), `7` e `8`.

O padrão do Ministério da Saúde soma `2` + `10` (abandono primário) e exclui os
não avaliados do denominador.

Para TB/PE/2024: **11,89% pela regra do R, 14,75% pelo padrão do MS.**

Não é bug de programação, é escolha metodológica — mas precisa ser decidida antes
de fixar as referências de paridade. Ver `tests/paridade/excecoes.md`.

### 5. `SITUA_ENCE` já vem reagrupado

Os rótulos foram achatados em Favorável / Desfavorável / Não avaliado. Os códigos
`2` (abandono), `3` e `4` (óbitos) e `9` (falência) aparecem todos como
"Desfavorável". Para separar óbito de abandono, use o **código**, nunca o
`valor_lbl`.
