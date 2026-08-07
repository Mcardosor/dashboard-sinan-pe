# Perguntas para a equipe de R

Levantadas durante a reconstrução em Python. Ordenadas por quanto travam o
trabalho.

> **Atualização (05/ago).** Com acesso ao banco `cenarios_ai`, que tem o SINAN
> bruto, **três das quatro foram respondidas na fonte** — ver as marcas
> RESPONDIDA abaixo. Sobram uma pergunta e um pedido.

Nenhuma é reclamação: são escolhas que precisam ser confirmadas por quem
conhece o pipeline, e duas delas decidem qual número aparece na tela.

---

## 1. Residência ou notificação? — RESPONDIDA na fonte

Quatro datasets respondem "quantos casos" e não conciliam entre si:

| Fonte | DF em 2024 |
|---|---:|
| `incidence` e `cases_new` | 440 |
| `_cache_ts` e `piramides` | 474 |

Nacionalmente a diferença some (0,0086% no pior ano), mas por UF é grande e
**sistemática**: o DF desvia de 7,7% em 2024 a **36,8% em 2011**, e é a pior
UF nos 15 anos da série. Fora dele, PI, TO e AP chegam a 13,9%.

O padrão — DF ganhando enquanto GO e TO perdem — é o que se espera de **UF de
residência** num dataset e **UF de notificação** no outro. Reforça a hipótese
o fato de a coluna geográfica dos indicadores de TB se chamar
`CO_MUNI_RESIDENCIA`.

**Resposta, medida no `silver.tuberculose`:**

| Datasets | Critério |
|---|---|
| `_cache_ts` e `piramides` | **UF de notificação** |
| `incidence` e `cases_new` | **UF de residência** |

Comparando, para TB/2024 caso novo, a contagem por `estado_notificacao` contra
`estado_residencia` nas 27 UFs, e o desvio `_cache_ts` contra `incidence` nos
parquets: **correlação de 0,998**, com 26 dos 27 sinais concordando. No DF o
bruto dá +7,31% por notificação e os parquets +7,73%; em Tocantins inverte nos
dois (−5,05% e −5,99%).

**O que ainda vale confirmar:** se a escolha de expor as duas bases foi
deliberada, e qual vocês consideram autoritativa. Nossa leitura é que
residência é o critério de vigilância — é onde a pessoa vive e onde a política
age; notificação reflete a rede assistencial, e é por isso que o DF, que
atende o Entorno, aparece inflado.

**Por que trava:** o card de KPI lê de `incidence` e o gráfico de série
temporal lê de `_cache_ts`. Os dois vão aparecer lado a lado mostrando números
diferentes para o mesmo recorte. O dashboard em R tem a mesma inconsistência
hoje — a diferença é que agora ela está medida.

---

## 2. A regra do abandono — CONFIRMADA na fonte, decisão pendente

O `mod_kpis.R` calcula `interrupcao_trat_pct` contando apenas `SITUA_ENCE = 2`
e usando **todos** os encerramentos no denominador, incluindo `5`
(transferência), `7` e `8`.

O indicador do Ministério da Saúde soma `2` (abandono) e `10` (abandono
primário), e exclui os não avaliados do denominador.

Para TB/PE/2024: **11,89% pela regra atual, 14,75% pelo padrão do MS.**

**O que a fonte mostra.** Em `silver.tuberculose`, "Abandono" e "Abandono
primário" são categorias **distintas** — a regra atual, contando só o código 2,
de fato deixa a segunda de fora. E o denominador atual inclui transferência,
não informado, TB-DR e mudança de esquema, que somam **24% dos registros**.

Recalculando em PE/2024 sobre a mesma população (caso novo, por residência):
**10,87% pela regra atual, 14,70% pelo padrão do MS** — a regra atual
subestima o abandono em cerca de um terço.

**O que precisamos saber:** a regra atual é deliberada, por comparabilidade
com alguma série histórica? As duas estão implementadas e testadas do nosso
lado; falta só a decisão.

---

## 3. Um ambiente de R que rode o dashboard

O harness de paridade compara nossos números com referências extraídas dos
parquets por um caminho independente. Isso valida fórmula e pega regressão,
mas **não** substitui conferir contra a tela do original.

Não conseguimos rodar o dashboard aqui: o `renv.lock` fixa R 4.4.0 com 125
pacotes, a pasta `renv/library/` veio vazia, e o `run.ps1` desativa o renv com
o comentário de que os pacotes estão na biblioteca do sistema — que nesta
máquina tem só o R 4.6 sem nenhum deles.

**O que ajudaria, em ordem de preferência:**

1. um `renv.lock` restaurável, ou a lista de pacotes com versões;
2. ou, mais simples, uma planilha com os KPIs de ~30 recortes (doença × nível ×
   ano) tirados da tela do dashboard — resolve o essencial sem ninguém precisar
   montar ambiente.

---

## 4. A pirâmide de tuberculose está vazia — RESPONDIDA: o dado existe

O dataset `piramides` tem a partição `tipo` com CASOS, CURA e OBITOS. Para
tuberculose, **CURA e OBITOS somam zero** em todos os 15 anos e nos três
níveis geográficos. Só a dengue tem OBITOS preenchido; hanseníase e zika
também estão zeradas.

**O dado existe na fonte.** Em `silver.tuberculose`, ano 2024, caso novo:
54.323 curas e 6.668 óbitos, **com sexo e idade preenchidos em mais de 99,9%**
dos registros. Ou seja, não é ausência de dado — algo no pipeline zera essas
duas partições.

**Impacto e o que já fizemos.** Óbitos foram resolvidos localmente: a
pirâmide sai de `obitos_sim_faixa` (6.354 óbitos no Brasil em 2024). As oito
faixas do SIM são um subconjunto das onze de `piramides` e os `faixa_ord`
coincidem, então a reindexação é direta. Mistura SIM com SINAN, e isso está
sinalizado na tela.

**Cura continua sem saída.** Nenhum parquet quebra cura por idade —
`incidence` só tem `cura_M`/`cura_F` e `incidence_0_14` cobre uma faixa. É o
que ainda depende de vocês.

**Pergunta:** o que zera CURA e OBITOS em `piramides`? E a pirâmide de óbitos
do dashboard de vocês sai de onde — do SINAN ou do SIM?

---

## 5. De onde sai o card "Casos novos"? — A PERGUNTA MAIS IMPORTANTE

Comparamos os KPIs contra a tela dos dois painéis de vocês, com o ano fixado
em 2024. O resultado tem um padrão muito nítido.

**Bate no número exato:**

| KPI | Nosso | Painel de vocês |
|---|---|---|
| Taxa de mortalidade (PE) | 4,98 | 5,0 |
| HIV positivo na testagem (PE) | 13,89% | 13,9% |
| — testados no denominador | 8.250 | 8.250 |
| Interrupção de tratamento (PE) | 11,89% | 11,9% |
| — abandono / encerramentos | 1.034 / 8.700 | 1.034 / 8.700 |

Ou seja: tudo que sai do `sinan_landing` e do SIM reproduz a regra de vocês,
incluindo o critério de quem entra em cada denominador.

**Não bate:**

| KPI | Nosso | Painel de vocês | Razão |
|---|---|---|---|
| Casos novos (Brasil) | 85.932 | 113.651 | ×1,32 |
| Casos novos (PE) | 5.246 | 7.438 | ×1,42 |
| Incidência (Brasil) | 40,42 | 53,46 | ×1,32 |
| Curas (Brasil) | 49.114 | 59.565 | ×1,21 |

O fator não é constante entre os recortes, então não é escala nem duplicação
de linhas. E não é escolha de dataset do nosso lado: `incidence`, `cases_new`
e `_cache_ts` concordam entre si em torno de 85,9 mil para o Brasil — nenhum
chega perto de 113 mil.

**A pergunta:** de qual tabela sai o card "Casos novos"? Especificamente, ele
inclui **recidiva** e **reingresso após abandono**, ou conta só caso novo?

Perguntamos porque os parquets que recebemos têm apenas três tipos de entrada
em `TRATAMENTO` — Caso Novo, Pós-óbito e Não Sabe. Recidiva e reingresso não
aparecem. Se o painel de vocês os inclui, o extrato que nos passaram está
filtrado e precisamos do não filtrado.

Vale registrar que a nossa incidência nacional, 40,42 por 100 mil, é a ordem
de grandeza publicada para tuberculose no Brasil; 53,46 fica acima. Não é
prova de nada — é o motivo de perguntarmos antes de mudar o nosso lado.

---

## Achados que não pedem resposta, só aviso

São coisas que corrigimos do nosso lado, mas que provavelmente também afetam
o dashboard em R.

**`incidence.casos_obitos` é zero para tuberculose** em todos os anos. Quem
calcular mortalidade ou letalidade a partir desse campo obtém zero. Assumimos
que a fonte correta é `cache_ts_sim_obitos` (SIM), que é o que o `mod_kpis.R`
também faz — só confirmando o entendimento.

**O `municipios.csv` tem erro de ponto flutuante no código do município.**
Oito dos 185 estão gravados como decimal com resíduo: São Vicente Férrer é
`2613799.9999999995`, Tabira é `2614599.9999999995`. Truncar em vez de
arredondar produz o código errado, e em dois casos isso faz o município sumir
da agregação por região sem erro nenhum — a soma das macrorregiões dava 5.236
contra 5.246 do estado. Vale checar se o pipeline de vocês arredonda.

**Os arquivos da faixa de identificação não vieram na entrega.**
`Bandeira_de_Pernambuco.jpeg` e `cenarios_logo_full.jpeg` são procurados pelo
`app_shell.R` dois níveis acima da pasta de dados; não achando, ele renderiza
a faixa sem imagem, em silêncio. Repusemos o logotipo. A bandeira ficou de
fora de propósito: nossos dados são nacionais e, ao lado de um mapa do
Brasil, ela lia como recorte geográfico em vez de emissor.
