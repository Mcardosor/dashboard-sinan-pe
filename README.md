# dashboard-sinan-pe

Dashboard de vigilância epidemiológica SINAN em Streamlit/Python. Reconstrução
de um dashboard Shiny/R desenvolvido por outra equipe — mesmo escopo funcional,
com ganhos de performance e de acabamento visual.

**Alcance:** os dados e a navegação são **nacionais** — 27 UFs, 5.571
municípios. Sobre isso há uma camada de **recortes administrativos de saúde**
(macrorregião e região de saúde) que hoje só Pernambuco tem, porque só para PE
existem a malha e o lookup. Essa camada é genérica: acrescentar outro estado é
registrar uma entrada em `src/data/recortes.py` e soltar os arquivos, sem
tocar em código.

**Status:** em construção. Primeira entrega: Tuberculose.

---

## Objetivo

Três metas, nesta ordem de prioridade:

1. **Paridade funcional** com o dashboard em R — mesmos KPIs, mesmos gráficos,
   mesma navegação. Divergências numéricas são permitidas apenas quando
   intencionais e registradas em `tests/paridade/excecoes.md`.
2. **Mais rápido.** O original faz round-trip ao servidor R a cada interação e
   simplifica geometria a cada redesenho do mapa. Aqui: DuckDB sobre parquet
   pré-agregado, geometria simplificada uma vez em disco, cache do Streamlit.
3. **Mais bonito.** Preserva o que o original acertou (cor por métrica, cards com
   acento lateral, escala por quantil) e corrige o que ficou fraco (alturas
   fixas, ausência de tema escuro, tipografia sem escala).

Além da paridade, o painel já faz coisas que o original em R não faz —
indicadores do programa (contatos examinados, cultura em retratamento), a
pirâmide de óbitos, 24 variáveis de composição contra 9 do painel de PE, e o
aviso de ano incompleto. Todas conferidas contra a tela deles.

A aba de **Análise Livre** com Apache Superset está **adiada, e pode não
entrar**: virou a última prioridade. O plano segue registrado em
**[docs/analise-livre.md](docs/analise-livre.md)** para quem retomar.

## Escopo

| Doença | Situação |
|---|---|
| Tuberculose | Primeira entrega — valida o core completo |
| Hanseníase | Depois. Único caso com trabalho real (grau de incapacidade, classificação operacional, casos 0–14) |
| Dengue | Depois. Entra como configuração |
| Zika | Depois. Entra como configuração |

A arquitetura segue o padrão de *disease pack* do projeto original: o core é
único e cada doença é um arquivo de configuração (cores, rótulos, layout de KPI,
variáveis de composição).

## Stack

- **Dados:** DuckDB sobre parquet particionado (Hive), leitura direta sem ETL
- **App:** Streamlit
- **Gráficos:** Altair — `st.altair_chart` tem evento de clique nativo e já vem
  com o Streamlit
- **Mapa:** pydeck (deck.gl). O coroplético do Plotly não dispara evento de
  clique, verificado com clique real; ver [docs/mapa-clique.md](docs/mapa-clique.md)
- **Análise livre:** Apache Superset sobre DuckDB — planejado, adiado

## Dados

Não versionados. São ~888 MB em 2.814 arquivos parquet, originados do projeto em
R da equipe parceira. O layout esperado, o significado de cada dataset e as
armadilhas conhecidas estão em **[docs/contrato-dados.md](docs/contrato-dados.md)**.

Coloque os dados em `data/parquet/dashboard/` na raiz do projeto, ou aponte a
variável de ambiente `SINAN_DATA_DIR` para onde eles estiverem.

Em `data/support/` ficam os arquivos de apoio de PE — os shapefiles de
macrorregião e região de saúde e o `municipios.csv`. Também não são
versionados, e são a única fonte dos recortes de saúde.

O logotipo da faixa de identificação fica em **`assets/`** e **é
versionado**: é identidade visual, não dado, não muda quando o SINAN atualiza.
Sem ele a faixa mostra só o título e a barra lateral avisa o que falta.

A bandeira de Pernambuco que o original exibe ao lado do título foi removida:
os dados aqui são nacionais e, ao lado de um mapa do Brasil, ela lia como
recorte geográfico em vez de emissor.

## Como rodar

```bash
git clone https://github.com/Mcardosor/dashboard-sinan-pe.git
cd dashboard-sinan-pe

python -m venv .venv
.venv\Scriptsctivate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py
```

**Os dados não vêm no clone** — são 892 MB e o `.gitignore` os exclui de
propósito. Sem eles a aplicação não sobe. Duas formas de resolver:

1. Copiar a pasta `data/` inteira de uma máquina que já a tenha.
2. Usar o pacote reduzido de 209 MB, que é o que a aplicação de fato lê:

   ```bash
   python -m scripts.preparar_publicacao --destino /caminho/do/pacote
   ```

   Rodado na máquina de origem, ele monta a árvore pronta para copiar. A
   diferença para os 892 MB é quase toda `_geo_cache`, GeoJSON bruto do
   pipeline que já convertemos para GeoParquet.

O layout esperado é `data/parquet/dashboard/`, `data/geo/` e `data/support/`.
Para manter os dados fora do projeto, aponte `SINAN_DATA_DIR` para a pasta que
contém esses três diretórios.

Se `data/geo/` não existir mas o `_geo_cache` sim, gere a geometria com
`python -m scripts.preparar_geometria` — leva cerca de 40 s para as 27 UFs.

### Testes

```bash
pytest
```

Rodam **sem os dados**: os módulos que dependem deles são ignorados e o
cabeçalho avisa. Num clone limpo passam 101 dos 552 — tema, navegação e
resiliência. Com os dados no lugar, os 552.

### Banco (opcional)

`docs/banco-cenarios.md` descreve o acesso somente-leitura ao SINAN bruto,
usado para investigação e não pela aplicação. Precisa de VPN e de um `.env`
com base em `.env.exemplo`.

## Documentação

- **[docs/cronograma.md](docs/cronograma.md)** — plano de 8 semanas com marcos e riscos
- **[docs/inventario-funcionalidades.md](docs/inventario-funcionalidades.md)** — checklist de paridade com o original
- **[docs/contrato-dados.md](docs/contrato-dados.md)** — datasets, esquemas, fórmulas dos KPIs e armadilhas
- **[docs/analise-livre.md](docs/analise-livre.md)** — integração com Apache Superset
- **[docs/perguntas-equipe-r.md](docs/perguntas-equipe-r.md)** — o que depende da equipe parceira
- **[docs/banco-cenarios.md](docs/banco-cenarios.md)** — o SINAN bruto, para investigação
- **[docs/deploy.md](docs/deploy.md)** — publicação: moldes de systemd e nginx, e o pacote de 209 MB

## Estrutura

```
assets/         logotipo da faixa de identificação (versionado)
src/
  data/         camada DuckDB: conexão, readers por dataset, KPIs
  theme/        tokens de design, gerador de rampa de cor, componentes visuais
  components/   KPI cards, mapa, gráficos
  pages/        telas do Streamlit
tests/
  paridade/     harness que compara os números contra o dashboard em R
scripts/        pré-processamento (simplificação de geometria, etc.)
docs/           documentação do projeto
```
