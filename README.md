# bot_mail

> **Estado a 22/09/2026.** A versão local corre no Mac: backend em Python (Starlette), página em HTML,
> CSS e JS com um painel de métricas, e MCP local por stdio. Já leu o Gmail real (35 pedidos, todos
> extraídos sem erros) e já envia respostas reais, aprovadas na página. As chamadas ficam separadas de onde
> correm, para mais tarde irem para a AWS Lambda e para uma .app. O estado e os próximos passos estão em
> [docs/PLANO-VERSAO-LOCAL.md](docs/PLANO-VERSAO-LOCAL.md) e as decisões em [docs/DECISOES.md](docs/DECISOES.md).
> O servidor HTTPS alojado está em pausa: o código dele está na tag `referencia-python`.

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

## A página local

É o painel do dia a dia e o caminho sem MCP: serve qualquer assistente, incluindo o ChatGPT, por
copiar/colar (o ChatGPT só aceita MCP por um endereço público, que ainda não existe).

```bash
./mac/web.command
```

Abre `http://127.0.0.1:8765` no browser, já com o link certo. É o mesmo que `.venv/bin/python main.py`.
- **O link muda a cada arranque**, de propósito: o código no fim garante que só abre a página quem a
  arrancou, e nenhum outro site aberto no browser consegue ler a fila ou enviar emails por trás.
- **Arrancar outra vez fecha a página anterior** da mesma pasta de dados; nunca mexe noutros programas.
- Tem quatro separadores: **Painel** (métricas dos últimos 14 dias, imóveis e estado da configuração),
  **Respostas**, **Imóveis** e **Voz e estilo**, com quatro temas visuais simples (Noite, Dia, Índigo e Âmbar)
  e dois temas ricos: o **90's RacingCar** (um cockpit de GT italiano dos anos 90: carbono, nogueira, pele, caixa
  de velocidades como navegação e um quadro de instrumentos por imóvel) e o **90's Boat** (o posto de comando de
  um iate de luxo dos anos 90: casco creme, cromados, teca envernizada nos detalhes, ecrãs azuis e bandeiras de
  sinais nos separadores). Os temas ricos vivem em `frontend/themes/`, cada um com a sua folha de estilo e, quando
  traz palavras, instrumentos, seletor, relógio ou sons próprios, o seu registo em `SKINS` no `app.js`.

Tudo o que orienta as respostas edita-se na página, e cada campo diz o que é: **RAG** (factos que o
assistente consulta: o know-how da agência, em «Voz e estilo», e o conhecimento de cada imóvel, em
«Imóveis»), **Prompt** (instruções: o comportamento geral e cada interação), **Voz** (estilo comum) e
**Copiar/colar** (o que levas e trazes do ChatGPT). Por agora usa-se copiar/colar ou, opcionalmente, a API
da OpenAI (ver «Via alternativa por API» abaixo); o MCP fica para depois.

No separador **Respostas**, o fluxo é em lote. Antes de ler, escolhes quantos dias recuar (7 por omissão):

1. **Ler emails do Gmail** e escolher os emails a tratar.
2. **Criar prompt**: um só prompt para todos os selecionados, mostrado na página antes de qualquer cópia.
   Leva a voz, o contexto do imóvel e as mensagens, sem o email nem o telefone dos clientes. **Copiar**
   copia-o para colares numa conversa normal do ChatGPT — ou, com uma chave OpenAI guardada (opcional, ver
   abaixo), **Gerar respostas via API** faz este passo e o seguinte de uma vez, sem saíres da página.
3. Colar a resposta do ChatGPT, um só bloco JSON com todas as respostas, e **Guardar rascunhos**. Os
   rascunhos podem ser corrigidos à mão. (Passo saltado quando usas a API.)
4. **Pré-visualizar** destinatários e textos finais e enviar o lote com uma só confirmação — sempre, mesmo
   com respostas geradas pela API.

Lotes de 5 a 10 emails dão melhores respostas do que dezenas de uma vez: com muitos, o ChatGPT corta a
resposta ou troca ids.

Os emails bloqueados não entram no prompt nem no envio: trata-os à mão e retira-os da fila.

## Via alternativa por API

Além de Criar prompt/Copiar/Colar, o passo 02 tem **«Gerar respostas via API»**: usa a tua própria chave da
OpenAI para gerar e guardar os rascunhos diretamente, sem passares pelo ChatGPT. É o mesmo prompt, a mesma
validação e os mesmos rascunhos — muda só quem escreve a resposta. Opcional: sem chave configurada, o botão
explica o que falta e o resto da página funciona exactamente como sempre.

- **Guardar a chave:** `./mac/openai_key.command`, que a confirma contra a API da OpenAI antes de a guardar
  no Keychain (uma chave errada nunca fica gravada). Nunca passa pela página nem por um ficheiro do projeto.
- **Modelo:** `gpt-4o` por omissão; muda-se com `openai_model` em `config.json`.
- **A aprovação humana não muda:** os rascunhos gerados pela API entram na fila tal como os colados à mão,
  e o envio continua a exigir pré-visualização e confirmação.
- **Custo:** os pedidos à API são cobrados à tua conta OpenAI, ao contrário do ChatGPT por assinatura.

No separador **Imóveis** crias ou atualizas um imóvel à mão ou a partir do link do anúncio: a página
dá-te o prompt, o ChatGPT extrai os dados e tu revês os campos antes de guardar. O remetente do portal e
as regras de resposta nunca vêm do texto colado. As características vão para a base de conhecimento
(`knowledge/anuncio.md`). Aí editas também os prompts de cada interação; em **Voz e estilo**, a voz comum.

A fotografia de cada imóvel é opcional. Se existir, fica em `data/properties/<REF>/foto.jpg` (ou `.png`,
`.webp`) e aparece no painel; sem ela, o cartão do imóvel não reserva espaço nenhum para uma imagem. É
carregada pelo dono: o Idealista bloqueia acessos automáticos, por isso nada é descarregado do anúncio. A
página ainda não tem o botão para a carregar; a API já aceita (`POST /api/property/photo`), mas por agora
não é uma prioridade (ver `docs/DECISOES.md`).

## Imóveis: uma família de emails por imóvel

Cada imóvel tem uma pasta privada `data/properties/<REF>/` com `profile.json` (regras e prompts) e o seu
`queue.json`. A voz é da pessoa ou equipa, comum a todos os imóveis: `data/voice.json` (saudação, idiomas,
fecho, assinatura, nome do remetente e assunto das respostas), escolhida sempre pelo `selected` de cada
opção e editável no separador **Voz e estilo**. Com imóveis, sem voz completa
nada arranca: o MCP recusa iniciar e as operações indicam o que falta. Uma pasta com `voice.json`
e sem perfis também recusa: nunca passa a ler o correio todo por engano. Para um imóvel novo, usa o
separador **Imóveis** da página ou `mac/setup.command`; à mão, copia
`backend/templates/profile.example.json` para `data/properties/<REF>/profile.json` e preenche os dados
reais. A pasta `data/` nunca entra no Git.

Com pelo menos um perfil, o READ só guarda:
- avisos do portal com o remetente exato (`from_address_equals`) e a referência exata no assunto;
- respostas diretas de um cliente a um email enviado por esta ferramenta (mesma conversa no Gmail);
- as tuas próprias respostas escritas diretamente no Gmail a um cliente que a página conhece (pelo endereço
  ou pela conversa do Gmail; o assunto desempata um cliente de dois imóveis). Nada sai da fila: os emails
  desse cliente anteriores à tua resposta ficam marcados «Já respondeste … no Gmail» (podes ainda
  acrescentar algo, sem gastar outra etapa, ou retirá-los), a conversa avança uma interação e o que
  escreveste (sem a parte citada) entra no histórico, que a IA lê. Com «Todo o correio» já lá estão; com
  só a INBOX, a leitura abre também a pasta dos enviados.

O resto do correio é ignorado, sem descarregar o texto.

**O assunto e o remetente das respostas.** O cliente nunca viu o aviso do portal, escrito para o
proprietário, com emoji, a referência interna e o anunciante. Por isso a resposta a um pedido do portal
leva o assunto definido na voz, que por omissão é a descrição do imóvel (`{imovel}` e `{referencia}` são
substituídos). Quando é o cliente que responde a um email nosso, mantém-se «Re: » e o assunto dele, para
não partir a conversa. O nome do remetente ao lado do endereço também vem da voz; vazio, vai só o endereço.

Em cada aviso é extraído o nome, o email (do Reply-To), o telefone e a mensagem do cliente, sem os
blocos do portal. Calcula-se também a interação (1.ª, 2.ª…) pelas respostas já enviadas a esse cliente.
A etapa só avança depois de um envio com sucesso e fica em `conversations`, mesmo depois de o email
sair da fila. A resposta vai só para o Reply-To, sem alternativa. Sem Reply-To, com vários endereços ou
com um endereço proibido (`never_reply_to`), o email fica `blocked`: não pode ser enviado e o assistente
avisa-te. Conflitos (outro código de anúncio, outro email no corpo) aparecem em `warnings`.
Cada imóvel devolve `instructions`: voz comum + contexto do imóvel + prompt de cada interação.

**Know-how comum da agência.** O que vale para todos os imóveis (como marcas visitas, que documentos
pedes, prazos habituais) escreve-se em `data/knowledge/*.md` e entra nas instruções de todos. Se o
conhecimento de um imóvel disser outra coisa, prevalece o do imóvel.

**Acrescentar conhecimento a partir da página.** Em cada email de **Respostas** há «+ Acrescentar ao
conhecimento»: escreves a informação (por exemplo, «Não tem arrecadação, mas pode guardar algumas coisas no
lugar de garagem.») e escolhes se é só deste imóvel ou de todos. Vai para `knowledge/notas.md` do imóvel ou
da agência, sem apagar nada do que lá está, e o próximo prompt já a leva. No separador **Imóveis**, cada
imóvel mostra em «Conhecimento» exatamente o que o assistente recebe, das duas camadas.

## As quatro interações e as visitas

1. **Primeira resposta:** as perguntas do imóvel e ainda quando o cliente gostaria de visitar e qual é a
   disponibilidade habitual.
2. **Segunda:** confirma o que o cliente respondeu e volta a pedir só o que falta, sem propor horas.
3. **Proposta de visita:** em «Imóveis → Visitas», escolhes o dia e o intervalo e depois os clientes. Por
   omissão vão todos os clientes a quem já escrevemos, exceto quem disse que não quer visitar ou que só pode
   noutra data (aparecem desmarcados, com o motivo; podes marcá-los), quem tem um email por responder e quem
   já tem visita. Ficam rascunhos na fila de Respostas, preparados no ChatGPT como os outros.
4. **Marcação:** quando respondem, o prompt leva as horas livres. O assistente marca uma hora de 30 em 30
   minutos (definido em «Voz e estilo»), juntando as visitas no mesmo dia, e devolve-a no campo `visita` do
   JSON. A página recusa horas fora do intervalo ou já ocupadas, e a hora só fica na agenda do imóvel
   (`properties/<REF>/visitas.json`) depois de o email sair.

Em qualquer interação, se o cliente disser que não quer visitar ou que só pode noutra data, o assistente
marca-o no campo `visita_estado` (`nao_quer` ou `outra_data`), e a próxima proposta já o deixa de fora.

## Registo de contactos

Cada leitura atualiza `data/contactos.csv` (600, fora do Git): uma linha por par cliente/imóvel, com
`email`, `nome`, `telefone`, `primeiro_contacto`, `imovel`, `fonte` (por agora sempre `Idealista`) e o
estado do RGPD (`rgpd`: `por_pedir`, `pedido`, `sim` ou `nao`, com `rgpd_data` e `rgpd_prova`). Um contacto
novo entra com `rgpd: por_pedir`; uma leitura seguinte do mesmo par só preenche o nome ou o telefone que
faltavam, nunca a data do primeiro contacto nem o estado do RGPD já registado.

O separador **Contactos** mostra este CSV numa tabela: filtras por imóvel, RGPD ou texto, corriges nome,
telefone e estado RGPD, acrescentas contactos à mão (telefone, presencial) e descarregas o ficheiro.
«Apagar» é o direito ao apagamento: o contacto sai do CSV, da conversa, dos emails por responder e das
visitas marcadas do imóvel. Os clientes respondidos antes de 22/09 entram ao abrir o separador, sem o dia do
primeiro contacto. A purga aos 6 meses sem `sim` ainda está por fazer (ver `docs/PLANO-VERSAO-LOCAL.md`).

## Lembretes, visitas fechadas e pedido de consentimento

Três emails que o próprio programa prepara — nunca o ChatGPT — e que entram na fila de **Respostas** como
qualquer outro rascunho: revês, editas se quiseres, e só saem depois da pré-visualização e de confirmares
o envio, tal como todos os outros.

- **Lembretes aos 2 e aos 4 dias sem resposta.** Duas frases em **Voz e estilo**. Em cada leitura,
  preparam-se automaticamente na mesma conversa (`Re:`, `In-Reply-To` do teu último envio real): a frase
  fica por cima do último texto que enviaste a essa pessoa. Contam sempre a partir desse último envio real
  — nunca a partir de um lembrete anterior — e o dos 4 dias só é preparado depois de o dos 2 dias ter
  saído. Param se o cliente responder entretanto, se fechares as visitas do imóvel, ou se retirares o
  rascunho do lembrete da fila sem o enviar; no máximo dois por pessoa. «Sem resposta» é sempre o silêncio
  do cliente: nunca se tenta saber se ele abriu o email (sem píxeis nem recibos de leitura, como já estava
  decidido para todo o resto).
- **Visitas fechadas.** Um texto em **Voz e estilo** e, em **Imóveis → Visitas**, o botão «Fechar visitas e
  agradecer a todos»: prepara um rascunho de agradecimento para cada cliente desse anúncio, pendente ou já
  respondido. O imóvel fica fechado logo ao clicares (não só depois de enviares) e, a partir daí, qualquer
  pedido novo desse anúncio chega já com o texto de fecho pronto, como rascunho.
- **Pedido de consentimento RGPD.** Um texto em **Voz e estilo** e o botão «Pedir consentimento RGPD a
  quem respondeu», para todos os que já têm conversa e ainda não foram convidados. Quando a resposta do
  cliente começa por «sim», «yes» ou «oui», a página assinala-o no email; um clique em «Confirmar
  consentimento» grava `rgpd: sim`, a data e o email de prova em `contactos.csv`.

## Ponto de situação diário

A cada leitura, se tiveres um destinatário configurado em **Voz e estilo** («Destinatário do ponto de
situação diário»), a página prepara um resumo de todos os imóveis (conversas, pendentes e quem ainda não
tem rascunho) uma vez por dia. Aparece no **Painel**, editável antes de enviar; «Guardar» grava o texto,
«Enviar» pede confirmação e manda-o pelo Gmail — a mesma regra de aprovação humana de sempre. Uma segunda
leitura no mesmo dia não repara o resumo já preparado.

## Estrutura

```text
backend/                   o código Python
  service.py               as chamadas: ler, rascunhos, pré-visualizar, enviar, retirar, configurar
  rules.py                 regras: família do email, imóvel, extração, destinatário (sem ficheiros nem rede)
  ai.py                    instruções para o assistente, prompts e respostas coladas (sem ficheiros nem rede)
  mail.py                  Gmail: ler (IMAP) e construir as respostas
  store.py                 a pasta de dados: JSON atómico, bloqueio, perfis, conhecimento e voz
  secrets.py               a App Password e a chave OpenAI, opcional (Keychain no Mac)
  openai_client.py         a via alternativa por API da OpenAI (opcional, só urllib)
  api.py                   a página local: uma rota por chamada (Starlette)
  mcp.py                   o MCP local por stdio: uma ferramenta por chamada
  cli.py, configure.py     os comandos bot-mail e a configuração no terminal
  demo.py                  pasta de demonstração, só com dados fictícios
  templates/               exemplos publicados, com dados fictícios: config, voz e perfil de imóvel
frontend/                  a página: index.html, app.js, style.css (só fala com a API)
  themes/<tema>.css        os temas ricos ("skins"), um ficheiro cada: racing.css (90's RacingCar), boat.css (90's Boat)
mac/                       atalhos de duplo clique: web, setup, password, openai_key, read, send e o agendamento do READ
main.py                    arranque local: a página em 127.0.0.1 e o browser; mais tarde, a .app
data/                      os teus dados (local, ignorado pelo Git)
  config.json              conta e filtros
  voice.json               voz e estilo comuns a todos os imóveis
  contactos.csv            registo de contactos (RGPD), atualizado em cada leitura
  knowledge/*.md           know-how comum da agência, para todos os imóveis
  properties/<REF>/profile.json     perfil real do imóvel
  properties/<REF>/queue.json       fila do imóvel: pendentes, rascunhos, IDs e etapas das conversas
  properties/<REF>/knowledge/*.md   base de conhecimento do imóvel (RAG)
  properties/<REF>/foto.*           fotografia do imóvel, para o painel
  properties/<REF>/visitas.json     intervalos propostos, visitas marcadas e se o imóvel está fechado
  properties/<REF>/painel.json      o painel do imóvel: tempo máximo de resposta, depósito da API, distância e consumo
  queue.json               fila única, só quando não há imóveis (criado no READ)
  logs/events.jsonl        registos sem conteúdo dos emails
  .page.pid                a página que está a correr, para o arranque seguinte a fechar
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

Para trabalhar na página, ou mostrá-la a outra ferramenta, sem os clientes reais:

```bash
.venv/bin/bot-mail demo ~/bot-mail-demo
.venv/bin/bot-mail --instance ~/bot-mail-demo web --port 8766
```

A demonstração tem dois imóveis e clientes fictícios. Nunca apontes uma ferramenta de design ou outro
assistente à pasta `data/`: tem os nomes, emails e telefones dos clientes reais.

A App Password do Gmail fica no Keychain. Não a partilhes com o assistente. Para a guardar ou trocar sem
repetir o resto da configuração:

```bash
./mac/password.command
```

Cria-a na Conta Google, em Segurança → Palavras-passe de aplicações; exige a verificação em dois passos.
O comando confirma o login IMAP antes de guardar, por isso uma password errada nunca fica gravada.

A chave OpenAI (opcional, para «Gerar respostas via API») segue o mesmo padrão, também no Keychain:

```bash
./mac/openai_key.command
```

Cria-a em platform.openai.com. O comando confirma-a contra a API antes de guardar; uma chave errada nunca
fica gravada. Sem esta chave, o botão explica o que falta e o resto da página funciona na mesma.

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
Por agora não se usa: o trabalho faz-se por copiar/colar na página.

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

117 testes: lotes, persistência, falhas SMTP, deduplicação, anexos, leitura IMAP simulada, regras dos
imóveis, assunto e remetente, links do Idealista, registo de contactos, gestão de contactos, lembretes,
visitas fechadas, pedido de consentimento, ponto de situação diário, via API da OpenAI, métricas sem dados
de clientes, fotografias, página local, MCP local por stdio e comandos do terminal, sempre com dados
fictícios. Nenhum teste lê uma caixa
real ou envia emails.
A primeira leitura do Gmail real e os primeiros envios reais foram feitos à mão a 21/09/2026.

Código de leitura e construção de respostas adaptado do ZIP original `gmail_cycle_mac.zip`.
O ZIP, configurações pessoais, emails e segredos não são publicados no Git.
