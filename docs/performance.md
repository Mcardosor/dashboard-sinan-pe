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

## Geometria (semana 2.4)

Pré-processada uma vez por `scripts/preparar_geometria.py`, de GeoJSON gzipado
para GeoParquet simplificado. O dashboard em R simplificava **a cada
redesenho**; aqui é uma vez só, em disco.

| | Antes | Depois |
|---|---:|---:|
| Tamanho total | 133,7 MB | 3,7 MB |
| Carregar a malha de PE | 267 ms | 16 ms |
| Idem, já em cache | — | < 1 ms |

Dois ganhos independentes: **formato** (GeoParquet contra GeoJSON gzipado) e
**simplificação** (tolerância relativa à largura do bbox, como no original).

### Por que topológica

O `simplify` do shapely trata cada polígono isoladamente, então vizinhos
simplificam a divisa comum de formas diferentes e o mosaico se rompe. Medido
no ES com a tolerância do original: 1,97% da área do estado virava fresta e
163 pares de municípios passavam a se sobrepor — fiapos brancos e bordas
dobradas no coroplético. O dashboard em R tem esse defeito.

Com simplificação topológica, as arestas compartilhadas são simplificadas uma
única vez:

| | Por polígono | Topológica |
|---|---:|---:|
| Frestas (ES) | 1,97% | 0,41% |
| Erro de área (ES) | 0,470% | 0,088% |
| UFs sem nenhuma sobreposição | — | 15 de 27 |
| Pior sobreposição do país | — | 1,74 km² (MT) |

A pior sobreposição restante equivale a **0,06 pixel²** num mapa do Brasil de
800px de largura. Custa cerca de 1,5 s por UF na geração, uma vez só.

Limites monitorados em `tests/test_geo.py`.

---

## O payload do mapa — risco aberto, medido em 07/ago/2026

O `GeoJsonLayer` do deck.gl recebe a geometria **embutida no JSON do
componente**. Cada renderização do mapa reenvia o mosaico inteiro ao
navegador:

| Recorte | Payload | A 10 Mbit/s |
|---|---:|---:|
| Brasil (27 UFs) | 0,85 MB | 0,7 s |
| PE (185 municípios) | 0,53 MB | 0,4 s |
| **MG (853 municípios)** | **2,76 MB** | **2,2 s** |

E não é só na primeira carga: o spec muda a cada navegação e a cada troca de
métrica — as cores fazem parte dele —, então o mosaico volta pela rede toda
vez que alguém clica.

**Por que isso importa mais do que parece.** Em `localhost` o custo é zero, e
foi em `localhost` que medimos os 754 ms que hoje sustentam a comparação com
o painel em R. Sobre uma rede real, MG sozinho gasta mais tempo transferindo
mapa do que o round-trip inteiro que medimos no painel deles. A meta de
performance pode evaporar exatamente no recorte mais pesado, e nenhum teste
local mostraria isso.

**Caminhos, do mais barato ao mais caro:**

1. Simplificar mais a malha nos níveis com muitos polígonos — hoje a
   tolerância é a mesma para 27 UFs e para 853 municípios.
2. Servir a geometria uma vez e mandar só as cores nas renderizações
   seguintes. É o ganho grande e a mudança maior: exige separar geometria de
   dado no componente.
3. Aceitar e medir. Se a rede do servidor for rápida, 2,76 MB pode custar
   pouco — mas isso é uma medição, não uma suposição.

Só a opção 3 depende de servidor. As outras duas dão para atacar antes.
