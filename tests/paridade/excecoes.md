# Divergências intencionais

Toda diferença numérica entre este dashboard e o original em R deve estar
registrada aqui, com justificativa. O que não estiver listado e divergir é bug.

| KPI | Regra do R | Regra adotada aqui | Justificativa | Decidido em |
|---|---|---|---|---|
| `interrupcao_trat_pct` | `SITUA_ENCE=2` / todos os encerramentos | **idêntica** | Confirmado contra a tela: PE 2024 dá 11,9% dos dois lados, e o denominador bate no número exato (1.034 de 8.700). A regra do MS continua disponível em `REGRA_INTERRUPCAO="ms"`, mas o padrão reproduz o R. | 2026-08-07 |
| `hiv_pos_pct` | positivos / (positivos + negativos) | **idêntica** | PE 2024: 13,9% dos dois lados, com 8.250 testados no denominador em ambos. | 2026-08-07 |
| `casos`, `incid`, `cura` | fonte desconhecida | `incidence` (residência) | **Divergência aberta, a maior que temos.** O R mostra mais casos que nós: 113.651 contra 85.932 no Brasil (×1,32) e 7.438 contra 5.246 em PE (×1,42). O fator não é constante, então não é escala nem duplicação. Nenhum dos nossos três datasets chega perto do número deles — `incidence`, `cases_new` e `_cache_ts` concordam entre si em ~85.9 mil. Nossa incidência nacional de 40,42 por 100 mil é a ordem de grandeza publicada para tuberculose no Brasil; a deles, 53,46, está acima. **Pergunta para a equipe:** de qual tabela sai o card "Casos novos", e ele inclui recidiva e reingresso após abandono? | *pendente* |
| `letalidade` | óbitos / casos, com os casos deles | óbitos / casos, com os nossos | Consequência direta da linha acima: o numerador (óbitos do SIM) bate, o denominador não. | *pendente* |

## Divergências visuais

| Item | Comportamento do R | Aqui | Justificativa |
|---|---|---|---|
| Rampa de cor gerada | `mix("#000000", base, t)` com t = 0,18/0,34/0,52, onde t é o peso da **base** — o tom mais escuro fica quase preto e os seguintes clareiam | `mix(base, "#000000", t)` com os mesmos t, escurecendo progressivamente | A rampa do R não é monotônica, o que invalida a leitura de uma escala sequencial. Não afeta a paridade da TB, que declara paletas explícitas (`PALETA_MAPA`) e nunca cai no fallback. |
| Tooltip dos gráficos | 10,5px | 12px | Legibilidade |
| Altura do mapa e dos painéis | `height` fixo (520px / 760px) | `min-height` | O valor fixo quebra em telas baixas |

## O que foi comparado

Valores lidos da tela dos dois painéis em R, com o ano fixado em 2024, e
gravados em `referencia_r.json`. O teste `test_referencia_r.py` compara a cada
execução e **prende as divergências**: se uma delas passar a bater, ele falha
pedindo que a exceção saia daqui.

Resumo em PE, 2024:

| KPI | Nosso | R | |
|---|---|---|---|
| Taxa de mortalidade | 4,98 | 5,0 | bate |
| HIV positivo na testagem | 13,89% | 13,9% | bate |
| Interrupção de tratamento | 11,89% | 11,9% | bate |
| Casos novos | 5.246 | 7.438 | **diverge** |
| Incidência | 55,00 | 77,97 | **diverge** |
| Curas | 2.619 | 3.371 | **diverge** |

O padrão é claro: tudo que sai do `sinan_landing` e do SIM reproduz o R no
número exato. Só o que sai de `incidence` diverge.

Ver `docs/contrato-dados.md`, armadilha 4.
