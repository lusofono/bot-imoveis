# apalace/rent

Primeira réplica pessoal do **bot_mail**. Consulta o [README principal](../../README.md).

- `setup.command`: conta, filtro e App Password (Keychain no Mac).
- `read.command`: acrescenta emails novos ao único `queue.json`.
- `send.command`: mostra os rascunhos com `send_reply=true` e pede confirmação antes de enviar.
- `setup_server.command`: configura origem HTTPS, callback ChatGPT e password MCP.
- `mcp.command`: inicia o endpoint MCP autenticado; precisa de HTTPS através de proxy.
- `install_schedule.command`: agenda apenas READ no Mac.
- `uninstall_schedule.command`: remove o agendamento desta instância.

A via principal para responder em lote é o ChatGPT ligado ao MCP: ler, guardar rascunhos,
pré-visualizar, confirmar. Não é preciso editar o JSON nem copiar/colar emails.
O SEND remove apenas os enviados com sucesso; falhas e pendentes ficam no ficheiro.
Não edites manualmente durante uma operação. Dados e credenciais desta pasta não entram no Git.
