# Instalar no servidor e ligar ao ChatGPT

Exemplo para Linux com Python 3.11+, systemd e Caddy. Não foi instalado nada no teu servidor.
Escolhe um subdomínio para esta réplica, por exemplo `mail.teudominio.pt`, com DNS para o servidor.
Abre HTTPS 443 (e 80 se usado pelo Caddy para certificados). A porta Python fica apenas em localhost.

## 1. Preparar a pasta

Clona o repositório em `/opt/bot_mail` (ou adapta os caminhos). Cria um utilizador de serviço
sem privilégios administrativos chamado `botmail`; atribui-lhe a pasta `apalace/rent`.

```bash
cd /opt/bot_mail
python3 -m venv .venv
.venv/bin/pip install -e .
sudo -u botmail .venv/bin/bot-mail --instance apalace/rent setup
```

A configuração pede conta, filtro, dias iniciais e Google App Password, sem a mostrar.
É necessária uma conta Google que permita App Passwords. A password nunca deve ir para Git,
logs, prompts ou ficheiros de configuração públicos.

## 2. Configurar a ligação OAuth

No ChatGPT, inicia a criação de uma ligação MCP personalizada em modo de desenvolvimento,
com URL `https://mail.teudominio.pt/mcp` e autenticação OAuth. Copia o callback exato que a
página de gestão da ligação apresenta. Se pedir client ID/secret, usa registo dinâmico (DCR),
quando disponível: este servidor publica `/register`. A disponibilidade e a interface variam
com o plano e as políticas da conta.

```bash
sudo -u botmail .venv/bin/bot-mail --instance apalace/rent setup-server
```

Indica:

- A origem HTTPS, **sem `/mcp`**: `https://mail.teudominio.pt`.
- O callback exato mostrado pelo ChatGPT; não uses wildcards.
- Uma password MCP longa, diferente da App Password Gmail.

A configuração gera `secrets/login.json`, com hash da password e callback permitido.
O servidor usa o callback específico da ligação; não anuncia suporte ao callback estável com `iss`.
Se alterares esta configuração, reinicia o processo e volta a ligar o ChatGPT: os grants são revogados.
Se ainda não conseguires ver o callback, podes arrancar provisoriamente com um callback HTTPS
que controles, consultar a página de gestão da ligação e voltar a executar setup-server com o
callback correto. Nenhuma ligação é autorizada com callback diferente do configurado.

## 3. Arrancar

Adapta `deploy/bot-mail.service` e copia-o para `/etc/systemd/system/bot-mail.service`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bot-mail
sudo systemctl status bot-mail
```

Adapta o domínio de `deploy/Caddyfile` e acrescenta esse bloco à configuração do teu Caddy.
Valida a configuração antes de recarregar. Mantém HTTPS válido e não publiques a pasta dos dados:
**não uses `file_server` para servir `queue.json` ou `secrets/`.**

A app não confia em headers de proxy para autenticação ou redirecionamentos. Usa a origem pública
configurada. Um worker por réplica: não usar vários workers uvicorn sobre o mesmo estado OAuth.

## 4. Concluir no ChatGPT

1. Volta à ligação MCP e conclui a autorização.
2. Na página «Ligar o teu bot_mail», introduz a password MCP e autoriza.
3. Confirma que aparecem as cinco ferramentas descritas no README.
4. Experimenta primeiro `list_pending` (sem Gmail) e depois pede «Lê os meus emails».
5. Pede rascunhos; revê o lote; só então confirma o envio.

Não é necessário configurar uma chave OpenAI. A geração das respostas acontece na conversa
da pessoa, usando as instruções dela. Mantém ativa a confirmação das ferramentas de escrita.

Documentação oficial de referência:
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/connect-chatgpt

## Docker, em alternativa

O `compose.yaml` publica apenas `127.0.0.1:8000`. Continua a ser necessário um proxy HTTPS.
Constrói a imagem e usa `docker compose run --rm bot-mail python -m bot_mail.cli setup` e
`... setup-server` para configurar a instância. A pasta montada `apalace/rent` tem de ser gravável
pelo UID 10001 do contentor. Define o proprietário no servidor antes de executar os comandos.
Depois arranca com `docker compose up -d --build`. Não uses configuração Keychain do Mac no Linux:
configura novamente a App Password no servidor. A imagem não contém dados ou segredos locais.

## Mais pessoas

Uma réplica por pessoa, com pasta, password MCP, Gmail, subdomínio e porta próprios.
Podes partilhar o código e criar outra pasta com `bot-mail replicate pessoas/ana`, copiando e
adaptando a unidade systemd (`BOT_MAIL_INSTANCE`, porta, `ReadWritePaths`) e o bloco Caddy.
Para isolamento também ao nível do sistema operativo, usa utilizadores de serviço ou contentores distintos.
Não exponhas parâmetros MCP para escolher uma pasta: cada processo está fixo à sua instância.
