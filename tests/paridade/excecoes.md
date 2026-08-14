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
| Interrupção de tratamento | 11,89% | 11,9% | |

A regra do abandono estava em aberto desde a semana 1 e **fecha aqui**: nosso
padrão (`SITUA_ENCE=2` sobre todos os encerramentos, incluindo não avaliados)
reproduz o deles. O critério do Ministério da Saúde segue disponível em
`REGRA_INTERRUPCAO="ms"`, que soma abandono primário e retira os não
avaliados do denominador, e dá cerca de 4 pontos a mais.

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
- **Composição por 24 variáveis**, contra 9 no painel de PE e 7 no nacional.

---

Ver `docs/contrato-dados.md` para as armadilhas do dado e
`docs/perguntas-equipe-r.md` para o que depende de resposta.
