# Decisões

As decisões de produto e de arquitetura, da mais recente para a mais antiga. Cada uma diz o que se decidiu
e porquê. O código em pausa fica no histórico do Git, na tag `referencia-python`.

## 19/09/2026: etapa 1 feita; Starlette em vez de FastAPI; dados em `data/`

**Decisão.**
- **O backend fica em Starlette.** O FastAPI fica para quando houver login ou outros clientes da API.
- **O nome mantém-se `bot_mail` até à .app.** Hoje há três nomes (a pasta `Lead_Imoveis`, o repositório
  `bot-imoveis` e o pacote `bot_mail`); resolvem-se de uma vez com a .app, que é quando o nome passa a
  aparecer a outras pessoas.
- **MCP local: primeiro o Claude Desktop, por stdio.** O Codex usa o mesmo comando. O ChatGPT continua
  pela página de copiar/colar até haver AWS.
- **Os dados ficam em `data/`, na pasta do projeto, toda ignorada pelo Git.** O caminho é configurável com
  `--instance` ou `BOT_MAIL_INSTANCE`. Os exemplos publicados (configuração, voz e perfil) passam para
  `backend/templates/`, e os atalhos de duplo clique para `mac/`.
- **O código em pausa sai da árvore:** o OAuth e o MCP por HTTP, a página alojada com password, o cPanel
  (Passenger), o Docker, `deploy/` e as docs `SERVER.md` e `CPANEL.md`. Fica na tag `referencia-python`
  (commit `ef74f54`).
- **A pasta `php/` saiu do repositório** para `~/work/Lead_Imoveis-php-arquivo/`, sem ser apagada.
- A reestruturação faz-se no ramo `versao-local`.

**Porquê.**
- **Starlette.** A razão dada para o FastAPI (correr na Lambda através do Mangum) também vale para o
  Starlette: o Mangum corre qualquer aplicação ASGI. O Starlette já vem com o SDK MCP, e o FastAPI
  prendia-o a um intervalo de versões. A API é pequena (14 rotas), as regras estão em `service.py` e a
  etapa 1 não devia mudar o comportamento. Como o FastAPI assenta no Starlette, a passagem pode fazer-se
  aos poucos, quando fizer falta.
- **`data/`.** Num repositório público, separa o código dos dados com uma só regra no `.gitignore`. Tem a
  mesma forma da pasta que a .app vai usar.
- **Código em pausa fora da árvore.** Mantê-lo a funcionar sem uso até à AWS custava trabalho em cada
  etapa, e o login da AWS vai ser outro (Cognito ou próprio, com o MCP por HTTP sem estado).

**Consequências.**
- Os testes do OAuth e da página alojada saíram com esse código. Há um teste novo do MCP local, que o
  arranca por stdio e confirma as 6 ferramentas e as anotações.
- `rules.py` e `ai.py` já não leem ficheiros nem o relógio. A leitura dos perfis, do conhecimento e da voz
  está em `store.py`.

## 18/09/2026, mais tarde: afinal Python, com FastAPI e interface em HTML/CSS/JS

> **Substituída na parte do FastAPI** pela decisão de 19/09/2026: o backend fica em Starlette por agora.

**Decisão.**
- A versão local continua em **Python**. A reescrita em PHP fica sem efeito.
- A interface é **HTML, CSS e JavaScript** em ficheiros separados (`frontend/`). O backend é **FastAPI**.
- **As chamadas ficam separadas de onde correm.** Cada caso de uso (ler, rascunhos, pré-visualizar,
  enviar, retirar, configurar) é uma função que recebe e devolve dados simples e não sabe se foi chamada
  pela página, pelo MCP ou por uma função na AWS. Os dados, os segredos e o email ficam atrás de interfaces:
  - hoje, com implementação local no Mac (ficheiros JSON, Keychain, IMAP/SMTP);
  - mais tarde, na **AWS Lambda**, sem reescrever os casos de uso.
- **Localmente:** HTTP em `127.0.0.1` e MCP por `stdio`. Não é preciso HTTPS local. O HTTPS chega com a
  AWS (API Gateway ou Lambda).
- **Um dia, uma .app:** tudo empacotado numa aplicação para distribuir.
- O servidor HTTPS alojado (VPS Linux, cPanel) continua em pausa.

**Porquê.**
- O PHP não evolui bem para a AWS Lambda, a versão local ficava limitada e é difícil fazer dela uma
  aplicação para distribuir.
- O Python é mais natural para isto:
  - IMAP e SMTP na biblioteca padrão;
  - o SDK MCP oficial;
  - o FastAPI corre localmente (uvicorn) e na Lambda (através de um adaptador ASGI como o Mangum);
  - empacota-se numa aplicação (PyInstaller, Briefcase).
- A versão Python atual já tem a lógica e 52 testes: reestrutura-se em vez de se reescrever.

**Consequências.** A pasta `php/`, começada noutra sessão, fica sem uso. O plano está em
`docs/PLANO-VERSAO-LOCAL.md`.

## 18/09/2026: pausa no servidor HTTPS; versão local em PHP

> **Substituída na parte do PHP** pela decisão acima. A pausa no servidor HTTPS alojado continua válida.
> A 19/09/2026 o código do servidor saiu da árvore: está na tag `referencia-python`.

**Decisão.**
- Fica em pausa tudo o que é servidor HTTPS alojado: o VPS Linux (systemd e Caddy, `docs/SERVER.md`) e o
  alojamento cPanel com Passenger (`docs/CPANEL.md`).
- A próxima versão é local: corre no computador de quem responde (primeiro o Mac, depois o Windows), com
  uma página em HTTP local e um MCP local.
- É escrita em **PHP**, para mais tarde poder ir para um servidor PHP (como o cPanel que já existe) sem
  reescrever. O plano está em `docs/PLANO-VERSAO-LOCAL.md`.

**Porquê.**
- O alojamento partilhado (cPanel da PT Domínios) só corre Python através do Passenger: é preciso uma
  camada WSGI e um login próprio, não aguenta o servidor MCP e pode bloquear as portas do Gmail. Um VPS
  resolve isso, mas exige administrar um servidor.
- Uma versão local é o caminho mais curto para responder a emails reais.
- O PHP corre no alojamento que já existe e instala-se no Mac e no Windows, o que facilita voltar ao
  servidor mais tarde com a mesma base de código.

**O que fica.**
- A versão Python é a referência: a lógica, os 34 cenários de teste e os formatos dos ficheiros.
- O código do servidor fica no repositório, em pausa: `server.py`, `oauth.py`, `passenger_wsgi.py`,
  `requirements-cpanel.txt`, `deploy/`, e o modo alojado de `web.py`.
- Não há trabalho em servidores até a versão local em PHP estar completa.

## 18/09/2026: decisões anteriores de que a versão PHP depende

- **Repositório público sem dados sensíveis.** Os perfis reais dos imóveis, a configuração, as filas e os
  segredos ficam fora do Git. No Git só entram exemplos com dados fictícios, como
  `properties/profile.example.json`.
- **Uma família de emails e uma fila por imóvel.** Um aviso do portal pertence a um imóvel pelo remetente
  exato e pela referência exata no assunto. Outro imóvel é outro perfil e outra fila.
- **A voz é de quem responde, não do imóvel.** Saudação, idiomas, fecho e assinatura estão em
  `voice.json`, comuns a todos os imóveis. Sem a voz completa, nada arranca: não se improvisa um
  tratamento.
- **O perfil de cada imóvel** guarda os dados do anúncio, as regras de resposta e os prompts de cada
  interação (geral, 1.ª, 2.ª e base de conhecimento). Pode ser criado à mão ou a partir do link do anúncio,
  com o ChatGPT a extrair os dados. O remetente do portal e as regras de resposta nunca vêm de texto colado.
- **A resposta vai só para o Reply-To.** Sem Reply-To, com mais do que um endereço ou com um endereço
  proibido, o email fica bloqueado e nunca se usa outro endereço por aproximação.
- **Aprovação humana antes de cada envio.** Há uma pré-visualização válida 15 minutos, presa aos textos
  exatos. Se a ligação cair a meio, o envio fica incerto e nunca se reenvia sozinho.
- **Sem API de IA.** As respostas são redigidas no ChatGPT (ou noutro assistente) de quem responde, por MCP
  ou por copiar e colar. Os emails dos clientes são dados, nunca instruções.
- **Etapas da conversa.** A interação só avança depois de um envio com sucesso e fica registada depois de
  o email sair da fila. As respostas diretas do cliente ligam-se pela conversa do Gmail ou pelos Message-ID
  enviados.
- **Servidor para várias pessoas.** Um único endereço HTTPS, com uma pasta por pessoa e o login a escolher
  a pasta, em vez de um processo por pessoa. Está em pausa com o resto do servidor.
