# bot_mail

> **Estado a 18/09/2026.** A próxima versão é local, no Mac, e continua em Python: backend FastAPI,
> interface em HTML, CSS e JS, e MCP local. As chamadas ficam separadas de onde correm, para mais tarde
> irem para a AWS Lambda e para uma .app. Esta versão vai ser reestruturada, não reescrita. O plano está
> em [docs/PLANO-VERSAO-LOCAL.md](docs/PLANO-VERSAO-LOCAL.md) e as decisões em [docs/DECISOES.md](docs/DECISOES.md).
> A instalação num servidor HTTPS alojado (`docs/SERVER.md`, `docs/CPANEL.md`) está em pausa.

Ferramenta pessoal para trabalhar emails em lote no **teu ChatGPT**, de duas formas:
por MCP (o ChatGPT lê e grava diretamente) ou, sem MCP, por uma página local com copiar/colar.
Uma réplica = uma pasta + uma conta Gmail. Cada imóvel tem o seu `queue.json` (sem imóveis, há um só).
Sem API de IA e sem base de dados. O HTTP do servidor existe apenas para MCP e para a página de
autorização da ligação; a página de copiar/colar corre só no teu computador.

## Como se usa

1. No ChatGPT, pede: **«Lê os meus emails.»**
2. O MCP consulta o Gmail, acrescenta os novos ao JSON e devolve os pendentes.
3. Dá a tua prompt: **«Prepara respostas a estes 10 emails, em português, com estas regras…»**
4. O ChatGPT grava todos os rascunhos no mesmo JSON numa chamada `save_replies`.
5. Pede: **«Mostra o lote que vais enviar.»** Confere destinatários e textos.
6. Confirma o envio. Só os enviados com sucesso saem dos pendentes.

READ pode correr hoje, amanhã ou daqui a uma semana: retoma desde a última leitura concluída.
Não apaga rascunhos. A primeira leitura usa os dias definidos na configuração.
Os identificadores já respondidos ficam no JSON para não voltarem a entrar.
Uma nova mensagem na mesma conversa tem outro ID e entra normalmente.

## Sem MCP: página local com copiar/colar

Para quem não pode ou não quer ligar o ChatGPT por MCP (o modo de desenvolvimento depende da conta).

```bash
./apalace/rent/web.command
```

Abre `http://127.0.0.1:8765` com um código que muda a cada arranque; só funciona neste computador.
Para a abrir de qualquer lado, com password, num alojamento cPanel com «Setup Python App»: [docs/CPANEL.md](docs/CPANEL.md).

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

Cada imóvel tem uma pasta privada `properties/<REF>/` com `profile.json` (regras e prompts) e o seu
`queue.json`. A voz é da pessoa ou equipa, comum a todos os imóveis: `voice.json` (saudação, idiomas,
fecho e assinatura), escolhida sempre pelo `selected` de cada opção. Com imóveis, sem voz completa
nada arranca: o servidor recusa iniciar e as operações indicam o que falta. Uma pasta com `voice.json`
e sem perfis também recusa: nunca passa a ler o correio todo por engano. Para um imóvel novo, copia `properties/profile.example.json` para
`properties/<REF>/profile.json` e preenche os dados reais. As pastas dos imóveis nunca entram no Git.

Com pelo menos um perfil, o READ só guarda:
- avisos do portal com o remetente exato (`from_address_equals`) e a referência exata no assunto;
- respostas diretas de um cliente a um email enviado por esta ferramenta (mesma conversa no Gmail).

O resto do correio é ignorado, sem descarregar o texto.

Em cada aviso o MCP extrai o nome, o email (do Reply-To), o telefone e a mensagem do cliente, sem os
blocos do portal. Calcula também a interação (1.ª, 2.ª…) pelas respostas já enviadas a esse cliente.
A etapa só avança depois de um envio com sucesso e fica em `conversations`, mesmo depois de o email
sair da fila. A resposta vai só para o Reply-To, sem alternativa. Sem Reply-To, com vários endereços ou
com um endereço proibido (`never_reply_to`), o email fica `blocked`: não pode ser enviado e o ChatGPT
avisa-te. Conflitos (outro código de anúncio, outro email no corpo) aparecem em `warnings`.
Cada imóvel devolve `instructions`: voz comum + contexto do imóvel + prompt de cada interação.

## Estrutura

```text
bot_mail/                  código Python partilhado
apalace/rent/              primeira instância pessoal
  config.json              conta e filtros (local, ignorado pelo Git)
  voice.json               voz e estilo comuns a todos os imóveis
  properties/
    profile.example.json   modelo de perfil com dados fictícios
    <REF>/profile.json     perfil real do imóvel (local, ignorado pelo Git)
    <REF>/queue.json       fila do imóvel: pendentes, rascunhos, IDs e etapas das conversas
    <REF>/knowledge/*.md   base de conhecimento do imóvel (RAG), escrita por ti ou extraída do anúncio
  queue.json               fila única, só quando não há imóveis (criado no READ)
  logs/events.jsonl        registos sem conteúdo dos emails
  secrets/                credenciais no servidor e estado OAuth (nunca no Git)
  setup.py / .command
  setup_server.py / .command
  read.py / .command
  send.py / .command
  mcp.py / .command
  web.py / .command        página local sem MCP (copiar/colar no ChatGPT)
  install_schedule.py / .command
  uninstall_schedule.py / .command
deploy/                   exemplos de systemd e Caddy HTTPS
docs/                     instalação e operação
tests/                    testes sem Gmail real
```

## No Mac

Requer Python 3.11 ou superior.

```bash
./install.command
./apalace/rent/setup.command
./apalace/rent/read.command
```

A App Password do Gmail fica no Keychain. Não a partilhes com o ChatGPT.
Para uma réplica configurada no servidor Linux, fica num ficheiro `secrets/gmail_app_password` com permissões 600.
A password MCP é diferente e é guardada apenas como hash.

Os comandos locais READ/SEND continuam independentes. Para SEND local, preenche `reply_text`, marca
`send_reply: true` no JSON e executa `send.command`. O terminal mostra o lote e pede `ENVIAR`.
O fluxo MCP não exige editar estes campos manualmente: usa pré-visualização e confirmação.

Para um cliente MCP local com transporte stdio (por exemplo Codex):

```json
{
  "command": "/caminho/bot_mail/.venv/bin/python",
  "args": ["-m", "bot_mail.cli", "--instance", "/caminho/bot_mail/apalace/rent", "stdio"],
  "cwd": "/caminho/bot_mail"
}
```

## No teu servidor

Segue [a instalação completa](docs/SERVER.md). O endpoint é `https://teu-dominio/mcp`.
Inclui OAuth com PKCE, descoberta automática, registo de cliente e renovação de tokens.
Cada réplica aceita apenas o callback que configurares e a password MCP do seu proprietário.
Não é necessário abrir contas num fornecedor de autenticação adicional.

## Replicar

```bash
.venv/bin/bot-mail replicate pessoas/ana
.venv/bin/bot-mail --instance pessoas/ana setup
.venv/bin/bot-mail --instance pessoas/ana setup-server
```

Cria uma pasta **vazia**, sem copiar emails, credenciais, tokens ou confirmações.
As réplicas podem partilhar o mesmo código. Se preferires cópias completamente independentes,
faz um novo clone por pessoa. Não copies uma instância já configurada com os seus segredos.
No servidor, cada réplica tem processo, porta, subdomínio e credenciais próprios.
O dimensionamento de 100 processos depende dos recursos do teu servidor; não foi feito teste de carga.

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

O ChatGPT tem de mostrar a pré-visualização e obter confirmação humana. A ferramenta de envio está
marcada como destrutiva e externa para que o cliente peça aprovação. O booleano de confirmação é
fornecido pelo cliente: não constitui, por si só, prova técnica de um clique humano. Mantém a aprovação
de ferramentas de escrita ativa no ChatGPT e não autorizes envio automático.

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
- Não edites o JSON à mão durante operações. Usa as ferramentas MCP para beneficiar da validação e do lock.
- Não existe nenhuma chamada à API OpenAI. Aplicam-se os limites do plano pessoal de cada utilizador.

## Testes

```bash
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q
```

Testes de lotes, persistência, falhas SMTP, deduplicação, anexos, OAuth/MCP HTTP em memória,
leitura IMAP simulada e regras dos imóveis (com dados fictícios).
Nenhum teste lê uma caixa real ou envia emails. O arranque final no teu domínio e a ligação no ChatGPT
precisam de ser verificados depois da instalação no servidor.

Código de leitura e construção de respostas adaptado do ZIP original `gmail_cycle_mac.zip`.
O ZIP, configurações pessoais, emails e segredos não são publicados no Git.
