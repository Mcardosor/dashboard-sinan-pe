# Divergências com o dashboard em R

Toda diferença numérica entre este painel e o original deve estar registrada
aqui, com justificativa. **O que não estiver listado e divergir é bug.**

`test_referencia_r.py` compara a cada execução contra os valores lidos da tela
deles, em `referencia_r.json`, e prende as divergências nos dois sentidos: se
algo hoje idêntico regredir, falha; se um divergente passar a bater, também
falha, pedindo que a linha correspondente saia daqui.

**Estado em 11/ago/2026:** três KPIs idênticos e **nenhuma divergência
aberta**. Duas são intencionais e fechadas por decisão nossa (§2); a terceira,
que estava em aberto desde a semana 1, fechou contra fonte externa — o
Boletim Epidemiológico do Ministério da Saúde confirma o nosso número e não o
deles (§3).

Vale registrar por que a paridade com o R nunca bastou como validação: em §2
está o caso em que **os dois painéis exibiam o mesmo número errado**, e a
comparação entre eles não tinha como perceber. Fonte externa é o que fecha
essa lacuna, e é por isso que `referencia_ms.json` existe ao lado de
`referencia_r.json`.

---

## 1. Idêntico — paridade confirmada

Conferido contra a tela, PE e Brasil, ano fixado em 2024.

| KPI | Nosso | R | Observação |
|---|---:|---:|---|
| Taxa de mortalidade | 4,98 | 5,0 | Fonte comum: SIM |
| HIV positivo na testagem | 13,89% | 13,9% | |

A **interrupção de tratamento** batia aqui — 11,89% contra 11,9% — e saiu
desta seção em 20/ago/2026, por decisão, não por defeito. Ver §2.

## 2. Divergência intencional — decidida e fechada

| Item | No R | Aqui | Justificativa | Fechado em |
|---|---|---|---|---|
| Contagens de `sinan_landing` | soma o dataset inteiro | soma só `sexo='TOTAL'` | **Estamos certos e eles não.** A linha TOTAL já é a soma de M, F e I — conferido em 9,97 milhões de combinações, sem exceção. Somar tudo dobra. Em PE 2024 os dois painéis exibiam "1.034 de 8.700" quando o correto é 517 de 4.350. A proporção nunca sentiu, porque numerador e denominador dobravam juntos — foi por isso que o defeito sobreviveu à primeira comparação. | 2026-08-08 |
| Percentual em base pequena | exibe sempre | suprime abaixo de 5 registros | Proporção sobre 2 registros não é interpretável, e "100% dos casos são do sexo masculino" apoiado numa pessoa é ruído apresentado como achado. A contagem continua à vista. | 2026-08-06 |

Os denominadores exibidos passam a ser metade dos deles, de propósito:

| | Nosso | R |
|---|---:|---:|
| Encerramentos (PE, 2024) | 4.350 | 8.700 |
| Testados para HIV (PE, 2024) | 4.125 | 8.250 |

### Interrupção de tratamento (`interrupcao_trat_pct`) — mudou por decisão conjunta

| | Numerador | Denominador | PE/2024 |
|---|---|---|---:|
| Painel em R | `SITUA_ENCE = 2` | todos os encerramentos | 11,9% |
| **Nosso, desde 20/ago** | `2` + `10` | todos os encerramentos | **12,23%** |

Perguntamos à responsável pelo painel em R como ela chegava ao número. A
resposta foi *"eu conto só o 2"*, confirmando a regra que reproduzíamos. Ela
levou a questão ao **José Mário**, que definiu: **o correto é somar abandono
(2) e abandono primário (10)** — quem nunca chegou a iniciar o tratamento
também interrompeu.

O painel passou a fazer isso (`REGRA_INTERRUPCAO = "boletim"`). O de R ainda
conta só o 2, então os dois se separaram **até ele acompanhar** — e aí esta
entrada sai daqui e volta para a §1.

**Por que `boletim` e não `ms`.** As duas somam `2` + `10`; a diferença é o
denominador. A decisão do José Mário foi sobre o numerador e não mencionou o
resto. Escolhemos o denominador completo porque é o que reproduz o número
**publicado**: a Tabela 9 do Boletim de TB 2026 traz 15,2% para casos novos
no Brasil em 2024, e `boletim` dá 15,52% — os 0,32 pontos restantes são a
defasagem de extração. A regra `ms`, que exclui os não avaliados, daria
17,20% e não corresponde a nada publicado. Se o José Mário quiser o outro
denominador, é trocar uma constante.

## 3. Resolvido por fonte externa — o painel em R está errado

| Item | Campo | Nosso | R | Razão |
|---|---|---:|---:|---|
| Casos novos (Brasil) | `casos` | 85.932 | 113.651 | ×1,32 |
| Casos novos (PE) | `casos` | 5.246 | 7.438 | ×1,42 |
| Incidência (Brasil) | `incid` | 40,42 | 53,46 | ×1,32 |
| Curas (Brasil) | `cura` | 49.114 | 59.565 | ×1,21 |
| Letalidade (Brasil) | `letalidade` | 7,42% | 5,6% | consequência das duas linhas acima |

Os campos acima são exatamente os de `DIVERGENTES`, em
`test_referencia_r.py` — um teste confere que os dois não se separem.

**Fechado em 2026-08-11 pelo Boletim Epidemiológico de Tuberculose 2026**
(Ministério da Saúde, número especial de março/2026, Figura 1). O boletim
publica a série oficial de casos novos e coeficiente de incidência do Brasil,
e para 2024 dá **86.204 casos** e **40,6 por 100 mil**:

| Fonte | Casos novos (BR, 2024) | Incidência | Desvio vs MS |
|---|---:|---:|---:|
| **Boletim do MS** | **86.204** | **40,6** | — |
| Nosso painel | 85.932 | 40,42 | **−0,32%** |
| Dashboard em R | 113.651 | 53,46 | **+31,8%** |

Os 272 casos que nos separam do oficial são 0,32% e têm explicação natural: o
boletim foi extraído em fevereiro/2026 e o SINAN é atualizado retroativamente,
então nossa extração, anterior, tem alguns casos a menos. É o desvio esperado
entre duas fotografias da mesma base em datas diferentes.

Os 27.447 casos que separam o painel em R do oficial não têm explicação desse
tipo. **A divergência é deles.**

Isso não invalida a investigação anterior, só a conclui. Continua valendo que
o fator não é constante entre recortes — logo não é escala nem duplicação de
linhas — e que não é escolha de dataset do nosso lado: `incidence`,
`cases_new` e `_cache_ts` concordam entre si em torno de 85,9 mil, e nenhum
chega perto de 113 mil. A hipótese de que o card deles some recidiva e
reingresso após abandono segue sendo a mais provável, e agora é a explicação
de um erro conhecido em vez de uma dúvida sobre quem está certo.

**O que muda na prática:** a pergunta 5 de `docs/perguntas-equipe-r.md` deixa
de ser bloqueio e passa a ser aviso à equipe parceira. `DIVERGENTES` continua
com os quatro campos, porque eles de fato divergem do R e o teste que prende
isso continua sendo útil — o que mudou é que a divergência está explicada.

## 4. Divergências visuais

| Item | No R | Aqui | Justificativa |
|---|---|---|---|
| Card de KPI clicável | clicar no card troca a métrica do mapa | card é só leitura; a métrica tem controle próprio | O card não avisa que é clicável — parece indicador porque é indicador, e a única pista é o realce no hover, que não existe em toque. A interação custou quatro rodadas de conserto (botão invisível, rótulo vazando, área de clique dobrada, `aria-pressed` no DOM) para algo que um controle nativo entrega com teclado e leitor de tela incluídos. **Implementado em 08/ago/2026.** |
| Bandeira de PE na faixa | à esquerda do título | removida | Os dados são nacionais; ao lado de um mapa do Brasil ela lia como recorte geográfico, não como emissor |
| Zoom do mapa pela roda do mouse | ativo | bloqueado | Rolar a página com o cursor sobre o mapa destruía o enquadramento, sem volta a não ser recarregando |
| Overlay de carregamento | cobre a tela por ~3 s | indicador discreto | Copiar seria anunciar uma lentidão que não temos |
| Eixo da pirâmide | assimétrico | simétrico | Em TB os homens somam quase o triplo; sem simetria o excesso masculino vira efeito de escala |
| Sexos na pirâmide | tons quase iguais | duas cores distintas | Legibilidade |
| Rampa de cor gerada | `mix("#000000", base, t)`, não monotônica | `mix(base, "#000000", t)` | Rampa não monotônica invalida a leitura de escala sequencial. Não afeta a TB, que declara paletas explícitas e nunca cai no fallback |
| Tooltip dos gráficos | 10,5px | 12px | Legibilidade |
| Altura do mapa e dos painéis | `height` fixo (520/760px) | `min-height` | Valor fixo quebra em telas baixas |

## 5. Além do original

Não são divergências — são coisas que o painel deles não tem. Ficam aqui para
a comparação não parecer omissa.

- **Indicadores do programa**: contatos examinados e cultura em retratamento.
  O dado veio nos parquets e não é exibido em nenhum dos dois painéis deles.
- **Pirâmide de óbitos**: a deles só mostra CASOS.
- **Aviso de ano incompleto**, nomeando o último mês com dado.
- **Proporção de cura (%)**, que nenhum dos dois painéis tem. Entrou em
  18/ago/2026 e **substituiu a contagem de curas no mapa**, mantendo-a no card
  como fração.

  **Mudou de denominador em 21/ago/2026**, de casos novos do ano para todos os
  encerramentos — 57,15% viraram 65,1% no Brasil em 2024. O motivo foi a tela:
  com o empilhado de desfechos na evolução, passou a haver dois números de
  cura para o mesmo ano, oito pontos apart e ambos rotulados "cura". O
  denominador que ficou é o da Tabela 9 do boletim, o mesmo do card de
  interrupção. Um teste prende card, mapa e empilhado ao mesmo valor.

  A fração exibida passou a sair inteira de `SITUA_ENCE` ("2.621 de 4.350" em
  PE). Antes o numerador vinha de `incidence`, por residência, e as duas
  fontes discordam em alguns casos por UF — a conta mostrada não dava a
  porcentagem mostrada.

  A troca no mapa não é estética. Coroplético pinta **área**, e área não tem
  relação com população: com a contagem crua, São Paulo ficava no tom mais
  escuro por ser São Paulo, e o mapa de curas era na prática um mapa de
  população. Com a proporção, o Acre (78,8%) aparece à frente e a Bahia
  (42,5%) atrás — o mapa passa a mostrar desfecho de tratamento, que é o que
  o rótulo promete. O boletim do MS mapeia só taxas, nunca contagens, pela
  mesma razão.

  **Não é comparável ao 65,5% do boletim sem ajuste.** O número deles é sobre
  casos novos *confirmados por critério laboratorial*, um subconjunto; o nosso
  é sobre todos os casos novos, e dá 57,15% no Brasil em 2024. Igualar a
  população antes de comparar — é a mesma armadilha da interrupção de
  tratamento. O que corrobora é a direção: o boletim aponta o Acre como maior
  proporção de cura do país, e nós chegamos ao mesmo lugar por outro caminho.

  **É aproximação de coorte**, e a tela diz isso na ajuda do card. Tratamento
  de TB leva cerca de seis meses, então parte dos casos de um ano só encerra
  no seguinte; o boletim usa coorte fechada e nós não temos como fechar a
  coorte com os agregados que recebemos. `letalidade` convive com a mesma
  aproximação desde o início, pelo mesmo motivo.

- **Desfechos do tratamento empilhados**, no painel de evolução: cura,
  interrupção, óbito e não avaliados, ano a ano, no formato da Figura 22 do
  Boletim de TB 2026. Entrou em 21/ago/2026. Responde o que a linha isolada de
  cura não responde — para onde foi o que deixou de curar.

  **Não é o número do boletim, e a tela diz isso.** A Figura 22 é sobre
  tuberculose pulmonar *confirmada por critério laboratorial*, um subgrupo que
  não conseguimos isolar: o `sinan_landing` guarda marginais, uma variável por
  vez, e temos `SITUA_ENCE` e `FORMA` mas não o cruzamento. O nosso é sobre
  todos os casos novos encerrados, com o mesmo denominador do card de
  interrupção — um teste prende os dois juntos.

  A tendência, essa reproduz. O boletim: cura de 74,6% (2019) para 65,5%
  (2024), interrupção de 12,6% para 16,5%. Nós: 72,8% para 65,1% e 12,2% para
  15,5%.

  **Fica 1,7 ponto acima do publicado, e a causa é conhecida.** Fechado em
  22/ago/2026 — ver §6.

- **Composição por 24 variáveis**, contra 9 no painel de PE e 7 no nacional.

## 6. Diferença de denominador com a Tabela 9 do boletim — explicada

| Indicador (Brasil, 2024) | Boletim | Nosso | Diferença |
|---|---:|---:|---:|
| Cura | 63,4% | 65,13% | +1,73 |
| Interrupção de tratamento | 15,2% | 15,52% | +0,32 |
| Não avaliados | 12,6% | 7,62% | −4,98 |

**O numerador está certo; falta uma fatia do denominador.** O apêndice de
métodos do boletim (nota `e`, página impressa 51) define o denominador como o
total de casos novos com desfecho em *cura, interrupção, óbito, **ignorado ou
não avaliado***, excluindo falência (9), mudança de esquema (8) e TB
drogarresistente (7) — que são acompanhados no Site-TB — e mudança de
diagnóstico (6), por não ser tuberculose.

O `sinan_landing` **só traz linha para caso com `SITUA_ENCE` preenchido**:
75.404 no Brasil em 2024, contra 85.936 casos novos. Os 10.532 sem
encerramento não existem como linha, e é parte deles que o MS conta como "não
avaliado". Denominador menor dá proporção maior, e é por isso que os dois
indicadores ficam acima.

Reconstruído: pondo 4.066 desses casos (39% dos 10.532) no denominador, os
quatro indicadores caem a menos de meio ponto do publicado.

| Denominador | Cura | Interrupção | Óbito | Não aval. |
|---|---:|---:|---:|---:|
| Nosso hoje — todos com registro | 65,1 | 15,5 | 9,6 | 7,6 |
| Nota `e` — exclui 7/8/9 | 66,6 | 15,9 | 9,8 | 7,8 |
| Nota `e` + **todos** os sem registro | 58,3 | 13,9 | 8,6 | 19,3 |
| Nota `e` + **4.066** dos sem registro | 63,1 | 15,0 | 9,3 | 12,6 |
| **Boletim, Tabela 9** | **63,4** | **15,2** | **8,8** | **12,6** |

**Não temos como saber quais 4.066.** O agregado que recebemos não distingue,
entre os casos sem encerramento, os que o MS considera "não avaliado" dos que
deixa de fora. Por isso a regra fica como está: aplicar só a exclusão da nota
`e` afastaria mais (66,6%), e jogar todos os sem registro no denominador
afastaria muito mais (58,3%).

`test_referencia_ms.py` prende a faixa nos dois sentidos, e um segundo teste
prende a **causa**: se o dataset um dia passar a trazer os casos sem
encerramento, ele falha pedindo que esta seção saia daqui.

**Não afeta a comparação temporal**, que é para o que o empilhado serve: o
denominador é o mesmo em todos os anos, então a queda de 73,8% para 65,1%
continua válida como tendência.

---

Ver `docs/contrato-dados.md` para as armadilhas do dado e
`docs/perguntas-equipe-r.md` para o que depende de resposta.
