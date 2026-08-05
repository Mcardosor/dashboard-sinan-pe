# Perguntas para a equipe de R

Levantadas durante a reconstrução em Python, todas verificadas com query nos
próprios parquets. Ordenadas por quanto travam o trabalho.

Nenhuma é reclamação: são escolhas que precisam ser confirmadas por quem
conhece o pipeline, e duas delas decidem qual número aparece na tela.

---

## 1. Residência ou notificação? — a mais urgente

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

**O que precisamos saber:** qual dataset usa residência e qual usa notificação,
e qual dos dois é a fonte autoritativa do total anual.

**Por que trava:** o card de KPI lê de `incidence` e o gráfico de série
temporal lê de `_cache_ts`. Os dois vão aparecer lado a lado mostrando números
diferentes para o mesmo recorte. O dashboard em R tem a mesma inconsistência
hoje — a diferença é que agora ela está medida.

---

## 2. A regra do abandono de tratamento

O `mod_kpis.R` calcula `interrupcao_trat_pct` contando apenas `SITUA_ENCE = 2`
e usando **todos** os encerramentos no denominador, incluindo `5`
(transferência), `7` e `8`.

O indicador do Ministério da Saúde soma `2` (abandono) e `10` (abandono
primário), e exclui os não avaliados do denominador.

Para TB/PE/2024: **11,89% pela regra atual, 14,75% pelo padrão do MS.**

**O que precisamos saber:** a regra atual é deliberada — por comparabilidade
com alguma série histórica, por exemplo — ou é para seguir o padrão do MS?

As duas estão implementadas e testadas do nosso lado; falta só a decisão.

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

## 4. A pirâmide etária de tuberculose está vazia

O dataset `piramides` tem a partição `tipo` com CASOS, CURA e OBITOS. Para
tuberculose, **CURA e OBITOS somam zero** em todos os 15 anos e nos três
níveis geográficos. Só a dengue tem OBITOS preenchido; hanseníase e zika
também estão zeradas.

**O que precisamos saber:** é intencional — porque o dado não existe na fonte —
ou é falha do pipeline?

**Impacto:** a alternância CASOS/CURA/ÓBITOS da pirâmide não funciona na
entrega de TB. Nossa alternativa é montar a pirâmide de óbitos a partir de
`obitos_sim_faixa`, que tem o dado (6.354 óbitos no Brasil em 2024), mas isso
mistura fontes e vale confirmar antes.

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
a faixa sem imagem, em silêncio. Já repusemos os dois do nosso lado.
