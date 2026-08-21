# Publicação

Estado: **em produção desde 18/ago/2026**, na VM `wrdocker2`, porta 8507.
Público desde 20/ago/2026, quando o bloco do nginx entrou.

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/sinan/` |
| Direto, por VPN | `http://10.20.10.64:8507/cenarios/sinan/` |
| Container | `dashboard-sinan` |
| Pasta na VM | `~/dashboard-sinan-pe` |

Este documento descrevia systemd, porta 8506 e o slug `sinanpe`. As três
informações estavam erradas: foram escritas antes de alguém ter acesso à VM.
O histórico do que se supunha está no git; aqui fica só o que é verdade.

## Por que Docker, e não systemd

Os cinco painéis irmãos rodam em `docker compose`, e a receita de deploy da
família é uma linha só. Subir este com systemd faria dele o único fora do
padrão — outro jeito de subir, outro de reiniciar, outro lugar de log — e
nenhuma automação da família serviria.

## Deploy de uma mudança de código

```bash
ssh cenarios-vm 'cd ~/dashboard-sinan-pe && git pull && docker compose up -d --build'
```

O container antigo continua no ar se o build falhar: o Docker só troca depois
de construir com sucesso.

Mudança apenas em `app.py`, `src/`, `.streamlit/` ou `assets/` dispensa
rebuild — esses caminhos são montados como volume somente-leitura, então
basta `docker compose restart`. Rebuild só é necessário quando muda
`requirements.lock.txt` ou o próprio `Dockerfile`.

## Troca de dados

Os 209 MB **não estão no git**, de propósito. Chegam por fluxo único de `tar`
— e não por `scp` arquivo a arquivo, que com 2.176 arquivos pequenos paga o
custo por arquivo 2.176 vezes:

```bash
python -m scripts.preparar_publicacao --destino /tmp/pacote
tar -C /tmp/pacote -cf - . | ssh cenarios-vm 'tar -C ~/dashboard-sinan-pe/data -xf -'
```

Sem `-z`: parquet já vem comprimido, e gzipar de novo gasta CPU sem encolher.
A primeira carga levou 2 minutos.

Depois, `docker compose restart` — o cache do Streamlit tem TTL de um dia, e
reiniciar é o que garante que o dado novo apareça na hora.

## O bloco do nginx

Já aplicado em `/etc/nginx/sites-enabled/telessaude`, junto dos outros
`location`. Fica registrado para quando a VM for reconstruída:

```nginx
    location /cenarios/sinan {
        proxy_pass         http://localhost:8507;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

**O `nginx -t` antes do reload não é zelo excessivo:** erro de sintaxe nesse
arquivo derruba os seis painéis, não só este.

**Sem barra final**, nos dois lados. O bloco do `Leprosy` usa barra em ambos e
funciona porque aquele painel não declara `baseUrlPath`; aqui o Streamlit roda
com `--server.baseUrlPath=cenarios/sinan` e espera receber o prefixo. Com
barra, o nginx o cortaria e o Streamlit devolveria 404.

## Como o acesso ao repositório foi resolvido

O repositório é privado e a VM não tinha credencial nenhuma do GitHub. A saída
foi uma **deploy key somente-leitura**, gerada na VM — a privada nunca sai de
lá — e apontada por `core.sshCommand` **no próprio repositório**, não no
`~/.ssh/config` global. Assim cada painel fica com a chave dele, e uma chave
não consegue falar pelos outros.

A receita completa está no `INDEX.md`, na raiz de `Painéis_Cenários`.

## Uma armadilha que custou um susto

**O healthcheck do Streamlit não sabe se a aplicação funciona.**
`/_stcore/health` responde assim que o servidor sobe, e ignora se o script
levantou exceção. No teste local o container ficou `healthy` enquanto a página
exibia `FileNotFoundError` — o dado não estava montado.

Depois de qualquer deploy, **abra a página** e confira um número conhecido.
Container verde não é painel funcionando. Para 2024, Brasil: incidência 40,42
e 85.932 casos novos.
