# Divergências intencionais

Toda diferença numérica entre este dashboard e o original em R deve estar
registrada aqui, com justificativa. O que não estiver listado e divergir é bug.

| KPI | Regra do R | Regra adotada aqui | Justificativa | Decidido em |
|---|---|---|---|---|
| `interrupcao_trat_pct` | `SITUA_ENCE=2` / todos os encerramentos | *a decidir* | *a decidir* | *pendente — gate da semana 1* |

## Divergências visuais

| Item | Comportamento do R | Aqui | Justificativa |
|---|---|---|---|
| Rampa de cor gerada | `mix("#000000", base, t)` com t = 0,18/0,34/0,52, onde t é o peso da **base** — o tom mais escuro fica quase preto e os seguintes clareiam | `mix(base, "#000000", t)` com os mesmos t, escurecendo progressivamente | A rampa do R não é monotônica, o que invalida a leitura de uma escala sequencial. Não afeta a paridade da TB, que declara paletas explícitas (`PALETA_MAPA`) e nunca cai no fallback. |
| Tooltip dos gráficos | 10,5px | 12px | Legibilidade |
| Altura do mapa e dos painéis | `height` fixo (520px / 760px) | `min-height` | O valor fixo quebra em telas baixas |

Ver `docs/contrato-dados.md`, armadilha 4.
