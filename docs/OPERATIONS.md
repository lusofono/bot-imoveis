# Operação

## JSON único

`queue.json` contém `emails`, `replied_message_ids`, `revision` e datas de controlo.
Cada email inclui `id`, cabeçalhos, `body_text`, `reply_text` e `reply_status`.
Depois de enviar tudo, `emails` fica `[]`. Os IDs respondidos permanecem para evitar reimportação.
O ficheiro não fica literalmente vazio: é sempre JSON válido.

`config.json` guarda a configuração; `secrets/oauth.json` guarda a ligação autenticada.
São ficheiros técnicos, não queues diárias. O modelo só recebe os pendentes e os resultados das operações,
nunca estes segredos. O antigo `state.json` deixa de ser necessário e não é consultado.

## Envios incertos

Se a ligação SMTP cair, pode não ser possível saber se o Gmail aceitou a resposta.
Procura em Enviados, usando o `reply_message_id` do item (a pesquisa Gmail aceita `rfc822msgid:`).
Depois de confirmar o resultado, executa no servidor:

```bash
.venv/bin/bot-mail --instance apalace/rent resolve ID_DO_EMAIL --was-sent yes
# OU, apenas se confirmaste que não foi enviado:
.venv/bin/bot-mail --instance apalace/rent resolve ID_DO_EMAIL --was-sent no
```

`yes` remove o pendente e guarda o ID respondido. `no` volta a rascunho, sem enviar.
O passo seguinte exige outra pré-visualização e confirmação. Este comando não está exposto ao modelo.

## Logs e backups

`logs/events.jsonl` guarda datas, operações, IDs e resultados, sem corpos ou credenciais.
Faz backups privados da pasta de dados se precisares de recuperação. Não publiques backups no repositório.
Não há backups automáticos diários de queues; evita retenção indefinida de corpos já respondidos.
Rotação dos logs fica a cargo do sistema de alojamento.

## Agendamento

A utilização principal é a pedido, no ChatGPT. Não há envio automático agendado nesta versão:
o SEND exige revisão e confirmação. No Mac, `install_schedule.command` agenda apenas READ;
`uninstall_schedule.command` remove os jobs desta instância. O Mac precisa de estar ligado.
No servidor, podes agendar `bot-mail --instance ... read` com o agendador que já usas.
O lock protege as operações quando coincidem com um pedido MCP.

## Atualizar e replicar

Atualiza o código sem substituir `config.json`, `queue.json` ou `secrets/`.
Reinicia o serviço após atualizar. Para revogar todas as ligações, executa setup-server e reinicia.
Não copies dados privados para criar outra conta; o comando `replicate` só cria configuração vazia e atalhos.
As réplicas novas partilham o ambiente Python da instalação que as criou. Para mover para outra máquina,
instala um clone completo e cria/configura a instância de novo.
