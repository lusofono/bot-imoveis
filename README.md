# bot_mail

> **Estado a 19/09/2026.** Etapa 1 do plano feita: a versão local no Mac tem o backend em Python
> (Starlette), a interface em HTML, CSS e JS e o MCP local por stdio. As chamadas ficam separadas de onde
> correm, para mais tarde irem para a AWS Lambda e para uma .app. Segue-se a etapa 2 (interfaces para o
> exterior). O plano está em [docs/PLANO-VERSAO-LOCAL.md](docs/PLANO-VERSAO-LOCAL.md) e as decisões em
> [docs/DECISOES.md](docs/DECISOES.md). O servidor HTTPS alojado está em pausa: o código dele está na tag
> `referencia-python`.

Ferramenta pessoal para responder em lote, com o teu assistente, aos pedidos de arrendamento que chegam
por email dos portais. Há duas formas:
- pela **página local, com copiar/colar**: serve qualquer assistente, incluindo o ChatGPT;
- pelo **MCP local**: um assistente neste computador (por exemplo o Claude Desktop) lê e grava diretamente.

Uma pasta de dados = uma conta Gmail. Cada imóvel tem o seu `queue.json` (sem imóveis, há um só).
Sem API de IA e sem base de dados. Tudo corre no teu computador.

## Como se usa

1. No assistente ligado ao MCP, pede: **«Lê os meus emails.»**
2. O MCP consulta o Gmail, acrescenta os novos ao JSON e devolve os pendentes.
3. Dá a tua prompt: **«Prepara respostas a estes 10 emails, em português, com estas regras…»**
4. O assistente grava todos os rascunhos no mesmo JSON numa chamada `save_replies`.
5. Pede: **«Mostra o lote que vais enviar.»** Confere destinatários e textos.
6. Confirma o envio. Só os enviados com sucesso saem dos pendentes.

READ pode correr hoje, amanhã ou daqui a uma semana: retoma desde a última leitura concluída.
Não apaga rascunhos. A primeira leitura usa os dias definidos na configuração.
Os identificadores já respondidos ficam no JSON para não voltarem a entrar.
Uma nova mensagem na mesma conversa tem outro ID e entra normalmente.

## Sem MCP: página local com copiar/colar

Para quem não pode ou não quer ligar um assistente por MCP (o ChatGPT só aceita MCP por um endereço
público, que ainda não existe).

```bash
./mac/web.command
```

Abre `http://127.0.0.1:8765` com um código que muda a cada arranque; só funciona neste computador.
É o mesmo que `.venv/bin/python main.py`.

1. **Ler emails do Gmail** e escolher os emails a tratar.
2. **Copiar prompt** e colá-lo numa conversa normal do ChatGPT. Leva a voz, o contexto do imóvel e as
   mensagens, sem o email nem o telefone dos clientes.
3. Colar a resposta do ChatGPT (um bloco JSON) e **Guardar rascunhos**. Os rascunhos podem ser corrigidos à mão.
4. **Pré-visualizar** destinatários e textos finais e confirmar o envio.

Os emails bloqueados não entram no prompt nem no envio: trata-os à mão e retira-os da fila.
No separador **Imóveis** crias ou atualizas um imóvel à mão ou a partir do link do anúncio: a página
dá-te o prompt, o ChatGPT extrai os dados e tu revês os campos antes de guardar. O remetente do portal e
as regras de resposta nunca vêm do texto colado. As características vão para a base de conhecimento
(`knowledge/anuncio.md`). Aí editas também os prompts de cada interação; em **Voz e estilo**, a voz comum.

## Imóveis: uma família de emails por imóvel

Cada imóvel tem uma pasta privada `data/properties/<REF>/` com `profile.json` (regras e prompts) e o seu
`queue.json`. A voz é da pessoa ou equipa, comum a todos os imóveis: `data/voice.json` (saudação, idiomas,
fecho e assinatura), escolhida sempre pelo `selected` de cada opção. Com imóveis, sem voz completa
nada arranca: o MCP recusa iniciar e as operações indicam o que falta. Uma pasta com `voice.json`
e sem perfis também recusa: nunca passa a ler o correio todo por engano. Para um imóvel novo, usa o
separador **Imóveis** da página ou `mac/setup.command`; à mão, copia
`backend/templates/profile.example.json` para `data/properties/<REF>/profile.json` e preenche os dados
reais. A pasta `data/` nunca entra no Git.

Com pelo menos um perfil, o READ só guarda:
- avisos do portal com o remetente exato (`from_address_equals`) e a referência exata no assunto;
- respostas diretas de um cliente a um email enviado por esta ferramenta (mesma conversa no Gmail).

O resto do correio é ignorado, sem descarregar o texto.

Em cada aviso é extraído o nome, o email (do Reply-To), o telefone e a mensagem do cliente, sem os
blocos do portal. Calcula-se também a interação (1.ª, 2.ª…) pelas respostas já enviadas a esse cliente.
A etapa só avança depois de um envio com sucesso e fica em `conversations`, mesmo depois de o email
sair da fila. A resposta vai só para o Reply-To, sem alternativa. Sem Reply-To, com vários endereços ou
com um endereço proibido (`never_reply_to`), o email fica `blocked`: não pode ser enviado e o assistente
avisa-te. Conflitos (outro código de anúncio, outro email no corpo) aparecem em `warnings`.
Cada imóvel devolve `instructions`: voz comum + contexto do imóvel + prompt de cada interação.

## Estrutura

```text
backend/                   o código Python
  service.py               as chamadas: ler, rascunhos, pré-visualizar, enviar, retirar, configurar
  rules.py                 regras: família do email, imóvel, extração, destinatário (sem ficheiros nem rede)
  ai.py                    instruções para o assistente, prompts e respostas coladas (sem ficheiros nem rede)
  mail.py                  Gmail: ler (IMAP) e construir as respostas
  store.py                 a pasta de dados: JSON atómico, bloqueio, perfis, conhecimento e voz
  secrets.py               a App Password (Keychain no Mac)
  api.py                   a página local: uma rota por chamada (Starlette)
  mcp.py                   o MCP local por stdio: uma ferramenta por chamada
  cli.py, configure.py     os comandos bot-mail e a configuração no terminal
  templates/               exemplos publicados, com dados fictícios: config, voz e perfil de imóvel
frontend/                  a página: index.html, app.js, style.css (só fala com a API)
mac/                       atalhos de duplo clique: web, setup, read, send, agendar e desagendar o READ
main.py                    arranque local: a página em 127.0.0.1 e o browser; mais tarde, a .app
data/                      os teus dados (local, ignorado pelo Git)
  config.json              conta e filtros
  voice.json               voz e estilo comuns a todos os imóveis
  properties/<REF>/profile.json     perfil real do imóvel
  properties/<REF>/queue.json       fila do imóvel: pendentes, rascunhos, IDs e etapas das conversas
  properties/<REF>/knowledge/*.md   base de conhecimento do imóvel (RAG)
  queue.json               fila única, só quando não há imóveis (criado no READ)
  logs/events.jsonl        registos sem conteúdo dos emails
docs/                      decisões, plano e operação
tests/                     testes sem Gmail real
```

## No Mac

Requer Python 3.11 ou superior.

```bash
./install.command
./mac/setup.command
./mac/read.command
```

Os dados ficam em `data/`. Para usar outra pasta, define `BOT_MAIL_INSTANCE` ou passa
`--instance <pasta>` ao comando `bot-mail`.

A App Password do Gmail fica no Keychain. Não a partilhes com o assistente.

Os comandos locais READ/SEND continuam independentes. Para SEND local, preenche `reply_text`, marca
`send_reply: true` no JSON e executa `mac/send.command`. O terminal mostra o lote e pede `ENVIAR`.
O fluxo MCP não exige editar estes campos manualmente: usa pré-visualização e confirmação.

Para um assistente com MCP local por stdio (por exemplo o Claude Desktop ou o Codex):

```json
{
  "command": "/caminho/Lead_Imoveis/.venv/bin/bot-mail",
  "args": ["--instance", "/caminho/Lead_Imoveis/data", "stdio"]
}
```

## Servidor: em pausa

O MCP por HTTPS com OAuth, a página alojada com password, o cPanel e o Docker estão em pausa. O código
está na tag `referencia-python` e volta, adaptado, com a AWS. Ver [docs/DECISOES.md](docs/DECISOES.md).

## Replicar

```bash
.venv/bin/bot-mail replicate ~/bot-mail-outra-conta
.venv/bin/bot-mail --instance ~/bot-mail-outra-conta setup
```

Cria uma pasta de dados **vazia** para outra conta Gmail, sem copiar emails, credenciais ou confirmações.
Não copies uma pasta já configurada com os seus segredos.

## MCP

| Operação | Efeito |
|---|---|
| `read_emails` | Consulta Gmail e acrescenta novos emails; devolve o lote e as instruções por imóvel |
| `list_pending` | Lê o JSON sem consultar Gmail |
| `save_replies` | Guarda respostas em lote por ID, validando a revisão do JSON |
| `preview_send` | Mostra destinatários, textos e avisos e produz token válido durante 15 minutos |
| `send_replies` | Envia o lote confirmado; consome o token e remove apenas os sucessos |
| `dismiss_emails` | Retira emails da fila sem responder (o Gmail não é alterado) |

Com mais do que um imóvel, as operações sobre uma fila recebem `property_ref`. Com um só, é opcional.

O assistente tem de mostrar a pré-visualização e obter confirmação humana. A ferramenta de envio está
marcada como destrutiva e externa para que o cliente peça aprovação. O booleano de confirmação é
fornecido pelo cliente: não constitui, por si só, prova técnica de um clique humano. Mantém a aprovação
de ferramentas de escrita ativa no assistente e não autorizes envio automático.

## Proteções e limites

- Lock entre READ, gravação de rascunhos e SEND; escrita atómica do JSON.
- Revisão impede um rascunho antigo de sobrescrever alterações novas.
- O lote de envio fica associado aos destinatários/textos exatos; alterações exigem nova revisão.
- Se SMTP confirmar sucesso, o email sai dos pendentes. Recusas explícitas ficam como erro.
- Se a ligação cair durante um envio, o estado fica `uncertain` (ou `sending` após falha do processo).
  Não há reenvio automático: [confere o Gmail e resolve localmente](docs/OPERATIONS.md).
- Cabeçalhos e partes de texto são lidos por `BODY.PEEK`; anexos não são pedidos nem guardados.
  HTML é convertido em texto sem carregar imagens, links ou scripts. Textos longos são limitados e sinalizados.
- Sem imóveis, filtros de assunto vazios abrangem qualquer assunto. Configura antes da primeira leitura.
- Não edites o JSON à mão durante operações. Usa as ferramentas MCP ou a página para beneficiar da
  validação e do lock.
- Não existe nenhuma chamada a APIs de IA. Aplicam-se os limites do plano pessoal de cada utilizador.

## Testes

```bash
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q
```

Testes de lotes, persistência, falhas SMTP, deduplicação, anexos, leitura IMAP simulada, regras dos
imóveis, página local e MCP local por stdio, sempre com dados fictícios.
Nenhum teste lê uma caixa real ou envia emails. O primeiro teste com o Gmail real é a etapa 3 do plano.

Código de leitura e construção de respostas adaptado do ZIP original `gmail_cycle_mac.zip`.
O ZIP, configurações pessoais, emails e segredos não são publicados no Git.
