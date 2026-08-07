# Publicação

Estado: **moldes prontos e subcaminho verificado; falta o servidor.**

O que já foi provado localmente e o que ainda depende de decisão está separado
abaixo de propósito — o segundo bloco é curto e é onde o processo para.

## O que já está verificado

**A aplicação funciona sob subcaminho.** Testado em
`http://localhost:8511/cenarios/sinanpe/`, que é o formato dos painéis irmãos
(`/cenarios/tbpe`). Confirmado nesse modo:

- a página carrega e o tema escuro funciona;
- o clique no mapa navega (BR → UF), com reenquadramento;
- o bloqueio de zoom por roda do mouse continua ativo — importa porque ele
  depende de um `components.v1.html`, que vira um iframe e acessa
  `window.parent`; sob subcaminho isso poderia falhar por origem, e não falha.

Reproduzir::

    streamlit run app.py --server.port 8511 --server.baseUrlPath cenarios/sinanpe

**O pacote de dados cabe em 209 MB**, contra 927 MB em disco. A diferença é
quase toda `_geo_cache`: GeoJSON gzipado que o pipeline da equipe parceira usou
e que já convertemos para GeoParquet em `data/geo` (3,7 MB). Sobra em uso um
único arquivo de lá, o de centroides.

Montar o pacote::

    python -m scripts.preparar_publicacao --conferir            # só mede
    python -m scripts.preparar_publicacao --destino /tmp/pacote

O manifesto é conferido por `tests/test_publicacao.py` contra
`conexao.PARTICOES`: dataset novo sem entrada no pacote quebra o teste, não a
produção.

## O que falta decidir

Três respostas, e nenhuma delas eu tenho:

1. **Qual servidor.** Os painéis irmãos rodam em algum host com nginx servindo
   `/cenarios/<nome>`. Preciso do endereço e de acesso.
2. **Porta e caminho.** As ocupadas que conheço: 8501, 8503, 8504, 8505, 8512.
   Sugestão: **8506** e `/cenarios/sinanpe`.
3. **Como o dado chega lá.** São 209 MB que não estão no git — de propósito.
   `scp` de uma vez, ou tem processo de sincronização?

## Moldes

Trocar `PORTA`, `CAMINHO` e os diretórios conforme as respostas acima.

### systemd

```ini
# /etc/systemd/system/sinan-pe.service
[Unit]
Description=Dashboard SINAN — Tuberculose
After=network.target

[Service]
Type=simple
User=SEU_USUARIO
WorkingDirectory=/opt/dashboard-sinan-pe
Environment="SINAN_DATA_DIR=/opt/dashboard-sinan-pe/data"
ExecStart=/opt/dashboard-sinan-pe/.venv/bin/streamlit run app.py \
  --server.port 8506 \
  --server.address 127.0.0.1 \
  --server.baseUrlPath cenarios/sinanpe \
  --server.headless true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`--server.address 127.0.0.1` não é detalhe: sem isso o Streamlit escuta em
todas as interfaces e a porta fica acessível por fora, contornando o nginx.

### nginx

```nginx
location /cenarios/sinanpe/ {
    proxy_pass http://127.0.0.1:8506/cenarios/sinanpe/;
    proxy_http_version 1.1;

    # O Streamlit fala por WebSocket. Sem estes dois cabeçalhos a página
    # carrega e congela: os widgets não respondem e nada explica por quê.
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # A primeira leitura de parquet de um recorte novo pode passar do padrão
    # de 60 s enquanto o cache está frio.
    proxy_read_timeout 300s;
}
```

O `proxy_pass` **mantém** o prefixo, porque o Streamlit já está servindo sob
ele via `baseUrlPath`. Estripar o caminho aqui é o erro clássico: os assets
respondem 404 e sobra uma tela em branco.

## Depois de subir

- [ ] Abrir a URL pública e navegar BR → UF → município
- [ ] Conferir o aviso de ano incompleto em 2025
- [ ] **Medir o tempo de resposta pela rede** e comparar com o painel em R —
      é a única forma de sustentar a meta de performance. O que temos hoje
      (754 ms nosso contra mediana de 1.020 ms deles) não vale, porque o
      nosso não pagou rede.
- [ ] Conferir o tema escuro, que ninguém testa em produção e sempre quebra
