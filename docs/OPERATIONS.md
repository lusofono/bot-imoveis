# Operação

Os caminhos são relativos à pasta de dados: `data/` no projeto, ou a que indicares com `--instance` ou
`BOT_MAIL_INSTANCE`.

## JSON único

`queue.json` contém `emails`, `replied_message_ids`, `revision` e datas de controlo.
Cada email inclui `id`, cabeçalhos, `body_text`, `reply_text` e `reply_status`.
Depois de enviar tudo, `emails` fica `[]`. Os IDs respondidos permanecem para evitar reimportação.
O ficheiro não fica literalmente vazio: é sempre JSON válido.

Com imóveis, cada `properties/<REF>/queue.json` tem o mesmo formato, mais:
- `conversations`: por email de cliente, a etapa (`stage` = respostas enviadas com sucesso), os
  `Message-ID` enviados e as conversas do Gmail. Serve para calcular a interação seguinte e reconhecer
  as respostas do cliente. Não guarda corpos de emails.
- `dismissed_message_ids`: emails retirados sem resposta (`dismiss_emails`); também não voltam a entrar.
- Em cada email: `kind` (`lead` ou `follow_up`), `customer`, `recipient`, `blocked` e `warnings`,
  calculados no READ a partir do perfil.

`config.json` guarda a configuração. É um ficheiro técnico, não uma queue diária. O modelo só recebe os
pendentes e os resultados das operações, nunca segredos. O antigo `state.json` deixa de ser necessário e
não é consultado.

Os outros ficheiros da pasta de dados:
- `voice.json`: a voz comum, incluindo `sender_name` (nome do remetente) e `reply_subject` (assunto das
  respostas a pedidos do portal, com `{imovel}` e `{referencia}`).
- `knowledge/*.md`: o know-how comum da agência, para todos os imóveis.
- `properties/<REF>/foto.jpg`, `.png` ou `.webp`: a fotografia do imóvel, com permissões 600.
- `properties/<REF>/visitas.json`: os intervalos de visita propostos e as visitas marcadas (dia e hora,
  email e nome do cliente). Uma hora só entra aqui depois de o email que a marca sair.
- `.page.pid` e `.queue.lock`: ficheiros técnicos da página e do bloqueio. Não se editam.

## Leitura do Gmail

A leitura procura por datas na pasta «Todos» (ou na Caixa de entrada, conforme `mailbox`), ignora os IDs
que já estão na fila, respondidos ou retirados, e lê com `BODY.PEEK`: não marca nada como lido, e estar
lido ou não lido não conta. Cada leitura recua os dias que escolheres, na página ou com
`bot-mail read --days N`; por omissão, os `lookback_days` da configuração (7). Nunca recua menos do que até
à leitura anterior, por isso, depois de muitos dias parado, não se perde nada. Para ir buscar pedidos mais
antigos (por exemplo, de um imóvel acabado de configurar), escolhe mais dias só nessa leitura.

A App Password guarda-se ou troca-se com `mac/password.command`, que confirma o login antes de guardar.

## Envios incertos

Se a ligação SMTP cair, pode não ser possível saber se o Gmail aceitou a resposta.
Procura em Enviados, usando o `reply_message_id` do item (a pesquisa Gmail aceita `rfc822msgid:`).
Depois de confirmar o resultado, executa no terminal:

```bash
.venv/bin/bot-mail resolve ID_DO_EMAIL --was-sent yes
# OU, apenas se confirmaste que não foi enviado:
.venv/bin/bot-mail resolve ID_DO_EMAIL --was-sent no
```

`yes` remove o pendente e guarda o ID respondido. `no` volta a rascunho, sem enviar.
O passo seguinte exige outra pré-visualização e confirmação. Este comando não está exposto ao modelo.
Se houver mais do que um imóvel, acrescenta `--property REF`. Com `yes`, a etapa da conversa avança.

## Logs e backups

`logs/events.jsonl` guarda datas, operações, IDs e resultados, sem corpos ou credenciais. Em cada envio
guarda também quantas horas o cliente esperou, para o tempo médio do painel.
Faz backups privados da pasta de dados se precisares de recuperação. Não publiques backups no repositório.
Não há backups automáticos diários de queues; evita retenção indefinida de corpos já respondidos.
Localmente, não há rotação automática dos logs.

## Agendamento

A utilização principal é a pedido, no assistente ou na página. Não há envio automático agendado:
o SEND exige revisão e confirmação. No Mac, `mac/install_schedule.command` agenda apenas READ;
`mac/uninstall_schedule.command` remove o agendamento. O Mac precisa de estar ligado.
O lock protege as operações quando coincidem com um pedido MCP ou da página.

## Atualizar e replicar

Atualiza o código sem mexer na pasta `data/`. Reinicia a página depois de atualizar: correr outra vez
`mac/web.command` fecha a anterior.

Para trabalhar na página com outra ferramenta ou outro assistente, usa uma pasta de demonstração
(`bot-mail demo <pasta>`), nunca `data/`. Podem trabalhar vários agentes ao mesmo tempo, desde que cada um
mexa em ficheiros diferentes: dois a editar os mesmos ficheiros estragam o trabalho um do outro. As regras
para os agentes (testar só com código, sem browser; cada um nos ficheiros da sua tarefa) estão no `CLAUDE.md`.
Não copies dados privados para criar outra conta; o comando `replicate` só cria uma pasta de dados vazia.
As pastas novas usam o ambiente Python da instalação que as criou. Para mover para outra máquina,
instala um clone completo e configura a pasta de dados de novo.
