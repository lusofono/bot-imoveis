# Plano: versão local em Python (Starlette e HTML/CSS/JS), preparada para a AWS Lambda

Para começar numa sessão nova. Lê primeiro o `docs/DECISOES.md`, onde a decisão mais recente está no topo.

## Estado (22/09/2026)

- **Etapa 1 feita e publicada:** commit `b2c61ee` no ramo `versao-local`, com push para o GitHub. A
  referência é o commit `ef74f54` (tag `referencia-python`, só local), com o código do servidor em pausa.
- **Etapa 3 (uso real) feita, à frente da etapa 2.** Está em commit (`864c16d` e o seguinte, de 22/09):
  - App Password guardada no Keychain com `mac/password.command`, que confirma o login antes de guardar;
  - **primeira leitura real a 21/09:** 35 pedidos, com nome, telefone e mensagem extraídos em todos;
  - **primeiros envios reais:** até 22/09, 44 respostas enviadas depois de aprovadas, a 38 clientes de
    dois imóveis; 6 clientes já vão na 2.ª interação;
  - assunto e nome do remetente configuráveis na voz;
  - **nome do cliente em cada conversa:** o código novo guarda-o em cada envio; nas conversas anteriores,
    foi preenchido a 22/09 a partir do assunto dos avisos do Idealista (só cabeçalhos). Uma página aberta
    antes de 21/09 à noite corre o código antigo, que não o guarda: reinicia-a com `./mac/web.command`.
- **As quatro interações até à visita** (ver `docs/DECISOES.md`, 21/09 à noite): proposta de visita a
  todos, com exceções, marcação de 30 em 30 minutos na agenda do imóvel, e dias à escolha em cada leitura.
- **Tudo o que orienta as respostas edita-se na página**, com etiquetas RAG, Prompt, Voz e Copiar/colar.
- **Feito também, fora das etapas:**
  - Painel com métricas (pendentes, rascunhos, bloqueados, enviados, tempo até resposta, 14 dias);
  - a página redesenhada, com quatro temas visuais;
  - fotografia de cada imóvel (a API aceita-a; falta o botão para a carregar na página);
  - know-how comum da agência em `data/knowledge/`;
  - `bot-mail demo <pasta>`, para trabalhar na página só com dados fictícios;
  - arrancar a página outra vez fecha a anterior da mesma pasta.
- **71 testes passam**, todos com dados fictícios.
- **Dados reais no Mac, fora do Git, em `data/`:** a conta, a voz, o know-how, e dois imóveis com o
  perfil, o conhecimento e a fila de cada um.
- **Por agora usa-se só copiar/colar;** o MCP fica para depois.

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
│   ├── demo.py           pasta de demonstração com dados fictícios
│   ├── configure.py      a configuração no terminal
│   └── templates/        exemplos publicados: config, voz e perfil de imóvel (dados fictícios)
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── mac/                  atalhos de duplo clique e o agendamento do READ (launchd)
├── data/                 fora do Git: config.json, voice.json, knowledge/, properties/<REF>/…, logs/
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
- **O que a página já faz:** os 4 separadores (Painel, Respostas, Imóveis, Voz e estilo) e o fluxo
  de copiar/colar em lote.

## Decisões

O porquê está no `docs/DECISOES.md`.

Tomadas a 19/09/2026:
1. **Nome:** mantém-se `bot_mail` até à .app.
2. **Assistente do MCP local:** primeiro o Claude Desktop; o Codex usa o mesmo comando. O ChatGPT continua
   pela página de copiar/colar até haver AWS.
3. **Dados locais:** em `data/`, toda ignorada pelo Git, com o caminho configurável.
4. **A pasta `php/`:** saiu do repositório para `~/work/Lead_Imoveis-php-arquivo/`, sem ser apagada.
5. **A versão de referência:** commit `ef74f54`, com a tag `referencia-python`.
6. **Backend:** Starlette; o FastAPI fica para quando houver login ou outros clientes da API.

Tomadas a 21/09/2026:
7. **A etapa 3 passa à frente da etapa 2.**
8. **Assinatura:** «Equipa APalace Imobiliária».
9. **Assunto e remetente na voz;** pedidos do portal sem «Re:».
10. **Fotografias carregadas pelo dono;** nunca descarregadas do Idealista, que bloqueia robôs.
11. **Um agente de cada vez nesta pasta;** ferramentas de fora só com dados de demonstração.
12. **Lembretes, visitas fechadas e pedido de consentimento:** preparados pelo programa e enviados num
    clique. Lembretes aos 2 e aos 4 dias sem resposta, sem tentar saber se leram.
13. **Contactos:** registo em `data/contactos.csv`; sem consentimento, guardam-se 6 meses.

Continua em aberto: **o prompt da 2.ª interação**, que o proprietário ainda vai escrever.

## Etapas

### 1. Reestruturar sem mudar o comportamento (feita a 19/09/2026, commit `b2c61ee`)
- Criar `backend/`, `frontend/`, `data/` e `main.py`; separar o `web.html` em três ficheiros.
- **Ficou pronta:** os testes passam, adaptados nos imports e nos caminhos dos exemplos, e a página
  funciona igual em `127.0.0.1`: os 3 separadores foram percorridos no browser, com dados fictícios.

### 2. Interfaces para o exterior
- `store`, `secrets`, `mail` e o relógio, com a implementação local. `service.py` deixa de abrir ficheiros
  ou chamar o Keychain diretamente, e a ligação SMTP passa para `mail.py`. Nos testes usa-se uma
  implementação em memória.
- **Fica pronta quando:** só `store.py` abre ficheiros de dados e só `secrets.py` chama o Keychain.

### 3. Uso real no Mac (feita a 21/09/2026; passou à frente da 2)
- Feito: App Password guardada; primeira leitura real (35 pedidos); primeiros envios reais; assunto e
  remetente configuráveis; prompts das quatro interações.
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

## Próximos passos, por esta ordem

Regra comum: o programa prepara, e nada sai sem a pré-visualização do lote e uma confirmação.

1. **Registo de contactos** em `data/contactos.csv` (permissões 600, fora do Git), atualizado em cada
   leitura. Colunas: `email`, `nome`, `telefone`, `primeiro_contacto`, `imovel`, `fonte` (Idealista),
   `rgpd` (`por_pedir`, `pedido`, `sim` ou `nao`), `rgpd_data` e `rgpd_prova` (o Message-ID da resposta em
   que o cliente disse sim). Os contactos sem `sim` apagam-se 6 meses depois do último contacto. Quem
   pedir para ser apagado sai do CSV, da fila e das conversas.
2. **Visitas fechadas:** o texto fica na voz. Um botão por imóvel prepara um email para cada cliente desse
   anúncio, pendentes e já respondidos com endereço válido: um email por pessoa. Depois do envio, o imóvel
   fica «fechado», os pendentes saem da fila e os pedidos novos desse anúncio chegam com o texto preparado.
3. **Lembretes aos 2 e aos 4 dias sem resposta:** duas frases na voz. Em cada leitura, preparam-se na
   mesma conversa (`Re:`, `In-Reply-To` do nosso último envio): a frase por cima do último texto que
   enviámos, que passa a ficar guardado na conversa. Param se o cliente responder, se as visitas fecharem ou
   se o email for retirado; no máximo dois.
4. **Pedido de consentimento:** o texto fica na voz, e há um botão por imóvel para todos os que
   responderam. Nas respostas que começam por «sim», «yes» ou «oui», a página sugere `sim` e o proprietário
   confirma com um clique; guarda-se a prova.
5. **O botão para carregar a fotografia** no separador Imóveis (a API já existe).
6. **Um JSON por run, para o Codex ou o Claude trabalharem sem copiar/colar:** cada run numa pasta
   `data/runs/<data-e-hora>/` com `pedidos.json` (o que o agente lê) e `respostas.json` (o que escreve), e
   um comando `bot-mail drafts` que aplica as respostas com as mesmas verificações.
7. **Separador Definições:** conta, dias de leitura por omissão, pasta do Gmail e agendamento, hoje só no
   terminal.
8. **Ícone no Desktop:** uma app sem janela de Terminal, com o código de acesso guardado em `data/` para
   não mudar a cada arranque.
9. Etapa 2 (interfaces) e etapa 4 (MCP no Claude Desktop), quando se voltar a usar MCP.

## Pendentes que passam para a nova versão

- Alerta de pedidos novos.
- Aproveitar os dados «com perfil» do Idealista, para não repetir perguntas.
- Alojamento local: famílias de emails de outras plataformas (Airbnb, Booking).
- Prazo de retenção das conversas e das filas (o dos contactos está decidido: 6 meses).

## Como começar a sessão nova

Num chat novo, aberto nesta pasta e sem mais contexto, cola isto:

```text
Estás na pasta do projeto bot_mail («bot de imóveis»). Não tens contexto anterior: tudo o que precisas está nos ficheiros.

Antes de fazer qualquer coisa, lê por esta ordem:
1. docs/DECISOES.md: as decisões tomadas e porquê. A mais recente está no topo.
2. docs/PLANO-VERSAO-LOCAL.md: o estado, a arquitetura e os próximos passos.
3. README.md e docs/OPERATIONS.md: como funciona e o formato dos ficheiros.
4. O código em backend/ e frontend/ e os testes em tests/.

Contexto:
- Sou consultor imobiliário (BigLearn). Respondo a pedidos de arrendamento que chegam por email dos portais, para já do Idealista. Escrevo em português de Portugal; responde-me em pt-PT.
- A versão local corre no Mac (ramo versao-local): backend em Python (Starlette), página em HTML/CSS/JS e MCP local por stdio. As etapas 1 e 3 (uso real) estão feitas: a App Password está guardada, a primeira leitura real trouxe 35 pedidos e já saíram as primeiras respostas reais, aprovadas na página. Por agora trabalha-se só por copiar/colar na página; o MCP fica para depois.
- As chamadas (casos de uso) ficam separadas de onde correm, para mais tarde irem para a AWS Lambda sem reescrever. Um dia, tudo numa .app.
- O servidor HTTPS alojado está em pausa; localmente basta HTTP em 127.0.0.1.

Regras de trabalho:
- O repositório é público (github.com/lusofono/bot-imoveis). Nunca ponhas no Git dados reais: perfis dos imóveis, conta de email, filas, segredos, nomes ou contactos de clientes. Os dados reais estão em data/, que o Git ignora. Nos testes, só dados fictícios.
- Não abras nem mostres dados de clientes sem precisar: para verificar, usa contagens. Para trabalhar na página, usa uma pasta de demonstração (bot-mail demo <pasta>).
- Não faças commit nem push sem eu pedir.
- Não escrevas nem guardes passwords (por exemplo, a App Password do Gmail): sou eu que as introduzo.
- Um agente de cada vez nesta pasta. Se vires ficheiros a mudar sem teres sido tu, para e avisa-me.
- Mantém os formatos dos ficheiros JSON que já existem.
- O envio de emails exige sempre a minha aprovação, depois da pré-visualização.

Continuamos pelos próximos passos do plano, pela ordem indicada. Antes de mexer no código, mostra-me em poucas linhas como vais fazer o passo seguinte.
```
