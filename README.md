# bot_mail

Ferramenta pessoal para trabalhar emails em lote no **teu ChatGPT**, através de MCP.
Uma réplica = uma pasta + uma conta Gmail + um `queue.json`.
Sem API de IA, sem base de dados, sem copiar/colar emails e sem dashboard HTTP.
O HTTP do servidor existe apenas para MCP e para a página de autorização da ligação.

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

## Estrutura

```text
bot_mail/                  código Python partilhado
apalace/rent/              primeira instância pessoal
  config.json              conta e filtros (local, ignorado pelo Git)
  queue.json               pendentes + rascunhos + IDs respondidos (criado no READ)
  logs/events.jsonl        registos sem conteúdo dos emails
  secrets/                credenciais no servidor e estado OAuth (nunca no Git)
  setup.py / .command
  setup_server.py / .command
  read.py / .command
  send.py / .command
  mcp.py / .command
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
| `read_emails` | Consulta Gmail e acrescenta novos emails; devolve o lote |
| `list_pending` | Lê o JSON sem consultar Gmail |
| `save_replies` | Guarda respostas em lote por ID, validando a revisão do JSON |
| `preview_send` | Mostra destinatários/textos e produz token válido durante 15 minutos |
| `send_replies` | Envia o lote confirmado; consome o token e remove apenas os sucessos |

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
- Filtros de assunto vazios abrangem qualquer assunto. Configura antes da primeira leitura.
- Não edites o JSON à mão durante operações. Usa as ferramentas MCP para beneficiar da validação e do lock.
- Não existe nenhuma chamada à API OpenAI. Aplicam-se os limites do plano pessoal de cada utilizador.

## Testes

```bash
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q
```

Testes de lotes, persistência, falhas SMTP, deduplicação, anexos e OAuth/MCP HTTP em memória.
Nenhum teste lê uma caixa real ou envia emails. O arranque final no teu domínio e a ligação no ChatGPT
precisam de ser verificados depois da instalação no servidor.

Código de leitura e construção de respostas adaptado do ZIP original `gmail_cycle_mac.zip`.
O ZIP, configurações pessoais, emails e segredos não são publicados no Git.
