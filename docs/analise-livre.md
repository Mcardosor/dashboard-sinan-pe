# Aba de Análise Livre (Apache Superset)

Exploração self-service para analistas, ao lado dos gráficos fixos e curados.
Não substitui o dashboard — atende quem precisa ir além do que já está pronto.

## Não partimos do zero

O projeto **dashboard-tb-v4** já resolveu essa integração e está em produção.
Aqui reaproveitamos a arquitetura inteira; o trabalho é estender, não reconstruir.

O que já está resolvido lá e vale ler antes de começar (`PLANO_SEMANA.md` do v4):

- **Imagem própria do Superset** com `duckdb`, `duckdb-engine` e `psycopg2-binary`
  embutidos. Instalar via `docker exec` não sobrevive à recriação do container.
- **Embutir sem quebrar a sessão.** O cookie do Superset é `SameSite=Lax; Secure`,
  descartado num iframe cross-site. A solução não foi HTTPS em subdomínio novo —
  foi rodar no *mesmo domínio*, no subcaminho `/cenarios/superset/`, atrás do
  nginx compartilhado. Cookie deixa de ser cross-site e o HTTPS é herdado.
- **Subcaminho no Flask** exige `ENABLE_PROXY_FIX` **e** `APPLICATION_ROOT`, que
  fazem coisas diferentes: o primeiro prefixa os links gerados, o segundo alimenta
  o frontend React. Só um dos dois configurado = tela preta. O nginx ainda precisa
  estripar o prefixo antes de repassar, e ter rota `/static/` dedicada.
- Auto-cadastro com role Gamma, tela de login em português, redirecionamento
  pós-login direto para o Explore.

## Decisão: uma instância, vários datasets

Reaproveitar a instância do v4 e adicionar as conexões e views deste projeto.
Uma segunda instância dobraria o custo operacional sem benefício — o Superset
isola por conexão de banco e por permissão de dataset.

## Como o dado chega no Superset

O padrão do v4, aplicado aqui:

1. Os parquets deste projeto são montados **somente leitura** no container
   (`x-superset-volumes`, sufixo `:ro`). Nada é escrito na pasta de dados.
2. Um arquivo DuckDB persistente no volume gravável do Superset
   (`/app/superset_home/sinan_pe.duckdb`) guarda **apenas definições de view** —
   nenhuma cópia de dado. Precisa ser arquivo, não `:memory:`, senão o conteúdo
   se perde entre conexões do pool.
3. URI SQLAlchemy: `duckdb:////app/superset_home/sinan_pe.duckdb`, cadastrada via
   "Connect this database with a SQLAlchemy URI string" — não pelo formulário
   dinâmico, que é voltado a MotherDuck.
4. `Allow DDL and DML` habilitado em *Advanced > SQL Lab* para permitir `CREATE VIEW`.
5. Views criadas por script (`docker exec ... python -c "import duckdb; ..."`),
   não pela UI do SQL Lab — mais confiável e reprodutível.

**Não há disputa de lock com o Streamlit.** Cada consumidor abre a própria conexão
DuckDB sobre os mesmos parquets somente leitura. O contrato compartilhado são os
parquets, não o arquivo `.duckdb`. Atualizações do pipeline aparecem nos dois lados
sem job de sincronização.

## As views são onde as armadilhas morrem

Este é o principal motivo para expor views curadas em vez dos parquets crus.
Um analista no SQL Lab não tem como saber que `valor` vem com espaço à esquerda,
nem que Hanseníase é `HANS` num dataset e `HANSENIASE` em outro. As views aplicam
`trim()` e o mapa canônico de doença de uma vez, para todo mundo.

Ver `docs/contrato-dados.md`, armadilhas 2, 3 e 5.

### Views planejadas

| View | Origem | Linhas | Para quê |
|---|---|---|---|
| `vw_incidencia` | `incidence` + `incidence_0_14` + `dim_geo` | ~325 k | Tabela principal de análise livre. Larga, uma linha por doença/nível/geografia/ano, com casos, óbitos, cura, população, incidência, cortes M/F e faixa 0–14 |
| `vw_serie_mensal` | `_cache_ts` | 1,2 M | Séries temporais mensais |
| `vw_sinan_variaveis` | `sinan_landing` + `sinan_dict` | 28,9 M | Granularidade por variável SINAN, com `trim()` aplicado e rótulo já resolvido |
| `vw_obitos_sim` | `cache_ts_sim_obitos` + `obitos_sim_faixa` | 122 k | Óbitos do SIM — a fonte real de mortalidade, já que `incidence.casos_obitos` é zero para TB |

`vw_incidencia` é a que o analista médio vai usar. É larga, pequena o bastante
para responder instantaneamente e cobre a maioria das perguntas. As outras três
existem para quem precisa descer.

## Integração com o dashboard

A aba carrega o Superset em iframe, no mesmo domínio, subcaminho
`/cenarios/superset/`. O analista não percebe que entrou noutra aplicação.

**Limitação herdada do v4, aceita conscientemente:** não há integração de volta.
O Superset não conhece os filtros de UF, ano e métrica aplicados na sidebar do
dashboard — ele parte do dataset completo. Passar contexto exigiria montar a URL
do Explore com filtros pré-aplicados; fica como melhoria possível, fora do escopo
da primeira entrega.

## Pendências herdadas do v4

Ambas precisam ser resolvidas antes de uso real continuado, e valem para esta
integração também:

- O auto-cadastro é aberto a qualquer um que alcance a rede interna. Restringir por
  domínio de e-mail institucional pede um validador customizado no Flask-AppBuilder.
- A senha de admin em uso é temporária, pensada para a fase de testes.
