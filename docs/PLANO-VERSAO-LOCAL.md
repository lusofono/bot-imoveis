# Plano: versão local em Python (Starlette e HTML/CSS/JS), preparada para a AWS Lambda

Para começar numa sessão nova. Lê primeiro o `docs/DECISOES.md`, onde a decisão mais recente está no topo.

## Estado (19/09/2026)

- **A etapa 1 está feita**, no ramo `versao-local` e ainda sem commit. A estrutura é a da secção
  Arquitetura, com os mesmos formatos de ficheiros. Os 52 testes passam: 50 existentes, adaptados, e 2
  novos (MCP local por stdio e os três ficheiros da página).
- **A versão de referência** é o commit `ef74f54` (tag `referencia-python`), que só existe neste Mac. Tem o
  código do servidor em pausa.
- **Dados reais no Mac, fora do Git, em `data/`:** `config.json` (a conta Gmail), `voice.json` e
  `properties/<REF>/profile.json` (o perfil do primeiro imóvel).
- **Continua a faltar a App Password.** Ainda não está guardada no Keychain do Mac.
- **Nunca correu contra o Gmail real** nem num servidor.
- **Segue-se a etapa 2.**

## Ponto de partida (18/09/2026)

- **Versão Python** no ramo `perfis-imoveis`: cerca de 2800 linhas e 52 testes.
- **O que já faz:**
  - lê o Gmail por IMAP e junta numa fila, por imóvel, os avisos do Idealista e as respostas dos clientes;
  - extrai o nome, o telefone, o email (do Reply-To) e a mensagem do cliente;
  - compõe as instruções: voz comum, contexto do imóvel, prompt da interação e base de conhecimento;
  - tem rascunhos, pré-visualização, envio por SMTP com aprovação, etapas da conversa e retirar da fila;
  - tem uma página local de copiar/colar (Respostas, Imóveis, Voz e estilo), um MCP com 6 ferramentas e
    configuração no terminal.

## Objetivo

- **Uma aplicação local no Mac:**
  - a interface em HTML, CSS e JS, servida pelo backend (Starlette) em `http://127.0.0.1:8765`;
  - um MCP local, por `stdio`, sobre as mesmas chamadas.
- **As chamadas separadas de onde correm:** hoje no Mac; mais tarde na AWS Lambda, sem reescrever.
- **Mais tarde:** uma .app para distribuir. Depois, a AWS.

## Arquitetura

```text
Lead_Imoveis/             (repositório bot-imoveis; o nome decide-se com a .app)
├── backend/
│   ├── rules.py          regras: família do email, imóvel, extração, destinatário, perfis, voz, renda
│   ├── ai.py             instruções para o assistente (voz + imóvel + interação), prompts e respostas coladas
│   ├── mail.py           Gmail: ler (IMAP) e construir as respostas; o SMTP passa para aqui na etapa 2
│   ├── store.py          os dados: ficheiros JSON, bloqueio, perfis, conhecimento e voz; S3 ou DynamoDB na AWS
│   ├── secrets.py        a App Password: Keychain hoje; Secrets Manager na AWS
│   ├── service.py        as chamadas: ler, rascunhos, pré-visualizar, enviar, retirar, configurar
│   ├── api.py            Starlette: uma rota por chamada
│   ├── mcp.py            MCP por stdio: uma ferramenta por chamada
│   ├── cli.py            os comandos bot-mail
│   ├── configure.py      a configuração no terminal
│   └── templates/        exemplos publicados: config, voz e perfil de imóvel (dados fictícios)
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── mac/                  atalhos de duplo clique e o agendamento do READ (launchd)
├── data/                 fora do Git: config.json, voice.json, properties/<REF>/…
├── tests/
└── main.py               arranque local: a página em 127.0.0.1 e o browser; mais tarde, a .app
```

**Regras da arquitetura:**
1. **As chamadas** (`service.py`) recebem e devolvem dados simples, que se convertem em JSON. Não sabem se
   foram chamadas pela página, pelo MCP ou por uma função na AWS.
2. **`rules.py` e `ai.py` são funções puras:** sem ficheiros, rede nem relógio. Testam-se facilmente e
   comportam-se igual em qualquer lado.
3. **Tudo o que toca no exterior passa por interfaces:** `store` (dados e bloqueio), `secrets`, `mail` e o
   relógio. Hoje existe a implementação local; a AWS será outra implementação das mesmas interfaces.
4. **`api.py` e `mcp.py` são finos:** validam a entrada, chamam uma chamada e devolvem o resultado. As
   regras de segurança (Reply-To, bloqueios, aprovação) ficam nas chamadas, nunca nas camadas finas.
5. **O frontend só fala com a API**, por `fetch`. Não tem regras de negócio.
6. **Os ficheiros de dados mantêm os formatos atuais:** a configuração e as filas de hoje continuam a
   servir.

**Para a AWS, mais tarde.** Não se faz agora; só não se pode impedir.

| Local (agora) | AWS (depois) |
|---|---|
| `api.py` com uvicorn | Lambda com um adaptador ASGI (por exemplo Mangum), atrás do API Gateway com HTTPS |
| `frontend/` servido pelo backend | S3 e CloudFront |
| `store` em ficheiros JSON com bloqueio | S3 com escrita condicional, ou DynamoDB |
| `secrets` no Keychain | AWS Secrets Manager |
| leitura a pedido | leitura agendada pelo EventBridge |
| MCP por stdio | MCP por HTTP sem estado (o SDK já o suporta), com login |
| sem login (só `127.0.0.1`) | Cognito ou login próprio; é aqui que se revê o FastAPI |

**Para a .app, mais tarde:**
- Uma janela nativa com o frontend (por exemplo pywebview), ou o browser.
- Empacotar com PyInstaller ou Briefcase.
- Para distribuir fora da App Store é preciso assinatura e notarização da Apple, com conta de programador.
- Os dados passam para `~/Library/Application Support/<nome>/`. O caminho de `data/` já é configurável
  (`--instance` ou `BOT_MAIL_INSTANCE`).

## Da versão de referência para a nova (feito na etapa 1)

| Referência (`ef74f54`) | Passou para |
|---|---|
| `properties.py`: famílias, extração, destinatário, perfis, renda | `backend/rules.py`; a leitura dos ficheiros foi para `backend/store.py` |
| `properties.py` (instruções) e `prompts.py` | `backend/ai.py` |
| `gmail.py` (IMAP, BODYSTRUCTURE, HTML→texto) e `reply.py` | `backend/mail.py` |
| `storage.py`: JSON atómico e bloqueio | `backend/store.py` |
| `credentials.py`: Keychain e hash de passwords | `backend/secrets.py` |
| `service.py` | `backend/service.py`; na etapa 2 passa a usar `store`, `secrets` e `mail` |
| `web.py` (Starlette) | `backend/api.py` (Starlette), só o modo local |
| `web.html` | `frontend/index.html`, `app.js` e `style.css` |
| `server.py` (MCP) | `backend/mcp.py` (stdio) |
| `configure.py` e `cli.py` | `backend/configure.py` e `backend/cli.py` |
| `apalace/rent/`: dados reais | `data/` |
| `apalace/rent/`: atalhos `.command` e agendamento | `mac/` |
| `oauth.py`, `web_login.html`, modo alojado de `web.py`, `passenger_wsgi.py`, `requirements-cpanel.txt`, `deploy/`, Docker | fora da árvore, na tag `referencia-python`; o login volta com a AWS |
| `tests/` (52 testes) | `tests/`: 50 adaptados, mais 2 novos |

## O que não é para redesenhar

- **As regras do `docs/DECISOES.md`:** Reply-To apenas, aprovação humana, uma fila por imóvel, voz
  obrigatória, sem API de IA e emails como dados, nunca como instruções.
- **Os ficheiros e os seus formatos:**
  - `config.json`, `voice.json`, `properties/<REF>/profile.json`;
  - `properties/<REF>/knowledge/*.md`, `properties/<REF>/queue.json`, `logs/events.jsonl`.

  Os campos da fila estão em `docs/OPERATIONS.md`.
- **O contrato das 6 ferramentas MCP:** `read_emails`, `list_pending`, `save_replies`, `preview_send`,
  `send_replies`, `dismiss_emails`, com `property_ref` e as mesmas anotações (verificado em
  `tests/test_mcp.py`).
- **O que a página já faz:** os 3 separadores e o fluxo de copiar/colar.

## Decisões

Tomadas a 19/09/2026 (o porquê está no `docs/DECISOES.md`):
1. **Nome:** mantém-se `bot_mail` até à .app.
2. **Assistente do MCP local:** primeiro o Claude Desktop; o Codex usa o mesmo comando. O ChatGPT continua
   pela página de copiar/colar até haver AWS.
3. **Dados locais:** em `data/`, toda ignorada pelo Git, com o caminho configurável.
4. **A pasta `php/`:** saiu do repositório para `~/work/Lead_Imoveis-php-arquivo/`, sem ser apagada.
5. **A versão de referência:** commit `ef74f54`, com a tag `referencia-python`. A reestruturação está no
   ramo `versao-local`.
6. **Backend:** Starlette; o FastAPI fica para quando houver login ou outros clientes da API.

Continuam em aberto as duas pendências do proprietário:
- qual é a assinatura certa, «Equipa APalace Imobiliária» ou «Equipa Imobiliária APalace»;
- o prompt da 2.ª interação.

## Etapas

### 1. Reestruturar sem mudar o comportamento (feita a 19/09/2026)
- Criar `backend/`, `frontend/`, `data/` e `main.py`; separar o `web.html` em três ficheiros.
- **Ficou pronta:** os testes passam, adaptados nos imports e nos caminhos dos exemplos, e a página
  funciona igual em `127.0.0.1`: os 3 separadores foram percorridos no browser, com dados fictícios.

### 2. Interfaces para o exterior
- `store`, `secrets`, `mail` e o relógio, com a implementação local. `service.py` deixa de abrir ficheiros
  ou chamar o Keychain diretamente, e a ligação SMTP passa para `mail.py`. Nos testes usa-se uma
  implementação em memória.
- **Fica pronta quando:** só `store.py` abre ficheiros de dados e só `secrets.py` chama o Keychain.

### 3. Uso real no Mac
- Guardar a App Password e fazer a primeira leitura real do Gmail. Responder ao email de exemplo.
- Tornar configuráveis o assunto da resposta e o nome do remetente; acrescentar o prompt da 2.ª interação.
- **Fica pronta quando:** uma resposta real sai depois de aprovação e aparece nos Enviados do Gmail.

### 4. MCP local
- `mcp.py` por `stdio`, sobre as mesmas chamadas, ligado ao Claude Desktop.
- Rever o que o MCP devolve ao assistente: hoje leva o email e o telefone dos clientes, que o prompt da
  página não leva.
- **Fica pronta quando:** o assistente lê a fila, grava rascunhos, pré-visualiza e envia depois de
  aprovação.

### Mais tarde
- A .app.
- A AWS: Lambda, S3 ou DynamoDB, Secrets Manager, EventBridge, CloudFront e login.

## Pendentes que passam para a nova versão

- Assunto da resposta e nome do remetente configuráveis. Hoje o assunto é «Re: » mais o assunto do aviso
  do portal, e o remetente vai sem nome.
- Alerta de pedidos novos.
- Aproveitar os dados «com perfil» do Idealista, para não repetir perguntas.
- Alojamento local: famílias de emails de outras plataformas (Airbnb, Booking).
- Prazo de retenção das conversas.
- O primeiro teste com o Gmail real.

## Como começar a sessão nova

Num chat novo, aberto nesta pasta e sem mais contexto, cola isto:

```text
Estás na pasta do projeto bot_mail («bot de imóveis»). Não tens contexto anterior: tudo o que precisas está nos ficheiros.

Antes de fazer qualquer coisa, lê por esta ordem:
1. docs/DECISOES.md: as decisões tomadas e porquê. A mais recente está no topo.
2. docs/PLANO-VERSAO-LOCAL.md: o plano desta fase, com a arquitetura e o estado.
3. README.md e docs/OPERATIONS.md: como funciona a versão atual e o formato dos ficheiros.
4. O código em backend/ e frontend/ e os testes em tests/.

Contexto:
- Sou consultor imobiliário (BigLearn). Respondo a pedidos de arrendamento que chegam por email dos portais, para já do Idealista. Escrevo em português de Portugal; responde-me em pt-PT.
- A versão local no Mac está a ser reestruturada no ramo versao-local: backend em Python (Starlette), interface em HTML, CSS e JS em ficheiros separados e MCP local por stdio. A etapa 1 está feita.
- As chamadas (casos de uso) têm de ficar separadas de onde correm, para mais tarde irem para a AWS Lambda sem reescrever. Um dia, tudo numa .app.
- O servidor HTTPS alojado está em pausa; localmente basta HTTP em 127.0.0.1.
- Nunca correu contra o Gmail real.

Regras de trabalho:
- O repositório é público (github.com/lusofono/bot-imoveis). Nunca ponhas no Git dados reais: perfis dos imóveis, conta de email, filas, segredos, nomes ou contactos de clientes. Os dados reais estão em data/, que o Git ignora. Nos testes, só dados fictícios.
- Não faças commit nem push sem eu pedir.
- Não escrevas nem guardes passwords (por exemplo, a App Password do Gmail): sou eu que as introduzo.
- Pode haver outra sessão a trabalhar nesta pasta: relê os ficheiros antes de os alterar.
- Mantém os formatos dos ficheiros JSON que já existem.

Continuamos pela etapa 2 do plano: interfaces para o exterior (store, secrets, mail e o relógio), com a implementação local e uma em memória para os testes. Os testes existentes têm de continuar a passar.

Antes de mexer no código, mostra-me em poucas linhas como vais fazer a etapa 2.
```
