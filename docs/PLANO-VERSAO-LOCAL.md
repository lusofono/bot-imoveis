# Plano: versão local em Python (FastAPI e HTML/CSS/JS), preparada para a AWS Lambda

Para começar numa sessão nova. Lê primeiro o `docs/DECISOES.md`, onde a decisão mais recente está no topo.

## Ponto de partida (18/09/2026)

- **Versão Python atual** no ramo `perfis-imoveis`: cerca de 2800 linhas e 52 testes. Nunca correu contra o
  Gmail real nem num servidor.
- **O que já faz:**
  - lê o Gmail por IMAP e junta numa fila, por imóvel, os avisos do Idealista e as respostas dos clientes;
  - extrai o nome, o telefone, o email (do Reply-To) e a mensagem do cliente;
  - compõe as instruções: voz comum, contexto do imóvel, prompt da interação e base de conhecimento;
  - tem rascunhos, pré-visualização, envio por SMTP com aprovação, etapas da conversa e retirar da fila;
  - tem uma página local de copiar/colar (Respostas, Imóveis, Voz e estilo), um MCP com 6 ferramentas e
    configuração no terminal.
- **Dados reais no Mac, fora do Git:**
  - `apalace/rent/config.json`: a conta Gmail;
  - `apalace/rent/properties/<REF>/profile.json`: o perfil do primeiro imóvel;
  - o `apalace/rent/voice.json` está no Git.
- **Falta a App Password.** Ainda não está guardada no Keychain do Mac.
- **A pasta `php/` fica sem uso.** Foi começada noutra sessão, antes de se decidir ficar em Python. O dono
  decide se a apaga.

## Objetivo

- **Uma aplicação local no Mac:**
  - a interface em HTML, CSS e JS, servida pelo FastAPI em `http://127.0.0.1:8765`;
  - um MCP local, por `stdio`, sobre as mesmas chamadas.
- **As chamadas separadas de onde correm:** hoje no Mac; mais tarde na AWS Lambda, sem reescrever.
- **Mais tarde:** uma .app para distribuir. Depois, a AWS.

## Arquitetura

```text
bot_mail/                 (nome a decidir: bot_mail ou biglearn-mail)
├── backend/
│   ├── rules.py          regras: família do email, imóvel, extração, destinatário, etapas
│   ├── ai.py             instruções para o assistente (voz + imóvel + interação), prompts e respostas coladas
│   ├── mail.py           Gmail: ler (IMAP) e enviar (SMTP)
│   ├── store.py          os dados: ficheiros JSON hoje; S3 ou DynamoDB na AWS
│   ├── secrets.py        a App Password: Keychain hoje; Secrets Manager na AWS
│   ├── service.py        as chamadas: ler, rascunhos, pré-visualizar, enviar, retirar, configurar
│   ├── api.py            FastAPI: uma rota por chamada
│   └── mcp.py            MCP por stdio: uma ferramenta por chamada
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── data/                 fora do Git: config.json, voice.json, properties/<REF>/…
├── tests/
└── main.py               arranque local: API em 127.0.0.1 e abre o browser; mais tarde, a .app
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
| `frontend/` servido pelo FastAPI | S3 e CloudFront |
| `store` em ficheiros JSON com bloqueio | S3 com escrita condicional, ou DynamoDB |
| `secrets` no Keychain | AWS Secrets Manager |
| leitura a pedido | leitura agendada pelo EventBridge |
| MCP por stdio | MCP por HTTP sem estado (o SDK já o suporta), com login |
| sem login (só `127.0.0.1`) | Cognito ou login próprio |

**Para a .app, mais tarde:**
- Uma janela nativa com o frontend (por exemplo pywebview), ou o browser.
- Empacotar com PyInstaller ou Briefcase.
- Para distribuir fora da App Store é preciso assinatura e notarização da Apple, com conta de programador.
- Os dados passam para `~/Library/Application Support/<nome>/`. Por isso o caminho de `data/` tem de ser
  configurável desde já.

## Da versão atual para a nova: reaproveitar, não reescrever

| Hoje | Passa para |
|---|---|
| `properties.py`: famílias, extração, destinatário, perfis, renda | `backend/rules.py` |
| `properties.py` (instruções) e `prompts.py` | `backend/ai.py` |
| `gmail.py` (IMAP, BODYSTRUCTURE, HTML→texto) e `reply.py` | `backend/mail.py` |
| `storage.py`: JSON atómico e bloqueio | `backend/store.py` (implementação local) |
| `credentials.py`: Keychain e hash de passwords | `backend/secrets.py` |
| `service.py`: filas, leitura, rascunhos, envio, etapas, definições | `backend/service.py`, através de `store`, `secrets` e `mail` |
| `web.py` (Starlette) | `backend/api.py` (FastAPI) |
| `web.html` | `frontend/index.html`, `app.js` e `style.css` |
| `server.py` (MCP) | `backend/mcp.py` (stdio) |
| `configure.py` e `cli.py` | configuração inicial: CLI e, mais tarde, a própria interface |
| `oauth.py`, `web_login.html`, modo alojado de `web.py`, `passenger_wsgi.py`, `requirements-cpanel.txt`, `deploy/` | em pausa; `oauth.py` e o login voltam com a AWS |
| `tests/` (52 testes) | `tests/`, com os mesmos cenários adaptados |

## O que não é para redesenhar

- **As regras do `docs/DECISOES.md`:** Reply-To apenas, aprovação humana, uma fila por imóvel, voz
  obrigatória, sem API de IA e emails como dados, nunca como instruções.
- **Os ficheiros e os seus formatos:**
  - `config.json`, `voice.json`, `properties/<REF>/profile.json`;
  - `properties/<REF>/knowledge/*.md`, `properties/<REF>/queue.json`, `logs/events.jsonl`.

  Os campos da fila estão em `docs/OPERATIONS.md`.
- **O contrato das 6 ferramentas MCP:** `read_emails`, `list_pending`, `save_replies`, `preview_send`,
  `send_replies`, `dismiss_emails`, com `property_ref` e as mesmas anotações.
- **O que a página já faz:** os 3 separadores e o fluxo de copiar/colar.

## Decisões em aberto

1. **Nome do projeto e do pacote:** manter `bot_mail` ou passar a `biglearn-mail`.
2. **Que assistente usa o MCP local.**
   - Por `stdio` ligam-se o Claude Desktop, o Codex e outros.
   - O ChatGPT só aceita MCP por endereço público (ou pelo túnel da OpenAI), ou seja, quando houver AWS.
     Até lá, com o ChatGPT usa-se a página de copiar/colar.
3. **Onde ficam os dados locais.** Proposta: `data/` na pasta do projeto, com o caminho configurável para a
   .app. Faz parte desta decisão como passar para lá os dados de `apalace/rent`.
4. **A pasta `php/`:** apagá-la ou guardá-la fora do repositório.
5. **Guardar a versão atual antes de reestruturar.** Proposta: um commit de referência no ramo
   `perfis-imoveis`, só quando o dono pedir.
6. **Duas pendências do proprietário:**
   - qual é a assinatura certa, «Equipa APalace Imobiliária» ou «Equipa Imobiliária APalace»;
   - o prompt da 2.ª interação.

## Etapas

### 1. Reestruturar sem mudar o comportamento
- Criar `backend/`, `frontend/`, `data/` e `main.py`; passar a página de Starlette para FastAPI; separar o
  `web.html` em três ficheiros.
- **Fica pronta quando:** os testes existentes passam, adaptados só nos imports, e a página funciona igual
  em `127.0.0.1`.

### 2. Interfaces para o exterior
- `store`, `secrets`, `mail` e o relógio, com a implementação local. `service.py` deixa de abrir ficheiros
  ou chamar o Keychain diretamente. Nos testes usa-se uma implementação em memória.
- **Fica pronta quando:** só `store.py` abre ficheiros de dados e só `secrets.py` chama o Keychain.

### 3. Uso real no Mac
- Guardar a App Password e fazer a primeira leitura real do Gmail. Responder ao email de exemplo.
- Tornar configuráveis o assunto da resposta e o nome do remetente; acrescentar o prompt da 2.ª interação.
- **Fica pronta quando:** uma resposta real sai depois de aprovação e aparece nos Enviados do Gmail.

### 4. MCP local
- `mcp.py` por `stdio`, sobre as mesmas chamadas, para o assistente escolhido.
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
2. docs/PLANO-VERSAO-LOCAL.md: o plano desta fase, com a arquitetura.
3. README.md e docs/OPERATIONS.md: como funciona a versão atual e o formato dos ficheiros.
4. O código em bot_mail/ e os testes em tests/: a versão atual, que vamos reestruturar, não reescrever.
Ignora a pasta php/: foi uma tentativa abandonada.

Contexto:
- Sou consultor imobiliário (BigLearn). Respondo a pedidos de arrendamento que chegam por email dos portais, para já do Idealista. Escrevo em português de Portugal; responde-me em pt-PT.
- A versão atual é em Python, no ramo perfis-imoveis. Nunca correu contra o Gmail real.
- Agora quero a versão local no Mac: backend em Python com FastAPI, interface em HTML, CSS e JS em ficheiros separados e MCP local por stdio.
- As chamadas (casos de uso) têm de ficar separadas de onde correm, para mais tarde irem para a AWS Lambda sem reescrever. Um dia, tudo numa .app.
- O servidor HTTPS alojado está em pausa; localmente basta HTTP em 127.0.0.1.

Regras de trabalho:
- O repositório é público (github.com/lusofono/bot-imoveis). Nunca ponhas no Git dados reais: perfis dos imóveis, conta de email, filas, segredos, nomes ou contactos de clientes. Nos testes, só dados fictícios.
- Não faças commit nem push sem eu pedir.
- Não escrevas nem guardes passwords (por exemplo, a App Password do Gmail): sou eu que as introduzo.
- Pode haver outra sessão a trabalhar nesta pasta: relê os ficheiros antes de os alterar.
- Mantém os formatos dos ficheiros JSON que já existem.

Começamos pela etapa 1 do plano:
1. Confirma comigo as decisões em aberto do plano: o nome do projeto, o assistente do MCP local, onde ficam os dados, a pasta php/ e o commit da versão atual antes de reestruturar. Dá a tua recomendação.
2. Reestrutura sem mudar o comportamento: backend/, frontend/ (index.html, app.js, style.css), data/, main.py e FastAPI. Os testes existentes têm de continuar a passar.

Antes de mexer no código, mostra-me em poucas linhas como vais fazer a etapa 1.
```
