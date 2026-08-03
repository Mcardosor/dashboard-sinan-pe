# Performance — linha de base

Medido em 03/ago/2026, antes de qualquer otimização. Reproduzir com:

```bash
python -m scripts.medir_performance
```

Mediana de 5 execuções, em milissegundos, **sem** o cache do Streamlit.

| Operação | BR | UF (PE) | MUN (Recife) |
|---|---:|---:|---:|
| `incidencia` | 1,9 | 2,0 | 2,9 |
| `incidencia_0_14` | 1,4 | 1,5 | 1,9 |
| `obitos_sim` | 0,8 | 1,1 | 1,0 |
| `serie_mensal` | 1,7 | 1,9 | 2,6 |
| `casos_novos` | 1,0 | 1,1 | 1,1 |
| `piramide` | 1,8 | 2,2 | 3,5 |
| `obitos_por_faixa` | 3,6 | 3,6 | 3,6 |
| `variavel_sinan(HIV)` | 2,8 | 2,7 | 4,5 |
| `indicador_contatos` | 1,2 | 1,8 | 2,2 |
| **`kpis.calcular`** (11 KPIs) | **14,3** | **13,8** | **18,3** |

## Leitura

A poda de partição pelo caminho está funcionando: consultar um município custa
o mesmo que consultar o Brasil, na mesma ordem de grandeza, apesar de
`sinan_landing` ter 28,9 milhões de linhas.

O conjunto completo de KPIs sai em menos de 20 ms. Com `st.cache_data` por
cima, o custo por interação tende a zero em recortes já visitados.

## O que ainda não foi medido

- Renderização do mapa, que no original é o componente mais lento
- O painel de composição, que percorre 11 variáveis de `sinan_landing`
- Comportamento com vários usuários simultâneos

O alvo de tempo de resposta por interação será fixado na semana 6, quando
mapa e gráficos existirem.
