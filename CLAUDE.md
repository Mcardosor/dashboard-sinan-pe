# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Painel de vigilância epidemiológica do SINAN, em Streamlit. Reconstrução de um
dashboard Shiny/R feito por outra equipe — mesmo escopo funcional, com ganhos
de performance e acabamento. Dados nacionais (27 UFs, 5.571 municípios), com
recortes de saúde que hoje só Pernambuco tem.

Documentação em português. Código, commits e comentários também.

## Comandos

```bash
streamlit run app.py                      # aplicação (porta 8501)
pytest                                    # suíte inteira (~630 testes, ~13 s)
pytest tests/test_mapa.py -q              # um módulo
pytest tests/test_mapa.py::test_x -q      # um teste
pytest tests/paridade -q                  # só o harness de paridade
pytest -rs                                # ver o motivo de cada skip

python -m scripts.preparar_geometria      # regera data/geo/ (~40 s, 27 UFs)
python -m scripts.preparar_publicacao --conferir          # mede o pacote
python -m scripts.preparar_publicacao --destino <pasta>   # monta o pacote
python -m scripts.medir_performance       # linha de base dos leitores
```

Não há linter nem formatter configurados no projeto.

**Testes sem os dados:** os parquets não são versionados (892 MB). Sem eles,
`tests/conftest.py` ignora os módulos que dependem de dado e a suíte roda com
101 testes em vez de ~630. O cabeçalho do pytest mostra `dados: presentes` ou
`AUSENTES` com o caminho — se disser AUSENTES, confira `SINAN_DATA_DIR`.

## Arquitetura

**Fluxo:** `app.py` (única página) → `src/estado.py` (máquina de estados) →
`src/data/*` (leitura) → `src/mapa.py` e `src/graficos.py` (visual).

- **`src/data/escopo.py`** — `Escopo` é o recorte que atravessa tudo: doença,
  ano, nível (BR/UF/MUN), UF, município. Todo leitor recebe um.
- **`src/data/conexao.py`** — `caminho()` constrói o glob podando partições.
  `PARTICOES` declara a ordem de cada dataset, e a ordem **difere entre eles**
  (`incidence` é doenca/nivel/ano; `_cache_ts` é nivel/doenca/ano).
- **`src/data/leitura.py`** — um leitor por dataset, todos devolvendo dado já
  normalizado. É o arquivo mais denso do projeto.
- **`src/doencas/`** — *disease pack*: o core é único e cada doença é um
  arquivo de configuração (cores, rótulos, layout de KPI, variáveis de
  composição, descrições). Só tuberculose existe hoje.
- **`src/resiliencia.py`** — `painel()` contém a falha de um painel no próprio
  painel. No Streamlit, exceção no corpo do script troca a página inteira pelo
  traceback.

### Regras que falham em silêncio

Violá-las não dá erro — dá número errado ou coluna faltando. Cada uma custou
uma investigação; a íntegra está em `docs/contrato-dados.md`.

1. **Nunca dar glob na raiz de um dataset.** Arquivos de `nivel=BR` não têm a
   coluna `uf`; o DuckDB une pelo esquema do primeiro arquivo e some com
   colunas dos demais. Use sempre `conexao.caminho(dataset, **particoes)`.
2. **`sinan_landing` tem linha `sexo='TOTAL'`** que já é a soma de M, F e I.
   Somar o dataset inteiro dobra a contagem. Filtre `sexo = 'TOTAL'`.
3. **Município tem dois comprimentos.** `incidence` usa `cod_mun7`, os demais
   `geo_id` de 6 dígitos. A chave canônica é 6 — aplique `mun6()` em todo
   filtro geográfico. Cruzar errado não dá erro, devolve vazio.
4. **O código da doença muda entre datasets.** Use `config.cod_agregado()`,
   `cod_landing()` ou `cod_sim()` conforme a fonte, nunca a string crua.
5. **`valor` do SINAN vem com espaço à esquerda** (`" 2"`). Filtre por código
   com `trim` aplicado, e **nunca por `valor_lbl`** — os rótulos vêm
   reagrupados (óbito e abandono ambos como "Desfavorável").
6. **`casos_obitos` é zero para tuberculose** em `incidence`. Mortalidade sai
   de `obitos_sim` (SIM), não do SINAN.
7. **Capture `Exception`, nunca `BaseException`.** `st.rerun()` levanta
   `RerunException`, que herda de `BaseException` justamente para atravessar
   `except Exception`. Ampliar a captura mata a navegação por clique sem erro
   nenhum aparecer.
8. **A suíte não importa o `app.py`.** Importar dispararia o script inteiro.
   `tests/test_app.py` faz checagem estática com `ast` — foi assim que se
   pegou uma constante de cache definida **depois** do decorador que a usava,
   com o app quebrando na importação e 629 testes verdes.
9. **A pirâmide de CURA está zerada** para tuberculose e hanseníase em todos
   os anos — falha do pipeline da equipe parceira, não ausência de dado.
   Óbitos saem de `obitos_sim_faixa`; cura não tem fonte local.
10. **Os indicadores de TB vêm de outra extração**, com cobertura de ano
   própria. Não compare com os KPIs num ano que ainda não fechou.

### Paridade

`tests/paridade/` compara com o dashboard em R, cujos valores foram lidos da
tela e gravados em `referencia_r.json`. **Toda divergência precisa estar em
`tests/paridade/excecoes.md`** — o que não estiver listado e divergir é bug, e
um teste confere que o registro acompanhe o código.

Três KPIs reproduzem o R no número exato; uma divergência é intencional (nós
corrigimos a contagem dobrada e eles não); uma segue aberta e depende de
resposta da equipe parceira. Ver `docs/perguntas-equipe-r.md`.

### Mapa

pydeck, não Plotly — o coroplético do Plotly não dispara evento de clique,
verificado com clique real. Duas coisas no `src/mapa.py` parecem gambiarra e
não são:

- `_compactar` troca o `to_json` da instância. O `pydeck.serialize` usa
  `indent=2` e o Streamlit envia isso ao navegador; a indentação era 74% do
  payload.
- O zoom pela roda do mouse é bloqueado por um ouvinte de `wheel` em
  `componentes.script_travar_zoom`, injetado via `components.v1.html`.
  Declarar `controller: false` no spec não funciona: o `DeckGlJsonChart`
  renderiza `<DeckGL controller={true}>` fixo.

## Dados

Não versionados. Esperados em `data/parquet/dashboard/`, `data/geo/` e
`data/support/`, ou aponte `SINAN_DATA_DIR` para a pasta que os contém.

`data/geo/` é gerado por `scripts.preparar_geometria` a partir do
`_geo_cache`, e a simplificação é **topológica** — `shapely.simplify` por
polígono rompe o mosaico entre vizinhos.

O `.gitignore` usa `/data/` com barra inicial de propósito: sem ela o padrão
casava com `src/data/` e engoliu a camada de dados inteira por dias.
