# Página num alojamento cPanel (sem MCP)

> **Em pausa desde 18/09/2026.** O foco passou para a versão local no Mac, em Python, e o caminho para a
> internet passa a ser a AWS Lambda. Ver [DECISOES.md](DECISOES.md) e
> [PLANO-VERSAO-LOCAL.md](PLANO-VERSAO-LOCAL.md). Este guia foi testado só numa simulação do Passenger, nunca
> no alojamento real.

Para alojamentos partilhados com **«Setup Python App»**, que usam o Phusion Passenger. Aqui corre a
página de copiar/colar, protegida por password, e abre em qualquer computador ou telemóvel.

A ligação direta ao ChatGPT (MCP) precisa de um servidor próprio: vê `docs/SERVER.md`.

**Usa um só sítio para ler e responder:** ou o Mac, ou o alojamento. Cada um tem a sua fila; usar os
dois pode dar duas respostas ao mesmo cliente.

## No Mac, antes de cada pacote

```bash
.venv/bin/bot-mail --instance apalace/rent web-password
```

Pede duas coisas:
- **Endereço público:** o que vais usar na «Application URL», por exemplo `https://teudominio.pt/bot/mail`.
- **Password da página:** 12 caracteres ou mais, diferente da do Gmail. Fica guardada só como hash.

```bash
.venv/bin/python deploy/cpanel_zip.py
```

Gera `bot-imoveis-cpanel-AAAAMMDD.zip`, com o código da página, a configuração da instância e o hash da
password. Não leva a App Password do Gmail nem emails de clientes. Guarda-o em privado.

## No cPanel

1. **Limpa tentativas antigas.** Se copiaste ficheiros do bot para dentro de `public_html`, apaga-os.
2. **Envia o zip para a pasta pessoal** e extrai-o. No Gestor de Ficheiros é a pasta `/home/<utilizador>`,
   **não** `public_html`. Fica tudo em `/home/<utilizador>/bot_mail`.
3. **App Password do Gmail.** Em `bot_mail/apalace/rent/secrets/`, cria o ficheiro `gmail_app_password`
   com a App Password (as 16 letras, com ou sem espaços). Depois muda as permissões do ficheiro para
   **600**.
4. **Setup Python App → Create Application:**

   | Campo | Valor |
   |---|---|
   | Python version | A versão 3 mais alta da lista (3.11 ou superior, se houver). Nunca 2.7. |
   | Application root | `bot_mail` |
   | Application URL | o teu domínio e `bot/mail` |
   | Application startup file | `passenger_wsgi.py` |
   | Application Entry point | `application` |
   | Passenger log file | `/home/<utilizador>/bot_mail/passenger.log` |

   Carrega em **Create**.
5. **Dependências.** Na página da aplicação, em «Configuration files», acrescenta `requirements-cpanel.txt`
   e carrega em **Run Pip Install**. No fim, carrega em **Restart**.
6. Abre `https://teudominio.pt/bot/mail/`, entra com a password da página e carrega em **«Ler emails do
   Gmail»**.

## Se algo falhar

- **A página não abre:** vê o `passenger.log`.
- **«Define a password da página»:** falta `secrets/web.json`. Repete os passos no Mac.
- **«O ficheiro da App Password deve ter permissões 600»:** corrige as permissões do ficheiro.
- **Erro de ligação ao Gmail:** o alojamento está a bloquear as portas 993 (IMAP) ou 465 (SMTP). Pede ao
  alojamento para as abrir ou usa um servidor próprio.
- **Mudaste ficheiros ou a password:** carrega em Restart na página da aplicação.

## Atualizar o código

Gera um zip novo e substitui só `bot_mail/bot_mail/`, `passenger_wsgi.py` e `requirements-cpanel.txt`.
Depois carrega em Restart.

Não substituas `apalace/rent`: é aí que ficam as filas, os segredos e o que mudaste na página, como a voz,
os imóveis e os prompts.
