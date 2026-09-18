# apalace/rent

Primeira réplica pessoal do **bot_mail**. Consulta o [README principal](../../README.md).

- `setup.command`: conta, filtro e App Password (Keychain no Mac).
- `voice.json`: voz e estilo comuns a todos os imóveis (saudação, idiomas, fecho, assinatura).
- `properties/<REF>/profile.json`: regras e prompts de cada imóvel; parte de `properties/profile.example.json`.
- `read.command`: acrescenta os emails novos de cada imóvel ao `queue.json` desse imóvel.
- `send.command`: mostra os rascunhos com `send_reply=true` e pede confirmação antes de enviar.
- `setup_server.command`: configura origem HTTPS, callback ChatGPT e password MCP.
- `mcp.command`: inicia o endpoint MCP autenticado; precisa de HTTPS através de proxy.
- `web.command`: abre a página local sem MCP (ler, copiar o prompt, colar a resposta, rever, enviar).
- `install_schedule.command`: agenda apenas READ no Mac.
- `uninstall_schedule.command`: remove o agendamento desta instância.

Há duas vias para responder em lote: o ChatGPT ligado ao MCP (ler, guardar rascunhos, pré-visualizar,
confirmar, sem copiar/colar) ou a página local, que troca o prompt e a resposta com o ChatGPT por copiar/colar.
Em nenhuma é preciso editar o JSON.
O SEND remove apenas os enviados com sucesso; falhas e pendentes ficam no ficheiro.
Não edites manualmente durante uma operação. Dados e credenciais desta pasta não entram no Git.
