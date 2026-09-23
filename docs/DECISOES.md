# Decisões

As decisões de produto e de arquitetura, da mais recente para a mais antiga. Cada uma diz o que se decidiu
e porquê. O código em pausa fica no histórico do Git, na tag `referencia-python`.

## 23/09/2026: separador Contactos (v0.11.0)

**Decisão.**
- **O `contactos.csv` gere-se na página**, num separador próprio: editar nome, telefone e RGPD, acrescentar
  contactos à mão (telefone, presencial) e descarregar o ficheiro. O email e o imóvel são a chave e não se
  editam: um email errado apaga-se e acrescenta-se de novo.
- **«Apagar» é o apagamento completo pedido pelo cliente:** o CSV, a conversa, os emails por responder e as
  visitas marcadas desse imóvel. Ficam só os IDs do Gmail, que não identificam ninguém, para os mesmos emails
  não voltarem a entrar. Para quem só não quer ser contactado para outros imóveis, o estado RGPD é `nao`.
- **Os clientes respondidos antes de 22/09 entram no CSV** ao abrir o separador (nome e imóvel das conversas;
  telefone se ainda houver um email deles na fila). O dia do primeiro contacto fica em branco.

**Porquê.** O registo só começou a 22/09: 31 dos 39 clientes não estavam lá, e sem página não havia como
corrigir um nome, marcar um consentimento dado por telefone ou cumprir um pedido de apagamento.

## 22/09/2026, fim do dia: nome «Real Estate AI Assistant, by BigLearn PT» e versões

**Decisão.**
- **O nome visível passa a «Real Estate AI Assistant», by BigLearn PT** (na página e no terminal). O pacote
  Python continua `bot_mail` e o repositório `bot-imoveis`, como decidido a 19/09, até à .app.
- **Cada pedido que muda a página ou o backend sobe a versão:** PATCH para afinações, MENOR para uma
  funcionalidade nova, MAIOR para uma mudança grande. A versão vive só em `pyproject.toml`, a página lê-a
  daí, e cada versão fica descrita em `CHANGELOG.md`. Ponto de partida: 0.6.0.

**Porquê.** Com várias mudanças por dia, a versão no canto diz logo se a página aberta já tem a última
alteração (o servidor tem de ser reiniciado para o backend novo) e o changelog diz o que mudou em cada uma.

**Exceção à regra de 21/09 «o Painel nunca leva dados de clientes» (pedido do utilizador, v0.10.0):** o hover
de «Respostas enviadas» mostra o primeiro nome, datas e número de interações de quem foi respondido. Nunca
o email, o telefone nem o nome completo; o teste do Painel continua a garantir isso.

**Pedidos recebidos (v0.10.1):** cada leitura passa a registar em `logs/events.jsonl` o dia de chegada de
cada email (só o ID e a data). Os emails já respondidos antes disso são datados pela hora do envio menos as
horas que o cliente esperou, que já ficavam registadas. Os que foram retirados da fila antes desta versão não
têm data e ficam de fora.

## 22/09/2026, à noite: ponto de situação diário, sem fotografias, tradução automática e afinações de uso

Já construído (91 testes).

**Decisão.**
- **Ponto de situação diário**, para o email pessoal do proprietário (em `voice.json`, fora do Git): preparado sozinho a seguir a cada leitura
  (uma vez por dia; uma segunda leitura no mesmo dia não o repara), com o resumo por imóvel (conversas,
  pendentes, quem ainda não tem rascunho) e um total geral. Fica em `data/digest.json`, fora do Git, editável
  na página (novo painel no Painel) e só sai com um clique de confirmação — sem exceção à regra de
  aprovação humana antes de qualquer envio.
- **Sem fotografias, por agora.** Extrair fotos do Idealista à mão não é viável no dia a dia. A página deixa
  de reservar espaço com um placeholder quando não há foto: o cartão do imóvel só mostra a fotografia
  quando ela existe mesmo. A funcionalidade de carregar fotografia mantém-se possível (a API já aceita),
  mas sai da lista de próximos passos.
- **Nova opção de idioma: «Idioma do cliente + tradução em inglês».** Responde sempre na língua da
  mensagem do cliente; se essa língua não for português, inglês nem espanhol, acrescenta no fim da mesma
  resposta, claramente separada, uma tradução completa em inglês. Passa a ser a opção escolhida por
  omissão; as duas opções anteriores (idioma do cliente sem tradução; só português/inglês/francês)
  continuam disponíveis no separador Voz e estilo.
- **«Criar prompt» e «Copiar» separados,** no passo 2 das Respostas: antes, um só clique gerava o prompt no
  servidor e tentava copiá-lo, e uma falha silenciosa da cópia (ou o clique ter sido demasiado cedo, antes
  da página acabar de carregar) podia parecer que nada tinha acontecido. Agora «Criar prompt» mostra sempre
  o texto (a secção abre-se sozinha) antes de qualquer cópia, e «Copiar» só copia o que já está visível.
  Muda a seleção de emails ou o texto de instruções extra e o botão «Copiar» desativa-se, para nunca copiar
  um prompt desatualizado.

**Porquê.**
- O ponto de situação existia manualmente (eu a ler `queue.json` e a escrever um resumo à mão); passou a
  ser o mesmo programa a calculá-lo, sem inventar números.
- O botão de fotografia nunca chegou a ser construído, e mantê-lo nos «próximos passos» estava a sugerir um
  trabalho que não vale a pena para este utilizador em concreto.
- A confusão do «Copiar prompt» apareceu em uso real: parecia vazio quando, na verdade, ou ainda não tinha
  sido gerado, ou a cópia para a área de transferência tinha falhado sem aviso claro.

## 22/09/2026, mais tarde: lembretes, visitas fechadas e pedido de consentimento construídos

Já construído (83 testes). Fecha a maior parte da decisão de 21/09 «lembretes, visitas fechadas e
contactos com RGPD»; falta ainda a purga aos 6 meses e apagar um contacto a pedido.

**Decisão.**
- **«Sem resposta» nos lembretes é sempre o silêncio do cliente, nunca uma deteção de leitura.** Confirmado
  ao retomar este trabalho: mantém-se a decisão de 21/09 de não usar píxeis nem recibos de leitura. Os
  lembretes aos 2 e aos 4 dias contam sempre a partir do último envio real (nunca de um lembrete anterior),
  e o segundo só é preparado depois de o primeiro ter sido efetivamente enviado.
- **Lembretes, pedido de consentimento e o email de visitas fechadas nunca contam como uma das quatro
  interações** nem mexem no relógio dos lembretes: só o envio real (a primeira resposta, a confirmação, a
  proposta de visita e a marcação) o faz. Ficam guardados como `last_text` na conversa, para o lembrete
  seguinte poder repetir «a frase por cima do último texto enviado» tal como descrito no plano.
- **Visitas fechadas fica marcado ao clicar no botão**, não só depois de os emails saírem: mais simples e
  mais seguro do que amarrar o estado a um envio em lote que pode falhar a meio; o botão já é, por si só,
  uma ação deliberada do proprietário. A partir daí, os pedidos novos desse anúncio recebem o texto de
  fecho automaticamente, como rascunho pronto a rever.
- **O pedido de consentimento marca-se como «já pedido» ao clicar**, não ao enviar, para o botão nunca
  repetir o pedido à mesma pessoa. A deteção do «sim» só sugere; o proprietário confirma sempre com um
  clique antes de `contactos.csv` mudar.
- Todos os três continuam a regra geral: preparados pelo programa (nunca pelo ChatGPT), aparecem como
  rascunhos comuns na fila de Respostas e nada sai sem pré-visualização e confirmação.

**Porquê.**
- Reafirmar a not-tracking dos lembretes evita reabrir, sem querer, a discussão de 21/09 sobre píxeis de
  leitura (ePrivacy, falsos positivos do Apple Mail) só porque a frase «se leram» apareceu num pedido novo.
- Marcar o fecho e o pedido de consentimento no clique, em vez de esperar pelo envio, evita ter de amarrar
  este estado ao resultado, por vezes parcial, de um lote de SMTP — mais simples e mais previsível para o
  proprietário perceber o que aconteceu.

## 21/09/2026, à noite: quatro interações até à visita; tudo editável na página

Já construído (71 testes).

**Decisão.**
- **As quatro interações de cada cliente:**
  1. a primeira resposta pergunta também quando gostaria de visitar e qual é a disponibilidade habitual;
  2. a segunda confirma o que o cliente respondeu e volta a pedir só o que falta, sem propor horas;
  3. a terceira é a **proposta de visita**: o proprietário escolhe o dia e o intervalo, e a proposta vai
     para todos os clientes do imóvel, **exceto** quem disse que não quer visitar, quem só pode noutra data
     (esses aparecem desmarcados e podem ser incluídos), quem tem um email por responder e quem já tem visita;
  4. a quarta **marca a visita**: horas de 30 em 30 minutos dentro do intervalo, juntas no mesmo dia, nunca
     duas pessoas à mesma hora. A hora fica na agenda do imóvel (`properties/<REF>/visitas.json`) só depois
     de o email sair.
- **As visitas ficam na voz:** de quantos em quantos minutos se marcam, e quanto dura uma visita de
  arrendamento (15 a 20 minutos) e uma de compra (30 a 40). O proprietário espera ou aperta o horário.
- **O assistente marca no JSON colado** a hora (`visita`) e o que o cliente disse sobre visitar
  (`visita_estado`: `nao_quer` ou `outra_data`). O programa não lê os emails sozinho.
- **Cada leitura escolhe quantos dias recua**, com 7 por omissão.
- **Tudo o que orienta as respostas edita-se na página**, com uma etiqueta que diz o que é: **RAG** (os
  factos: know-how da agência e conhecimento de cada imóvel), **Prompt** (instruções: comportamento geral e
  cada interação), **Voz** (estilo comum) e **Copiar/colar** (o que se leva e traz do ChatGPT).
- **Por agora usa-se só copiar/colar;** o MCP fica para depois.

**Porquê.**
- As visitas são o objetivo das conversas, e juntá-las no mesmo dia poupa deslocações.
- Quem já disse que não pode ou não quer não deve receber a proposta; mas o proprietário decide, por isso
  aparecem desmarcados em vez de escondidos.
- A hora só fica marcada depois de o email sair: um rascunho apagado ou um envio falhado nunca ocupa horas.

## 21/09/2026, mais tarde: lembretes, visitas fechadas e contactos com RGPD

**Tudo construído a 22/09/2026** (registo de contactos, lembretes, visitas fechadas e pedido de
consentimento; 83 testes) — ver a entrada «lembretes, visitas fechadas e pedido de consentimento
construídos», no topo. Falta a purga aos 6 meses e apagar um contacto a pedido.

**Decisão.**
- **Lembretes aos 2 e aos 4 dias sem resposta do cliente**, na mesma conversa: uma frase da voz por cima
  do texto que enviámos. Não se tenta saber se o cliente leu: nem píxeis de leitura, nem recibos.
- **Aviso de «visitas fechadas»** a todos os clientes de um anúncio, com o texto na voz e um botão por
  imóvel. Um email por pessoa, nunca todos no mesmo email.
- **Registo de contactos** em `data/contactos.csv`, com email, nome, telefone, data do primeiro contacto,
  imóvel, fonte e o estado do RGPD, e um **pedido de consentimento** por email, com o texto na voz.
- **Tudo preparado pelo programa e enviado num clique**, depois da pré-visualização do lote. A regra de
  aprovar cada envio mantém-se.
- **Os contactos sem consentimento guardam-se 6 meses** depois do último contacto.

**Porquê.**
- **Sem saber se leram.** Os píxeis de leitura exigem consentimento pelas regras europeias (ePrivacy) e o
  Apple Mail abre-os sozinho, o que dá leituras falsas; os recibos dependem de o cliente aceitar.
- **Um clique em vez de automático.** O programa não sabe se o cliente respondeu por telefone ou
  WhatsApp; enviar sem olhar mandava lembretes a quem já tinha resposta.
- **RGPD.** Guardar os contactos para tratar do pedido não precisa de consentimento, mas precisa de prazo;
  usá-los para outros imóveis ou novidades precisa. O prazo e o texto do pedido confirmam-se com quem
  aconselha em RGPD.

## 21/09/2026: uso real antes das interfaces; painel, fotografias e know-how comum

**Decisão.**
- **A etapa 3 (uso real) passa à frente da etapa 2 (interfaces).**
- **O assunto e o remetente das respostas vêm da voz** (`voice.json`, editável em «Voz e estilo»):
  - resposta a um pedido do portal: sem «Re:», com um assunto próprio. Por omissão é a descrição do
    imóvel; o modelo aceita `{imovel}` e `{referencia}`;
  - resposta a um email do próprio cliente: «Re: » e o assunto dele, para não partir a conversa;
  - nome do remetente vazio por agora: vai só o endereço.
- **A assinatura é «Equipa APalace Imobiliária».** Fecha a pendência de 18/09.
- **A App Password só entra pelo terminal** (`mac/password.command`), e só fica guardada depois de o login
  IMAP funcionar.
- **A página tem um Painel com métricas**, que nunca levam dados de clientes.
- **A fotografia de cada imóvel é carregada pelo dono.** O Idealista recusa acessos automáticos (proteção
  DataDome, HTTP 403): nunca se contorna essa proteção nem se descarrega nada do anúncio.
- **Há um know-how comum da agência** em `data/knowledge/*.md`, que entra nas instruções de todos os
  imóveis. Se um imóvel disser outra coisa, prevalece o imóvel.
- **Ferramentas de interface ou outros assistentes trabalham com dados de demonstração**
  (`bot-mail demo <pasta>`), nunca com `data/`, onde estão os clientes reais.
- **Um agente de cada vez nesta pasta.**
- **Arrancar a página outra vez fecha a anterior da mesma pasta** (`.page.pid`), sem tocar noutros
  programas.

**Porquê.**
- **Etapa 3 primeiro.** A ferramenta nunca tinha corrido contra o Gmail real; o risco maior estava aí, não
  na arquitetura. A primeira leitura real (21/09) trouxe 35 pedidos, de 07/09 a 20/09, com nome, telefone
  e mensagem extraídos em todos, nenhum bloqueado e nenhum aviso.
- **Assunto.** O cliente nunca viu o aviso do portal: esse assunto foi escrito para o proprietário e leva
  emoji, a referência interna e o anunciante.
- **App Password no terminal.** Não passa pelo browser, e uma password errada nunca fica gravada.
- **Um agente de cada vez.** A 21/09 duas sessões do Claude editaram os mesmos ficheiros ao mesmo tempo:
  o comando `demo` ficou duplicado e o `bot-mail` deixou de arrancar.

**Consequências.**
- 63 testes, todos com dados fictícios.
- A página mostra a fotografia, mas ainda não tem o botão para a carregar (a API já aceita:
  `POST /api/property/photo`).
- O primeiro envio real continua por fazer: é o que fecha a etapa 3.

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
