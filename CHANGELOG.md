# Changelog — ARIA, by BigLearn.pt

A versão aparece no canto superior esquerdo da página e vem de um só sítio: `version` em `pyproject.toml`.
Cada pedido que muda a página ou o backend sobe a versão e fica registado aqui, do mais recente para o mais
antigo:

- **PATCH** (0.7.0 → 0.7.1): uma afinação ou correção pequena;
- **MENOR** (0.7 → 0.8): uma funcionalidade ou pedido novo;
- **MAIOR** (0.x → 1.0, 1.x → 2.0): uma mudança grande no funcionamento.

**Desde 23/09/2026, a versão mostra-se como «α.X.Y», não «0.X.Y»** (pedido do utilizador): o "0" inicial
lia-se mal como zero absoluto; o símbolo α diz mais claramente "isto ainda é alfa". Só a apresentação muda —
o `pyproject.toml` continua com o número normal (`0.X.Y`), que é o que as ferramentas Python exigem; este
ficheiro passa a usar «α.X.Y» a partir daqui, para corresponder ao que aparece na página.

O porquê de cada decisão está em `docs/DECISOES.md`; aqui fica só o quê.

## α.106.0 — 03/10/2026

- **Proprietários por proprietário:** em cima escolhe-se o proprietário (da lista de proprietários, com ou sem imóveis),
  e vêem-se os imóveis dele (juntar ou tirar um imóvel ali mesmo), todas as mensagens dele de qualquer imóvel, «Escrever
  ao proprietário» (sobre um dos imóveis dele, ou sem imóvel), o ponto de situação de cada imóvel dele e o conhecimento
  só dele. «Novo proprietário» junta um à lista, com ou sem imóveis.
- **Um proprietário sem imóveis na ARIA** também é lido: os emails dele vão para a caixa dos proprietários
  (`data/proprietarios/caixa.json`) — nunca para as Comunicações —, e responde-se-lhe da mesma forma (rascunho, IA,
  pré-visualização, envio com a marca). As mensagens dos proprietários nunca aparecem nas Comunicações; o contador do
  menu conta as de todos.

## α.105.0 — 03/10/2026

- **Short list sem botão:** quando um cliente está na short list (escolhido, suplente ou short list), a resposta
  seguinte nas Comunicações pede os documentos sozinha (prompt «Short list: pedir documentos», editável na Oficina),
  sem nunca dizer «short list», «escolhido» nem «suplente». Depois de pedidos, cada resposta dele é lida pelo que
  escreveu e pelos **nomes dos anexos** (nada se abre nem descarrega): a IA agradece o que chegou, diz o que falta, e os
  documentos que chegaram ficam marcados na seleção (Contactos), onde se podem corrigir. O cartão diz «short list ·
  pedir documentos» ou «short list · documentos», mostra os anexos (📎) e o que ainda falta.
- **A leitura guarda os nomes dos anexos** de cada email, tirados da estrutura da mensagem; as imagens das
  assinaturas não contam.

## α.104.0 — 03/10/2026

- **Visitas: «Atualizar visitas» pode ir dias para trás** (só as próximas, 30, 60 ou 90 dias). As visitas confirmadas
  nesse período que já passaram entram na agenda «por registar» (veio ou não veio, dizes tu), uma só vez e sem enviar
  nada; o agradecimento e o inquérito saem só depois de registares. Serve para reconstruir a agenda.

## α.103.1 — 03/10/2026

- **Emails em tratamento: «Desistiu» sai das colunas** e passa a ser a primeira linha por baixo do quadro, antes de «Sem
  resposta», aberta por defeito (com o motivo, quando há).
- **Chamadas:** confirmado com os avisos verdadeiros do Gmail (12 em 10 dias, todos lidos). As chamadas de um anúncio da
  agência que não está na ARIA guardam a referência e deixam de aparecer em «sem imóvel identificado».

## α.103.0 — 02/10/2026

- **Chamadas do portal na página de cada imóvel** (Imóveis): lidas em «Ler emails» (de `naoresponder@idealista.pt`),
  guardadas à parte (`chamadas.json`), com a hora da chamada, atendida ou não, e o cliente quando o telefone é conhecido;
  WhatsApp, SMS e Ligar; «Procurar» vai N dias para trás no Gmail. As sem imóvel nem cliente ficam numa linha no fim.
- **Proprietários:** o que ele enviou numa conversa de um cliente (lida como «conversa ambígua») passa para o lado dele
  e sai do histórico do cliente. O conhecimento para todos os proprietários passa para a Voz e estilo; no separador
  Proprietários fica o conhecimento **deste** proprietário, só nas respostas a ele.

## α.102.0 — 02/10/2026

- **O portal passa a ser configurável** (Oficina → «Portal · Idealista»): tudo o que é próprio dele num só sítio
  (`backend/portals.py`), em vez de espalhado pelo código — quem envia os avisos de pedidos (`reply@idealista.pt`) e os de
  chamadas (`naoresponder@idealista.pt`), como o assunto diz o nome do cliente, o código e o link do anúncio, e os campos
  de um aviso de chamada (telefone, data e hora, estado, duração, anúncio e referência). Se o portal mudar os emails, ou
  para outro portal, muda-se aí; cada regra é conferida antes de guardar (compila, e tem o grupo com o valor a ler), e
  «Repor os de origem» volta atrás. Só se guarda o que difere do de origem (config.json, `portal`).
- **Os avisos de chamadas já se leem** (`rules.parse_call`): quem ligou, a hora da própria chamada (não a do email, que
  pode chegar dias depois), atendida ou não, a duração, e o anúncio e a referência quando vêm. Ainda não entram na
  leitura: é o passo das chamadas, a seguir.

## α.101.1 — 02/10/2026

- **A marca escondida passa a ir selada:** o cabeçalho `X-ARIA` e o Message-ID viajam com o email (vêem-se em «Mostrar
  original»), por isso o que dizem — o lugar na short list, o tipo de email — vai cifrado e assinado com a chave das
  Chaves do Mac: um código ASCII opaco («1.k3f9…»), que só esta ARIA abre e que, alterado, é recusado.
- **Cópias de segurança: nada se apaga, só se acrescenta** (antes ficavam as últimas 14). E, se o «Google Drive para
  computador» estiver instalado, a Oficina mostra «Usar o Google Drive (conta)», que cria a pasta `ARIA-copias` no Drive e
  passa a usá-la. (A palavra-passe do Gmail não dá acesso ao Drive.) «Escolher pasta…» abre a janela de escolha de pastas
  do próprio Mac, para qualquer pasta (o servidor local abre-a; a página não pode).

## α.101.0 — 02/10/2026

- **A marca escondida em cada email que a ARIA envia** (`backend/mark.py`): em ASCII e fora da vista de quem lê, diz o
  imóvel, o nosso n.º de email a esse cliente, o tipo de email (resposta, proposta de visita, agradecimento, pedido de
  documentos, despedida, proprietário…), a visita e a janela que nomeia, e o lugar na short list num pedido de
  documentos. Vai no cabeçalho `X-ARIA` (fica na nossa cópia, nos Enviados) e no Message-ID, que o programa de email do
  cliente copia para a resposta — a resposta diz sozinha a que email nosso responde. Assinada com uma chave criada uma
  vez e guardada nas Chaves do Mac (fora da pasta de dados e das cópias): confere que foi esta ARIA. Sem a chave, o
  email sai na mesma, sem marca. A leitura já guarda o `X-ARIA` dos nossos emails, para a reconstrução a partir do Gmail.

## α.100.0 — 02/10/2026

- **Cópias de segurança** (Oficina → «Cópias de segurança»): a pasta de dados — imóveis, conversas, agenda, contactos,
  conhecimento, voz, proprietários — comprimida uma vez por dia, na primeira leitura, para uma pasta à tua escolha (por
  exemplo, uma que o Google Drive sincroniza); ficam as 14 mais recentes. Nunca as chaves (Gmail, OpenAI) nem os
  ficheiros internos. «Fazer cópia agora» faz mais uma; uma cópia que falha vai para o quadro de avisos e não pára a
  leitura. Para repor, descomprime-se a cópia para a pasta da ARIA.

## α.99.1 — 02/10/2026

- **70's Scooter:** sai a fila de botões R a 6 debaixo do guiador (ganha espaço); no punho preto, ▲ passa à mudança de
  cima e ▼ à de baixo, e o tambor roda até ao número novo. O tambor segue a ordem do menu.
- **Luzes de aviso (80's RacingCar e 70's Scooter):** ao passar o rato (ou com o foco), uma explicação por cima do
  painel — o nome da luz e se está acesa, o que quer dizer, o que lê agora e para onde leva o clique. Sai o título do
  browser, que chegava tarde e só dizia a leitura.
- **90's Boat:** sai a legenda dos sensores debaixo do barco; ao passar o rato num círculo, um tooltip com o sensor, o que
  lê e para onde leva o clique. O leme ganha o 7.º raio, com a bandeira O (Oscar) dos Proprietários, na ordem do menu.

## α.99.0 — 02/10/2026

- **Proprietários: o proprietário define-se no próprio separador** — nome e email, em cima, com «Guardar»; o mesmo email
  em vários imóveis é um proprietário com vários («Também é proprietário de…»). Sem email, um aviso diz que as mensagens
  dele entram como as de um cliente.
- **«Escrever ao proprietário»**, sem ele ter escrito primeiro: um cartão novo (tracejado, «email novo · assunto»), com o
  assunto que escolheres (por defeito, a referência e a descrição do imóvel), escrito à mão ou com «Gerar resposta». Sai
  como um email novo, não como resposta. Em cada cartão, uma caixa opcional «o que lhe queres dizer» segue com o prompt.
- **O ponto de situação também nos Proprietários**, o do imóvel escolhido (continua no Painel): o mesmo bloco de notas,
  o mesmo envio ao proprietário ou para ti.
- **Menu:** Voz e estilo, linha, Painel, Comunicações, Contactos, Visitas, linha, Imóveis e Proprietários. As mudanças
  do 80's RacingCar seguem esta ordem (Proprietários é a 6.ª); a segunda linha tem a tira cromada dos temas ricos, e no
  90's Boat os Proprietários levam a bandeira O (Oscar).

## α.98.0 — 02/10/2026

- **Proprietários: um separador novo, à parte dos clientes.** O proprietário de cada imóvel é o «Email do proprietário»
  do imóvel (o mesmo do ponto de situação). Na leitura, os emails dele vão para uma fila sua (`kind: "owner"`) e a
  conversa para `owner_conversations`: nunca nos cartões das Comunicações, nas rondas, nos contactos, nas fichas nem nos
  números do Painel. O que já tinha entrado como cliente (antes de o email estar no imóvel) passa para o lado dele na
  leitura seguinte ou ao guardar o imóvel.
  - **O separador «Proprietários»** (a 6.ª mudança no 80's RacingCar): o imóvel em cima, um cartão por mensagem — a
    conversa, o rascunho, «Gerar resposta», «Guardar», «Enviar» (com a confirmação do destinatário) e «Não precisa de
    resposta» — e o contador no menu.
  - **O prompt do proprietário** (editável na Oficina, «Respostas ao proprietário»): é o cliente da agência, não um
    interessado; responde com o estado do imóvel (o do ponto de situação), dos interessados só o primeiro nome e o
    ponto em que estão, nunca decide por ele nem promete prazos, e escreve em nota o que ele pediu ou decidiu.
  - **Conhecimento para proprietários**, no fundo do separador (`data/proprietarios/knowledge/`): o tom, o que se
    reporta e o que se decide com eles; só entra nas respostas aos proprietários.
  - No Painel, «A fazer» ganha «Mensagens do proprietário por responder».

## α.97.0 — 02/10/2026

- **Quadro de avisos: o que é importante.** Juntam-se aos avisos do α.96.0:
  - **cliente à espera da nossa resposta há 3 dias ou mais** (`WAITING_NOTICE_HOURS = 72`): um aviso por imóvel e por
    dia, com quantos são e os nomes, depois de cada leitura;
  - **mensagem importante, dramática ou insultuosa**: ao escrever as respostas, a IA assinala-a (`alerta` e
    `alerta_motivo` no formato da resposta, só nesses casos, sem responder a insultos); o cartão mostra o aviso e o
    quadro pede-te para a leres antes de responder e, se for caso disso, pôr o cliente na lista cinzenta ou negra;
  - **um cliente da short list (escolhido, suplente ou short list) escreveu**: urgente, no quadro logo na leitura, e o
    cartão diz para responderes quanto antes.
- **Comunicações: «Encerrar contacto»**, uma pílula azul-ardósia no cartão de um email do cliente: a resposta passa a
  ser uma despedida cordial (o prompt do fecho), escrita logo pela API, que revês e envias. Depois de enviada, o contacto
  fica encerrado — sem rondas de visitas nem lembretes —, mas sem lista cinzenta: se voltar a escrever, entra
  normalmente. O cartão diz «encerrar contacto · despedida».

## α.96.0 — 02/10/2026

- **Painel: quadro de avisos**, por cima de tudo — as mensagens importantes do sistema para ti, da mais recente para a
  mais antiga, com a data e a hora, o imóvel e onde se tratam («Ver →»); as por ler a negrito, e o separador Painel
  mostra quantas são. «Arquivar» tira um aviso do quadro; «Marcar todos como lidos» e «Arquivar todos» tratam de todos.
  Cada aviso aparece uma só vez. Para já, avisam:
  - **a 8.ª interação enviada sem visita marcada**: precisa da tua intervenção (lista cinzenta, propor visita ou deixar
    seguir para o fecho);
  - **o email de fecho enviado** (a 9.ª): deixamos de insistir;
  - **o depósito da API de um imóvel na reserva ou vazio** (uma vez por enchimento);
  - **uma leitura do Gmail que falhou** (uma vez por dia e por erro).
  Ficam em `data/avisos.json` (os últimos 300), fora do Git. Na demonstração, o quadro só se lê.

## α.95.0 — 02/10/2026

- **Da 5.ª interação em diante, em três degraus.** Um cliente que continua a escrever depois da 4.ª sem visita marcada
  (o dia da ronda passou, só pode noutra data, mais uma pergunta) ficava sem prompt («avisa o proprietário») e o
  rascunho vinha vazio. Agora, cada degrau com o seu prompt, comum a todos os imóveis e editável na Oficina:
  - **5.ª a 7.ª:** responde só ao que perguntou, dentro do que sabemos; não propõe visita nem datas por iniciativa
    própria (se quer visitar ou só pode noutra data, diz que vamos ver e põe-no em nota) e aguarda por ti. O cartão
    lembra que, se não fizer sentido continuar, o pões na lista cinzenta.
  - **8.ª, conclusiva** (`CONCLUSIVE_AT = 8`): resume o ponto em que estamos e pergunta se quer continuar, sem pressão,
    e escreve-te em nota que precisa da tua intervenção. O cartão diz «8.ª interação · conclusiva», com o aviso, e
    depois de enviada aparece no Painel, em «A fazer»: decidir (lista cinzenta, propor visita ou deixar seguir para o
    fecho).
  - **9.ª em diante, o fecho** (`CLOSING_FROM = 9`): quase uma despedida — agradece e diz que, quando as condições se
    alterarem, entraremos de novo em contacto, sem perguntas nem proposta; se o cliente pedir claramente para visitar,
    não fecha e avisa em nota. O cartão diz «9.ª interação · fecho»; depois do fecho, as rondas de visitas deixam de o
    incluir («já levou o email de fecho» na linha da ronda). Os lembretes automáticos já paravam depois da proposta.
  - As fases com prompt próprio (visita marcada, já visitou, documentos, inquérito) continuam a valer sobre estes.

## α.94.0 — 02/10/2026

- **Painel → Depósitos: o imóvel de teste também tem o seu depósito, de 3 €**, mostrado no fim e marcado «· TESTE».
  Enquanto não for enchido com outro valor, o limite é 3 € (`FUEL_TEST_EUR`), contado como nos outros desde o
  enchimento do depósito antigo comum; «Encher» propõe 3 € e volta a contar do zero. Com o depósito vazio, a API pára
  no imóvel de teste (clientes de teste, respostas da ARIA, avaliador), como nos outros. O gasto da API no imóvel de
  teste deixa de contar como «sem imóvel» (os pedidos anteriores a 24/09) e passa a ser do seu depósito; continua fora
  do resto do Painel.

## α.93.5 — 02/10/2026

- **Comunicações: «Ler emails» (Caixa de correio) sobe para cima da escolha do imóvel**, na largura toda: uma leitura
  traz os emails de todos os imóveis, seja qual for o escolhido. Só com a API, a coluna que ficava ao lado (a
  importação do ChatGPT) deixa de ocupar espaço.

## α.93.4 — 02/10/2026

- **Comunicações: o primeiro email de um cliente novo não mostra as respostas rápidas** à direita («Agradecer o email…»,
  «Pedir que aguarde…», «Perguntar se mantém o interesse», «…recebeu o email anterior», «…os documentos», «telefone ou
  WhatsApp», «morada e Google Maps»): ainda não há nada nosso a que dar seguimento. O resto do cartão fica igual
  (acrescentar ao conhecimento, «Atualizar resposta», enviar).

## α.93.3 — 02/10/2026

- **Os emails dos clientes de teste vão com o esforço de raciocínio «Nenhum»**, seja qual for o da Oficina: os
  clientes novos («Gerar clientes de teste») e as respostas deles («Avançar o teste») não precisam de mais
  (`TEST_EFFORT` em `testlab.py`; `complete()` aceita o esforço de uma chamada, por cima do da Oficina). As respostas
  da ARIA aos clientes (também no imóvel de teste), as rondas e o avaliador continuam com o esforço escolhido na
  Oficina, e a explicação ao lado da escolha passa a dizê-lo.

## α.93.2 — 02/10/2026

- **O que a IA escreve para o proprietário vem sempre em português de Portugal**, seja qual for a língua do cliente:
  a nota de cada rascunho e a ficha do cliente (o formato da resposta passa a dizê-lo; só o `reply_text` vai na língua
  do cliente), e os erros e o resumo do avaliador (revisor e rondas de teste). Muda no código (`REPLY_FORMAT` e
  `evaluation_prompt`), que não fica guardado nos perfis: vale já para as próximas respostas.

## α.93.1 — 02/10/2026

- **Comunicações: as notas da IA sobre os rascunhos saem do passo 2** para um painel próprio logo abaixo dos passos,
  «Notas da IA sobre os rascunhos», na largura toda e com as notas lado a lado (fica menos alto). Cada nota começa pelo
  nome do cliente, a negrito; o painel só aparece quando há notas e limpa-se ao mudar de imóvel.

## α.93.0 — 02/10/2026

- **Oficina → Testes: «Descarregar as conversas (.txt)»**, ao lado de «Apagar clientes de teste». Um ficheiro de texto
  com a história de cada cliente de teste, por número, para ler com calma (antes de apagar, por exemplo):
  - quem é, quando entrou, como está (ficha, visita marcada, ignorado, inativo, se a história terminou);
  - o perfil escondido, que a ARIA não conhece;
  - a conversa com a ARIA, email a email, com a hora local, marcando o que ainda está por responder;
  - os rascunhos ainda por enviar, a conversa com o consultor (Human contest) e as avaliações, com as notas e os erros.
  As conversas do imóvel de teste sem cliente correspondente vêm no fim. É feito no computador (`api/testlab/transcript`,
  só com `"admin": true`) e guardado pelo browser; nada sai para fora.
- **Comunicações: «Última leitura…» passa para a linha do título «Ler emails», encostada à direita**; a linha do botão
  fica para o progresso da leitura.

## α.92.2 — 02/10/2026

- **Ronda de visitas: uma linha diz quem recebe o convite e quem fica de fora, e porquê**, por baixo da explicação do
  cartão — por exemplo «Agora: 5 recebem o convite · 19 com email por responder nas Comunicações (entram depois de lhes
  responderes) · 2 na lista de ignorados». Conta também quem já tem visita marcada, quem não quer ou só pode noutra
  data, os inativos e quem tem a proposta da ronda ainda por enviar. Os pedidos novos ainda sem resposta (sem conversa
  até à primeira resposta) entram nos «por responder». Vem de `api/visits/candidates`, que passa a devolver estas
  contas em `left_out`.

## α.92.1 — 02/10/2026

- **Visitas: a ronda corre no imóvel escolhido lá em cima.** O cartão «Ronda de visitas» deixa de ter a sua própria
  lista de imóveis (que podia mostrar outro imóvel que não o de cima) e segue as setas do topo; com «Todos os imóveis»
  pede para escolher um, e num imóvel com as visitas fechadas diz que não há ronda.

## α.92.0 — 02/10/2026

- **O revisor só corre quando se pede:** um cartão novo entre o passo 2 e o 3, **«Revisor · opcional — Rever com a
  IA»**, com «Rever os selecionados» (os rascunhos dos emails selecionados). A revisão logo depois de «Gerar
  respostas» passa a vir desligada (liga-se na Oficina, em «Avaliador»), e os cartões só mostram a caixa do revisor
  quando há uma revisão.

## α.91.1 — 02/10/2026

- **No imóvel de teste, os botões de envio ficam verdes** («3 Enviar todos» e «Enviar já este por email»), em todos os
  temas: um envio de teste vê-se logo.

## α.91.0 — 02/10/2026

- **«Ler emails» diz o que está a fazer, à direita do botão, em até três linhas:** «A ligar ao Gmail…», «A ler o email
  37 de 120», «De: Ana Exemplo», «Nova mensagem sobre…», e por fim «A guardar os emails novos…». (Antes ficava «A
  trabalhar…» até ao fim: o servidor atende os pedidos da página um de cada vez, e o do progresso esperava pela
  leitura inteira.)
- **O «Gerar respostas» em lotes passa a correr mesmo ao mesmo tempo:** os lotes que a página envia juntos ficavam em
  fila no servidor. O progresso da leitura e o «Gerar respostas» passam ao lado dessa fila (as gravações continuam a
  esperar a vez).

## α.90.3 — 02/10/2026

- **O aviso «IMÓVEL DE TESTE…» passa para a linha do título das Comunicações, à direita** de «Uma boa resposta começa
  aqui.» (estava numa faixa por cima de tudo).

## α.90.2 — 02/10/2026

- **Os avisos da plataforma de testes começam por «TEST!»** («TEST! Mensagem de teste de … sobre o teu imóvel…»),
  para se distinguirem logo na caixa de correio.

## α.90.1 — 02/10/2026

- **O imóvel de teste em roxo, para nunca se testar num imóvel real por engano:** o seletor de imóvel fica com fundo
  roxo leve quando é ele o escolhido (Comunicações, Visitas, Contactos e Imóveis), e as Comunicações dele ficam todas
  num roxo muito leve, com «IMÓVEL DE TESTE — o que se faz aqui só chega a clientes de teste» no topo. O roxo mistura-se
  com as cores de cada tema.

## α.90.0 — 02/10/2026

- **Esforço de raciocínio «Baixo» por defeito** (Oficina), com Nenhum, Mínimo, Médio, Alto e «O do modelo» à escolha.
- **Saem da escolha do motor os modelos antigos e caros (gpt-4o, gpt-4.1) e os acima de 3 € por 100 interações
  (gpt-6-astra):** continuam na tabela dos preços (as contas antigas ficam certas), com «Esconder» / «Mostrar» para
  cada modelo. O avaliador passa ao gpt-6-sol por defeito, o mais forte dos que ficam.
- **Enquanto «1 Ler emails» trabalha, o «2 Gerar respostas» fica desligado**, e **o botão mostra o que está a ler**:
  «A ligar ao Gmail…», «A ler 37 de 120 · Ana Exemplo · «Nova mensagem…»», «A guardar os emails novos…».
- Testes: os 5 que misturam o dia local com o de UTC são saltados entre a meia-noite e a uma (só aí falhavam).

## α.89.0 — 02/10/2026

- **Esforço de raciocínio (Oficina, por baixo do motor):** não enviávamos nenhum, e um modelo que raciocina (gpt-5.x,
  gpt-6) usava o seu, pensando antes de cada lote — mais lento, e esses tokens pagam-se. Passa a ir **«Nenhum» por
  defeito** (as respostas são curtas e o prompt tem as regras todas), com Mínimo, Baixo, Médio, Alto ou «O do modelo»
  à escolha. Só os modelos que o aceitam o recebem; se a OpenAI o recusar, o pedido repete-se sem ele. Os registos
  guardam os tokens de raciocínio, para se ver a diferença.
- **Testes & Debug: a «Última ronda» da avaliação abre e fecha**, fechada no início.

## α.88.1 — 02/10/2026

- **Oficina, Testes & Debug: os três passos pela ordem em que se fazem, numerados** — 1 o Human contest («1 Guardar»),
  2 os clientes de teste («2 Gerar clientes de teste»), 3 uma ronda («3 Avançar o teste») — e a consola mais legível:
  letra maior, legendas sem maiúsculas espaçadas e mais espaço entre linhas.

## α.88.0 — 02/10/2026

- **«Gerar respostas» mostra os rascunhos à medida que ficam prontos:** a página divide a seleção em lotes (com os
  limites da Oficina), pede até 4 ao mesmo tempo e redesenha os cartões assim que cada lote chega — o último antes do
  primeiro, se for mais rápido —, com «10 de 20 rascunhos prontos…». As operações curtas (a fila, os rascunhos)
  esperam a vez até 10 segundos, em vez de falharem com «já existe uma operação em curso».
- **A assinatura passa a ser posta pelo programa, não pela IA:** a IA escreve até ao fecho («Com os melhores
  cumprimentos,») e a página acrescenta por baixo a assinatura da Voz e estilo, sempre igual (havia respostas sem
  ela); uma cópia que a IA escreva na mesma é tirada antes, para nunca ficar duas vezes. A assinatura pode ter **várias
  linhas** (até 8). Também no texto comum da ronda.
- **O número de cada email («3 / 20») passa para o canto superior esquerdo, a cinzento.**

## α.87.0 — 02/10/2026

- **«Gerar respostas» muito mais rápido com muitos emails:** as chamadas à IA são feitas ao mesmo tempo (até 4), em
  vez de uma a seguir à outra — 20 emails, em 4 chamadas de cerca de 30 segundos, levavam mais de dois minutos; agora
  perto de 40 segundos. Os rascunhos continuam a ser guardados um lote de cada vez. Se uma chamada falhar, as outras
  ficam guardadas e o aviso diz quantas falharam. O revisor faz o mesmo.
- **Cada email das Comunicações mostra no canto a sua posição**, «3 / 20», pela ordem escolhida em «Ordenar».

## α.86.6 — 02/10/2026

- **«Ler emails» deixava de fora os emails chegados entre a meia-noite e a uma da manhã** (hora de Lisboa): pedia ao
  Gmail os emails até ao dia de hoje em UTC, mas o Gmail conta os dias na hora de Lisboa, e os já datados do dia
  seguinte não vinham (20 clientes de teste enviados às 00:14 não entraram). A leitura passa a pedir até ao dia
  seguinte, com um dia de folga; os identificadores de cada email impedem que algum entre duas vezes.

## α.86.5 — 02/10/2026

- **No imóvel de teste, o repouso dos passos 1 e 2 é de 1 minuto** (nos outros, 5), para as rondas de teste andarem
  depressa.
- **O repouso do passo 2 («Gerar respostas») é de cada imóvel:** ao mudar de imóvel, o 2 fica livre se lá ainda não se
  gerou; ao voltar, o repouso continua até acabar. O do passo 1 é o mesmo para todos, porque uma leitura do Gmail traz
  os emails de todos os imóveis de uma vez.

## α.86.4 — 01/10/2026

- **Os passos 1, 2 e 3 das Comunicações estão sempre à vista** (o 2 aparecia e desaparecia conforme a última leitura).
  Só o 1 («Ler emails do Gmail») e o 2 («Gerar respostas») ficam em repouso depois de usados, agora **5 minutos**
  (eram 10), com o aspeto verde de passo feito; o 3 («Enviar todos») segue as aprovações.
- Correção: a mudança anunciada na α.82.1 para o passo 2 nunca tinha sido aplicada.

## α.86.3 — 01/10/2026

- **O cartão já respondido no Gmail deixa de alternar entre cinzento e normal ao fazer scroll:** fica sempre a
  cinzento — a conversa, o cabeçalho e os avisos —, menos o rascunho, onde se escreve, que mantém as cores.

## α.86.2 — 01/10/2026

- **Na conversa de cada email, as nossas mensagens a cinzento e as dos clientes no fundo do tema**: o cinzento (fundo
  e texto) é uma mistura das cores do próprio tema — mais claro num tema claro, mais escuro num escuro —, com o texto
  a pelo menos 4,7:1 de contraste em todos os temas; as dos clientes ficam com o fundo e o texto do tema (antes, todas
  num «papel claro»). A mensagem por responder mantém a sua barra de cor.

## α.86.1 — 30/09/2026

- **Um email já respondido diretamente no Gmail fica em cinzento** e deixa de vir selecionado (não entra no «Enviar
  todos»); continua na fila, para se acrescentar algo, e volta às cores ao passar o rato.
- **Um «acrescento» quase vazio** (menos de 20 caracteres) **sai da fila quando o mesmo cliente volta a escrever**:
  o email novo é a resposta a escrever (um acrescento com «pdf» ficava ao lado dele como um segundo cartão).
- **O revisor não avalia rascunhos com menos de 40 caracteres** («Rascunho demasiado curto para rever») e avalia só o
  texto do rascunho: as mensagens anteriores da conversa são contexto, nunca o que avalia (deu 8,5/10 a «pdf» por
  coisas ditas antes).

## α.86.0 — 30/09/2026

- **O prompt sabe o dia e a hora em que é escrito** («AGORA: quarta-feira, 30/09/2026, 19:05»): o «hoje», o
  «amanhã» e o «ontem» de um cliente contam a partir da data do email dele, os da resposta a partir de agora. (Uma
  resposta escrita a 30/09 dizia «não lhe é possível visitar hoje» do que o cliente escreveu a 29/09.) Também na
  ronda de visitas, no revisor e nos clientes de teste.
- **O know-how da agência dividido entre arrendamentos e vendas**, tratados de forma muito diferente: um comum a
  todos (`data/knowledge/`), um só para arrendamentos (`data/arrendamento/knowledge/`) e um só para vendas
  (`data/venda/knowledge/`). Cada imóvel tem um **«Tipo de negócio»** (Arrendamento ou Venda; sem ele, arrendamento)
  e recebe o comum e o do seu tipo — o do outro tipo nunca lhe chega. Na Voz e estilo, o know-how aparece em três
  blocos; no «Acrescentar ao conhecimento» de cada email há «Todos os arrendamentos» ou «Todos os imóveis à venda».

## α.85.7 — 30/09/2026

- **KW-Area: o logótipo do cérebro com a altura do «ARIA© / AI FOR REAL ESTATE» ao lado** (60 px); crescia até ao
  tamanho da própria imagem.

## α.85.6 — 30/09/2026

- **As bolas da tabela dos clientes 20% maiores** (13 px de diâmetro, eram 11).

## α.85.5 — 30/09/2026

- **«Última leitura: ONTEM, terça-feira, 29/09/26, 18:40.»** — antes do dia, «HOJE», «ONTEM» ou «HÁ N DIAS», pelos
  dias do calendário deste computador.

## α.85.4 — 30/09/2026

- **O seletor do separador Imóveis também ganha o título «IMÓVEL»** à esquerda, a altura e a letra maior dos outros.

## α.85.3 — 30/09/2026

- **O título «IMÓVEL» do seletor passa para a esquerda**, numa linha só dele, como o dos outros cartões.
- **«GMAIL» passa a «CAIXA DE CORREIO»** no cartão «Ler emails».

## α.85.2 — 30/09/2026

- **Painel:** os cartões dos imóveis ganham espaço por cima (os números) e por baixo («A fazer»); estavam colados.

## α.85.1 — 30/09/2026

- **O seletor de imóvel ganha o título «IMÓVEL»**, 15% mais de altura e letra maior (Comunicações, Visitas e
  Contactos).
- **«Ler emails» com menos altura:** a «Última leitura» passa para a linha do botão, à direita.

## α.85.0 — 30/09/2026

- **Avaliador:** um segundo modelo, mais forte do que o que escreve (gpt-4o por defeito, escolhido na Oficina), dá
  nota de 0 a 10 às respostas em seis critérios — factos, perguntas do cliente, qualificação, regras da agência, voz e
  avanço — e aponta os erros concretos, citados.
  - **Revisor dos rascunhos reais:** logo depois de «Gerar respostas» (desligável na Oficina), cada rascunho mostra por
    baixo a nota, uma linha de resumo e os avisos; a revisão só vale para o texto que leu (mudado o texto, diz
    «Revisão de outra versão do texto»); «Rever com a IA» / «Rever outra vez» em cada cartão. Uma revisão que falhe
    nunca perde os rascunhos.
  - **Plataforma de testes:** em cada «Avançar o teste», antes de os clientes responderem, avalia as respostas da ARIA
    e do consultor, sabendo a ficha escondida de cada cliente; a consola mostra as médias por critério lado a lado
    (ARIA e consultor), o tempo de resposta e os erros da última ronda.

## α.84.0 — 30/09/2026

- **Tema novo, «AgentVal»** (id `agentval`), a pedido de uma cliente, no espírito do site da agência dela: página creme
  (`#f8f2ee`), cartões um tom mais claros, tinta antracite, títulos numa serifada clara (Cormorant Garamond quando o
  computador a tem; senão Garamond, Hoefler Text ou Georgia — a página não carrega letras de fora), rótulos em
  maiúsculas bem espaçadas depois de um traço terracota, cantos quase retos (2 px), botões principais antracite com
  maiúsculas creme e os três acentos da paleta: terracota, azulejo e oliva. Barra lateral antracite, com um V de
  linhas paralelas (desenho nosso, à maneira do logótipo) e «AGENTVAL» numa wordmark fina. Os títulos das páginas
  falam num tom mais caloroso («Cada contacto, uma decisão a acompanhar.», «Responder com cuidado, a cada pessoa.»).
  Contrastes verificados (texto 8:1, rótulos 4,8:1, barra lateral 10:1).

## α.83.0 — 30/09/2026

- **Todos os prompts passam para a Oficina** (cartão «Prompts»), para os mudar quando for preciso: os comuns a todos
  os imóveis (comportamento geral, pós-visita e o seu conteúdo base, resposta ao inquérito, lembrete de visita, visita
  marcada, já visitou, visita falhada, lembrete sem resposta, pedido de documentos) e os de cada imóvel (prompt base,
  1.ª a 4.ª interação, texto base da 1.ª, como usar o conhecimento). A resposta ao inquérito, o lembrete sem resposta e
  a visita falhada, que só existiam no código, passam a poder mudar-se. Um texto apagado volta ao de partida.
- **Saem da Voz e estilo e dos Imóveis**; o servidor recusa mudar um prompt sem `"admin": true`.
- **Sem «admin», nenhum prompt se vê** (tinham os dados dos clientes): nas Comunicações, na ronda, na análise e nos
  anúncios ficam só «Criar prompt» e «Copiar»; também as instruções do imóvel e «Ver o que foi enviado à IA».

## α.82.4 — 29/09/2026

- **A legenda das bolas mais curta** (cabe em menos linhas): «Eles (esquerda): incógnito · nada dado · ficha a meio ·
  ficha completa · desistiu / ignorado» e «Nós (direita): em dia · responder em breve · resposta atrasada (+48 h) · sem
  visita há +96 h».

## α.82.3 — 29/09/2026

- **Ao aprovar o último email selecionado, a página sobe até «3 Enviar todos»** (já ligado), que pisca um instante,
  com o aviso «Todos aprovados: carrega em «3 Enviar todos»». Enquanto falta algum, continua a descer para o seguinte.

## α.82.2 — 29/09/2026

- **«Aprovar» passa para o canto superior direito de cada email**, na linha do nome, com a moldura tracejada; o
  aspeto de aprovado (verde, «✓ Aprovado» e «Desfazer») fica igual.

## α.82.1 — 29/09/2026

- **Bolas:** a metade direita fica **verde, «em dia»**, quando já respondemos ou não é preciso responder; **vermelha**
  quando lhe devemos resposta há mais de 48 h (era laranja) — assim, toda verde é mesmo bom e toda vermelha mesmo mau.
  **Metade vazia = incógnito** (ainda não sabemos nada: um pedido novo); quem desistiu ou foi ignorado fica toda preta.
- **«Ordenar»: nova opção «Por nome (A–Z)»**, pelo nome do cliente (ou o email, sem nome), também nos nomes da tabela.
- ~~O passo 2 («Gerar respostas») aparece sempre que há emails na fila~~ — **não chegou a ser aplicado** (o comando
  que o fazia não correu); feito a sério na α.86.4.

## α.82.0 — 29/09/2026

- **Uma bola por cliente, em duas metades** (na tabela dos clientes por fase), porque são duas coisas diferentes: à
  esquerda **o que eles deram** — vermelha (nada ainda), **amarela (parte da ficha)**, verde (ficha completa), **preta
  (desistiu ou foi ignorado: as desistências passam a ter bola)** —; à direita **o que nós temos de fazer** — laranja
  (devemos-lhe resposta há mais de 48 h), **âmbar (devemos-lhe resposta, há pouco tempo)**, azul (ficha completa há
  mais de 96 h e sem data de visita), vazia (nada a fazer). A legenda, por baixo da tabela, explica as duas metades.
- **«Última leitura…»** alinhada à direita do painel.

## α.81.0 — 29/09/2026

- **O passo de envio passa a «3 Enviar todos»:** cada rascunho tem sempre, por baixo, «Aprovar» (lê-se e corrige-se
  no próprio cartão, com a conversa toda); o botão mostra «Enviar todos (2 de 5 aprovados)» e só se liga com os
  selecionados todos aprovados; mudar um texto depois de aprovado tira-lhe a aprovação. Continua a mostrar os
  destinatários antes de enviar e confirma que nada mudou desde a aprovação. Sai o passo intermédio de revisão.
- **Tabela dos clientes por fase:** saem os textos ao passar o rato por cima das bolas e dos nomes (o nome fica só como
  ligação ao cartão); **a legenda das bolas passa para baixo da tabela, à direita**.
- **«Última leitura»** com o dia da semana, maior e a negrito.

## α.80.0 — 29/09/2026

- **Limites de cada chamada à IA (Oficina):** «não ultrapassar X% do contexto do modelo» (50% por defeito) e «no
  máximo N emails por chamada» (5, como antes). «Gerar respostas» estima o tamanho de cada prompt antes de o enviar e
  junta emails na mesma chamada só enquanto couberem nos dois; se não, faz mais chamadas. O aviso no fim diz quantas
  chamadas houve e quanto do contexto a maior usou.
- **Contexto de cada modelo**, em tokens, numa coluna nova da tabela dos preços: os que se conhecem já preenchidos
  (gpt-4o e 4o-mini 128.000, gpt-4.1 1.047.576); os outros «por confirmar», a valer 128.000 até se indicar.
- Medido com os dados de hoje: as instruções (voz, know-how, conhecimento do imóvel e prompts) andam pelos 7.400
  tokens e cada email com o seu histórico até 2.400; um lote de 5 anda pelos 15% de 128.000. O histórico cresce (até
  20 mensagens de 4.000 caracteres por cliente): no pior caso, 5 conversas longas passariam o contexto do gpt-4o — é
  isso que os limites evitam.

## α.79.0 — 29/09/2026

- **«3 Rever para Enviar Todos» faz a revisão nos próprios cartões:** sai a lista que repetia os textos todos. Cada
  email selecionado ganha, por baixo do rascunho, **«Aprovar»** — lê-se com a conversa toda à vista e os botões de
  sempre; aprovar guarda o texto da caixa. Mudar o texto depois tira a aprovação («Alterado: aprova outra vez»). Ao
  lado do «3» ficam a contagem («2 de 5 aprovado(s)»), **«Enviar todos (N)»**, que só se liga com todos aprovados, e
  «Cancelar revisão». O envio confirma que nada mudou depois de aprovado.

## α.78.5 — 29/09/2026

- **As respostas deixam de contradizer o que já dissemos ao cliente:** uma regra nova diz à IA que o que nós já
  escrevemos a um cliente foi decidido pelo proprietário e vale mesmo que o conhecimento do imóvel diga outra coisa (é
  uma exceção para esse cliente), e que nunca volte a perguntar o que o cliente já respondeu. (Um rascunho voltava a
  dizer «no máximo 4 pessoas» e «2 anos, sem renovação» a quem já tinha ouvido que 5 e 1 ano serviam.)
- **O histórico vai para a IA pela ordem em que as coisas aconteceram** (um email do cliente lido tarde ficava depois
  do nosso seguinte) **e inteiro** (cada mensagem era cortada aos 1.000 caracteres; agora 4.000, o que se guarda).

## α.78.4 — 29/09/2026

- **Os mostradores da qualidade (inquéritos pós-visita) 20% maiores** no Painel.

## α.78.3 — 29/09/2026

- **O imóvel de teste nunca conta no Painel:** nem o cartão dele, nem os pedidos, as respostas enviadas, o tempo de
  resposta, o gráfico e o inquérito, nem o ponto de situação (e o envio do resumo de todos) e o «A fazer». Continua a
  não contar depois de apagar os clientes de teste, ou o próprio imóvel: a referência e os identificadores das
  mensagens ficam guardados na plataforma de testes. O custo da API continua a contar no gasto total, porque foi
  dinheiro gasto.

## α.78.2 — 29/09/2026

- **Os clientes de teste nunca respondem ao inquérito pós-visita**, para nenhuma nota de teste entrar nas médias do
  inquérito: o «Avançar o teste» salta a conversa cujo último email nosso é o agradecimento com o inquérito.

## α.78.1 — 29/09/2026

- **Consola de testes mais legível:** letras mais brancas (texto, legendas, endereços e o que se escreve nos campos).
  Saem um «null» e um «0» que apareciam como texto quando ainda não havia registo nem clientes.

## α.78.0 — 29/09/2026

- **«▶ Avançar o teste»** (Oficina, uma ronda por clique): cada cliente de teste com um email nosso por responder
  responde na pele da personagem dele — ou fica calado nesta ronda —, numa só chamada à IA: responde a tudo ou só a
  parte, faz perguntas novas sobre o imóvel, revela os segredos só se lhe perguntarem, escolhe a hora da visita ou pede
  outra data, desiste, conforme o feitio e o destino da ficha. A resposta sai pelo Gmail na conversa certa
  (In-Reply-To do nosso último email) e «Ler emails» trá-la como a interação seguinte.
- **Human contest:** na mesma ronda, o cliente responde também ao consultor, na conversa dele: a página lê no Gmail os
  emails do consultor para os endereços `+cdN` e o cliente responde-lhes em separado, com a mesma personagem.
- Cada email nosso (e do consultor) tem uma só ronda de resposta; uma história que acabou («terminou») não volta a
  responder. Entram os clientes novos da percentagem definida. Um registo das rondas fica no painel.
- **Oficina:** a ordem passa a Motor de IA, **Testes & Debug** (a consola de testes, dentro do seu cartão) e Preços dos
  tokens.

## α.77.2 — 29/09/2026

- **A plataforma de testes com cara de laboratório de IA**, igual em todos os temas: fundo preto com grelha de circuito,
  néon ciano e magenta, letra monoespaçada, linhas de monitor antigo e um brilho a varrer, uma borda de luz a dar a
  volta ao painel, cursor a piscar no título, «⚡ Gerar clientes de teste» em gradiente e a lista dos clientes como um
  registo de terminal. Com «reduzir movimento», fica tudo parado.

## α.77.1 — 29/09/2026

- **Plataforma de testes em duas linhas:** «Clientes novos», «Clientes novos por ronda (%)» e «Gerar clientes de teste»
  numa; o Human contest, o email do consultor e «Guardar» na de baixo.

## α.77.0 — 29/09/2026

- **Plataforma de testes (Oficina):**
  - **«Clientes novos por ronda (%)»**, 10% por defeito, editável (para o «Avançar o teste»);
  - **«Apagar clientes de teste»**: o imóvel de teste começa de novo — fila, conversas, agenda e contactos, e a lista
    dos clientes. Os emails ficam no Gmail, mas a página guarda os seus identificadores e nunca mais os lê; os
    clientes novos nunca repetem um endereço `+cdN` já usado.

## α.76.3 — 29/09/2026

- **«3 Preparar envios dos selecionados» passa a «3 Rever para Enviar Todos»**, e o «Enviar N email(s)» e o
  «Cancelar» ficam ao lado dele, em vez de no fim da lista dos emails a rever (que continua por baixo).

## α.76.2 — 29/09/2026

- **«1 Ler emails» e «2 Gerar respostas», depois de usados, parecem um passo feito e não um botão desligado:** verdes,
  com «✓ Emails lidos» e «✓ Respostas geradas», durante os 10 minutos de repouso (que continuam, para não repetir a
  leitura nem pagar duas vezes o mesmo lote); a hora a que voltam fica no título, ao passar o rato.

## α.76.1 — 29/09/2026

- **Human contest:** «Gerar clientes de teste» guarda primeiro o interruptor e o email do consultor tal como estão no
  ecrã (sem «Guardar», as cópias não saíam). Botão novo, **«Enviar ao consultor os que faltam»**, para os clientes já
  criados sem cópia; na lista, cada cliente diz se o consultor já recebeu a dele.

## α.76.0 — 29/09/2026

- **Oficina**, um espaço à parte para quem afina a ARIA, com um link no fundo da barra lateral que só aparece com
  `"admin": true` no `config.json` (quem usa a página no dia a dia não a vê):
  - **o motor de IA** sai da Voz e estilo e passa para aqui;
  - **preços dos tokens** editáveis, em dólares por 1M tokens: mudar o de um modelo, repor o da tabela, ou acrescentar
    um modelo novo, que passa a poder escolher-se no motor; valem para todas as estimativas (custo de cada chamada,
    depósitos, «/ 100 interações»);
  - **plataforma de testes**: «Gerar clientes de teste» inventa com a IA N clientes fictícios do imóvel de teste (um
    `profile.json` com `"test": true`), cada um com uma personagem escondida, e envia de verdade o aviso de cada um pelo
    Gmail, desta conta para ela própria, com o cliente no Reply-To (um endereço `+cdN` da conta) e a marca
    `X-ARIA-Teste`; «Ler emails» trá-los como avisos do portal. **Human contest**: ligado, cada aviso vai também, numa
    cópia à parte, para o email de um consultor, que responde à mão lado a lado.
- **Leitura:** um email da própria conta com a marca de teste lê-se como aviso ou resposta de cliente, só no imóvel de
  teste (o cliente vem do Reply-To); um imóvel real nunca o aceita. O nome no assunto ignora o «teste de».

## α.75.2 — 29/09/2026

- **Aviso enquanto os emails saem:** durante qualquer envio (um email, um lote ou a ronda), fica no topo da página uma
  faixa com um envelope a voar — «A enviar emails… Não feches esta janela, o browser nem o portátil até terminar» — e
  o browser pede confirmação se se tentar fechar ou recarregar a página. Some quando o envio acaba.

## α.75.1 — 29/09/2026

- **«Mais recentes» nas Comunicações conta a mensagem do cliente** que o cartão responde (e as que se juntaram a ela),
  não os nossos envios: uma ronda ou um lote enviados com segundos de diferença baralhavam a ordem.

## α.75.0 — 29/09/2026

- **«Ordenar» nas Comunicações:** mais recentes primeiro (o normal), mais antigos primeiro, primeiras fases primeiro ou
  últimas fases primeiro (pela coluna do cliente na tabela; dentro da mesma fase, os mais recentes primeiro). A escolha
  fica guardada neste browser, e os nomes em cada coluna da tabela seguem-na (mais recentes ou mais antigos primeiro).
- **Um empate na última interação** (o mesmo email nosso a vários clientes, como uma ronda) decide-se pela data do
  próprio email, em vez de voltar à ordem da fila.

## α.74.3 — 29/09/2026

- **Na tabela dos clientes por fase, no máximo 10 nomes por coluna** (os mais recentes); a partir daí, uma só linha
  com «+ N casos», sem os listar. O número no título continua a ser o total.

## α.74.2 — 29/09/2026

- **Nas Comunicações, os emails mais recentes primeiro:** cada cartão ordena-se pela interação mais recente da conversa,
  lida ou enviada (o email em si, os que se juntaram a ele e o histórico). Os «Enviados · clientes ativos» já vinham
  pelo último envio.

## α.74.1 — 29/09/2026

- **Sem guardar automático, afinal:** no canto de cima do rascunho de cada email ficam dois ícones pequenos, copiar e
  uma disquete para guardar, só para quando se quer mesmo guardar um texto sem o enviar; a disquete acende enquanto a
  caixa tem alterações por guardar. «Enviar já este por email» continua a enviar (e guardar) o que está na caixa.

## α.74.0 — 29/09/2026

- **Sai o «Guardar rascunho» e o aviso «Por guardar» de cada email:** o rascunho guarda-se sozinho, um segundo depois
  de se parar de escrever e ao sair da caixa, sem redesenhar a página (o cursor fica onde estava). Um clique logo a
  seguir a escrever (Atualizar resposta, enviar) espera que o texto esteja guardado; um rascunho novo da IA nunca é
  apagado pelo texto antigo da caixa. Se não conseguir guardar, diz porquê.

## α.73.5 — 29/09/2026

- **As setas da hora e dos minutos ficam as duas à direita do campo**, a da hora primeiro, pela ordem em que se lê.

## α.73.4 — 29/09/2026

- **As horas das visitas mais estreitas**, e **a hora de fim acompanha a de início**, mantendo o intervalo escolhido
  (também depois de se mudar a hora de fim). O dia vem preenchido com hoje e mostra sempre o dia da semana.

## α.73.3 — 29/09/2026

- **Ronda de visitas, os passos lado a lado:** «1 Preparar o texto da ronda», «Guardar alterações» e «2 Enviar a todos»
  ficam na mesma linha; o rascunho da ronda (dia, conhecimento, textos e saudações) aparece logo por baixo, antes da
  lista de quem recebeu a última ronda.

## α.73.2 — 29/09/2026

- **Ronda de visitas: primeiro o rascunho, depois o envio.** Com o texto comum, o botão passa a dizer «Preparar o texto
  da ronda», já não pergunta «Vais avisar N clientes» (não envia nada) e escreve logo o rascunho via API, que aparece no
  fim do painel para rever; só «Enviar a todos», lá, envia. Sem API, fica o copiar/colar. Individualizada, continua
  «Iniciar ronda», com um aviso que diz que nada é enviado antes de rever.

## α.73.1 — 29/09/2026

- **Mais duas fases na tabela dos clientes:** **«Pronto para visita»** (ficha completa e ainda sem proposta: os clientes
  a convidar na próxima ronda), entre «Em qualificação» e «Proposta de visita», e **«Hora por confirmar»** (aceitou ou
  pediu uma hora que ainda não confirmámos na agenda), antes de «Visita marcada».

## α.73.0 — 29/09/2026

- **A tabela dos clientes nas Comunicações passa a ser por fase**, não pelo número de emails trocados: as colunas «1.ª»,
  «2.ª», «3.ª» e «Mais de 3» dão lugar a **«Em qualificação»** (já lhe respondemos e ainda estamos a recolher os dados
  da ficha) e **«Proposta de visita»** (já recebeu uma proposta, numa ronda ou na conversa, e ainda não tem hora
  marcada). As outras colunas ficam como estavam.
- **O dia da semana fica na mesma linha da data**, em três letras (Ter).

## α.72.2 — 29/09/2026

- **Dia e horas das visitas com setas** (na ronda de visitas e nas Visitas de cada imóvel): ◀ ▶ mudam o dia (nunca para
  antes de hoje), e cada hora tem ▲ ▼ para a hora e para os minutos (de marcação em marcação, 30 em 30 por defeito).
  Escrever continua a funcionar. **O dia mostra sempre o dia da semana** por baixo. Nos temas ricos, as setas ficam com
  o seu desenho, fora do dos botões do tema.

## α.72.1 — 29/09/2026

- **80's RacingCar, 90's Boat e 70's Scooter: o veículo deixa de passar no cabeçalho**, passa só no rodapé. A regra fica
  em comentário no tema, para um dia voltar.

## α.72.0 — 29/09/2026

- **Ronda de visitas com um só texto para todos**, revisto e enviado no próprio painel da ronda (Agenda), sem encher as
  Comunicações com um cartão por cliente:
  - **«Conhecimento desta ronda»**: o que os emails desta ronda devem dizer (que o inquilino ainda lá está, onde
    estacionar, quanto dura a visita…); vai para a IA só nesta ronda, também nas respostas individualizadas;
  - **«Gerar o texto comum»** (ou copiar o prompt e colar a resposta do ChatGPT): uma só chamada à IA escreve o texto em
    português (sempre pt-PT, também para brasileiros) e em inglês, a saudação de cada cliente e, para quem escreve
    noutra língua, um resumo curto nela, a seguir ao inglês, que é o texto completo e oficial;
  - revês e alteras os textos e as saudações ali mesmo; **«Enviar a todos»** envia a cada cliente o seu, na conversa
    dele, depois de confirmares;
  - **«Individualizar»**: na ronda inteira (antes de a iniciar) ou num cliente, que passa para as Comunicações para
    lhe responderes à parte.

## α.71.2 — 29/09/2026

- **Empresa: só se fala nisso quando o cliente fala primeiro, mesmo que só o dê a entender** (por exemplo, colegas da
  mesma empresa a morar na casa, ou um gerente da sua própria empresa). Então pergunta-se se o arrendamento fica em
  nome da empresa e qual; se não, nunca se fala em empresa. A regra passa a estar no know-how comum a todos os imóveis,
  e sai dos prompts de cada imóvel a pergunta pela empresa. Na ficha do cliente, a empresa conta também quando o cliente
  só a deu a entender.

## α.71.1 — 29/09/2026

- **O mapa e o contacto de quem faz a visita vão sempre juntos, a quem já tem uma hora de visita marcada** (mesmo que
  ainda não a tenha confirmado): na confirmação da hora, no lembrete de visita e na resposta a um cliente com a visita
  marcada que pergunte onde fica. O contacto vai no corpo do email, logo a seguir à morada — «é a pessoa que vai fazer a
  visita consigo», com o nome e o telefone, sem cargo nem título —, e já não depois da assinatura. Antes de haver hora
  marcada, nenhum dos dois.

## α.71.0 — 28/09/2026

- **O que foi feito no tema Default passa para os outros temas** (Noite, Dia, Índigo, 80's RacingCar, 90's Boat, 70's
  Scooter, KW-Area e APalace):
  - nos temas ricos, o desenho próprio dos botões deixa em paz as pills de cada email, as respostas rápidas, os ícones
    de copiar e os nomes da tabela de clientes, que têm o seu (antes ficavam com o aspeto dos interruptores do tema e
    perdiam as cores);
  - «Enviar por WhatsApp» e «Enviar por SMS / iMessage» ficam com metade da altura também nos temas ricos;
  - o ponto de situação e o bloco de notas são um só cartão do tema (sem moldura dupla nem costuras a mais no
    RacingCar);
  - no 90's Boat e no 70's Scooter, «Enviar já este por email» fica só com o seu envelope (o tema juntava-lhe outra
    marca).
- **As cores do gráfico da atividade, tema a tema, validadas** (claridade, saturação, separação para daltónicos e
  contraste com o fundo): Noite, Dia e Índigo ganham um par que se distingue bem; no RacingCar passam a vermelho e
  azul (amarelo e laranja não se distinguiam para um daltónico), também no painel de cada imóvel; no Scooter, vermelho
  e verde (o laranja era demasiado parecido com o vermelho); no KW-Area e no APalace, um azul em vez do cinzento. As
  barras, a legenda e as caixas do gráfico usam sempre o mesmo par.

## α.70.0 — 28/09/2026

- **Respostas rápidas: nova opção «Ignorar os emails anteriores»**, a última, um pouco afastada e só clicável com uma ou
  mais das outras ligadas. Ligada, «Atualizar resposta» escreve só com os pontos marcados (uma resposta curta, com a
  saudação, o fecho e a assinatura da voz), sem seguir o prompt da interação nem responder ao que veio antes; desligar
  todas as outras desliga-a também. Sem ela, os pontos continuam a somar-se à resposta.
- **«Não precisa de resposta» passa a letra branca** no fundo amarelo torrado.

## α.69.3 — 27/09/2026

- **A pill «Retirar da fila» passa a dizer «Não precisa de resposta»**, com fundo amarelo torrado (letra escura, para se
  ler); a confirmação e o aviso dizem o mesmo. Faz o mesmo de antes: tira só este email da fila, sem resposta.

## α.69.2 — 27/09/2026

- **«Enviar por WhatsApp» e «Enviar por SMS / iMessage» ficam com metade da altura** dos outros botões, com o ícone
  mais pequeno.

## α.69.1 — 27/09/2026

- **Avisos do Idealista sem Reply-To, ou com o endereço do próprio Idealista no Reply-To: usa-se o email do cliente que
  vem no aviso, sem aviso nenhum** (é comum no Idealista). Sai a nota «Sem Reply-To: o destinatário é o email do corpo
  do aviso», também dos emails já na fila, e os que estavam bloqueados por um Reply-To do portal ficam resolvidos na
  leitura seguinte.
- **Um aviso sem email do cliente, mas com telefone, continua a poder ter resposta:** «Atualizar resposta» escreve-a
  (curta, para WhatsApp ou SMS) e o cartão mostra «Enviar por WhatsApp» e «Enviar por SMS / iMessage»; por email
  continua a não poder sair, e o aviso do cartão di-lo.

## α.69.0 — 27/09/2026

- **Um prompt próprio para quem escreve com a visita marcada, e outro para quem já visitou.** Estes emails iam à IA
  como «5.ª interação» ou seguintes, para as quais não há prompt, e a resposta saía do histórico. Passam a ir marcados
  «visita marcada» (com o dia e a hora da visita) ou «já visitou», cada um com as suas instruções, e o cartão mostra essa
  etiqueta em vez de «5.ª interação». Os dois textos editam-se em **Voz e estilo**, na secção nova «Visita marcada e
  depois da visita».
- **O pedido de documentos diz o que o dono diz:** que gostaríamos de passar à próxima fase de análise da candidatura
  e que, para isso, pedimos a documentação — nunca «short list» nem «escolhido». Também passa a editar-se em Voz e
  estilo. (O email já existia: em Visitas, «Pedir documentos» no cartão de cada candidato da short list.)
- **Mais uma resposta rápida: «Perguntar se recebeu o email anterior»** (não tivemos resposta e pode ter ido para o
  spam ou o lixo).
- **As pills de cada email ganham cor:** «Retirar da fila» a verde e «Não tem interesse» a vermelho, com letra branca.

## α.68.1 — 27/09/2026

- **A pill «Ignorar sempre / Blacklist» passa a ter fundo cinzento-escuro**, com letra branca (mais escuro ao passar o
  rato).

## α.68.0 — 27/09/2026

- **Comunicações: os passos por ordem.** O PASSO 02 («Gerar respostas») só aparece depois de «1 Ler emails do Gmail»,
  e o PASSO 03 («Rever e enviar») depois de «2 Gerar respostas». **Os botões 1 e 2 descansam 10 minutos depois de
  carregados** (desligados, com o hover a dizer a que horas voltam), para não se ler nem gerar o mesmo lote duas vezes.
- **«Guardar rascunho · Por guardar» só aparece depois de mudares o texto do rascunho:** a comparação ignora agora as
  diferenças de mudança de linha e os espaços no fim, que a própria caixa de texto pode introduzir.
- Para não ficar preso: ao recarregar a página nesses 10 minutos, os passos continuam à vista (a hora da leitura vem
  do servidor; a do lote gerado fica neste browser); e o PASSO 03 aparece também quando já há rascunhos prontos na fila
  (feitos por «Atualizar resposta», colados do ChatGPT ou de antes), sem obrigar a gerar outra vez.

## α.67.1 — 27/09/2026

- **As respostas rápidas e as instruções extra somam-se à resposta, não a substituem:** o prompt diz agora que cada
  resposta continua a fazer o que a sua interação pede, com a saudação e o fecho da voz, e integra os pontos extra no
  parágrafo a que pertencem, em poucas palavras, sem a tornar mais longa do que precisa (uma resposta real veio só com
  as frases das respostas rápidas, seguidas). No email, «Só para esta resposta» manda os pontos um por linha.
- **«Resposta API · modelo» deixa de ser uma linha por cima do botão:** fica só «API · GPT-4O-MINI», 30% mais pequeno,
  no canto direito do botão «Atualizar resposta».
- **O gasto da última geração passa para dentro do botão «Atualizar resposta»**, em letra pequena por baixo do nome
  («Última: 6 764 tokens · < 0,01 €»), sem o botão crescer.
- **As respostas vêm em parágrafos:** o formato pede saudação, parágrafos curtos separados por uma linha em branco, fecho
  e assinatura, nunca um bloco de frases seguidas.

## α.67.0 — 27/09/2026

- **Por baixo do nome de cada cliente: o email, o telefone e o perfil no Idealista.** O telefone é o do aviso do portal,
  o do `contactos.csv` ou um que o cliente escreveu; o email e o telefone têm cada um o ícone de copiar.
- **A leitura passa a guardar o link «Ver perfil» dos avisos do Idealista** (perdia-se ao passar o email a texto): fica
  no email e numa coluna nova do `contactos.csv`, «perfil», e aparece como «Perfil no Idealista ↗» também nas respostas
  seguintes desse cliente. Só para os avisos lidos daqui em diante; só ligações https.
- **«Enviar por SMS / iMessage»**, a seguir a «Enviar por WhatsApp», também só com texto no rascunho: abre as
  Mensagens do Mac para o número do cliente com o rascunho escrito, e envias tu, lá. Sem telemóvel, fica desligado.
- **Mais quatro respostas rápidas:** «Perguntar se mantém o interesse», «Confirmar que recebemos os documentos», «Propor
  falar por telefone ou WhatsApp» (e a melhor hora) e «Enviar a morada e o link do Google Maps» (os da base de
  conhecimento; se lá não estiverem, a IA não os inventa e diz em nota que faltam).

## α.66.1 — 27/09/2026

- **«Enviar por WhatsApp» vai também buscar o número que o cliente escreveu numa mensagem sua** (esta ou uma anterior,
  nunca o texto nosso citado), quando o aviso do portal e o `contactos.csv` não o têm: um telemóvel português, com ou
  sem +351, ou um número com o indicativo do país (+… ou 00…). Datas, preços e referências não contam. Só para o botão:
  não vai para a IA nem fica gravado.

## α.66.0 — 27/09/2026

- **Respostas rápidas em cada email**, por cima de «+ Acrescentar ao conhecimento»: **«Agradecer o email e as
  informações»** e **«Pedir que aguarde uns dias»** (para passarmos à próxima fase). São interruptores, e podem ligar-se
  vários: cada um ligado escreve a sua frase na caixa do conhecimento (que parte como «Só para esta resposta»), e
  desligá-lo tira-a; «Atualizar resposta» usa-as. O hover de cada um mostra a frase que escreve.

## α.65.1 — 27/09/2026

- **Em cada email, o painel de ações alinha pelo fundo do cartão** (acaba com ele, ao lado do rascunho), em vez de
  ficar alinhado pelo topo.
- **Quando «Atualizar resposta» não traz rascunho, o aviso mostra a nota em que a IA explica porquê** (antes dizia só
  «A API não devolveu um rascunho para este email.» e a nota perdia-se).
- **Os botões com número ou ícone voltam a tê-lo depois de carregados** (ficava «1Ler emails do Gmail», sem a
  bolinha: o botão guardava só o texto enquanto dizia «A trabalhar…»).
- **A etiqueta «Resposta · API · modelo» de cada email já traz o nome do modelo desde a abertura da página** (os
  cartões desenhavam-se antes de chegarem as definições, e ficava «API ·» sem modelo).

## α.65.0 — 27/09/2026

- **Em cada email, «+ Acrescentar ao conhecimento» passa a ter «Só para esta resposta» como opção de partida** (a
  primeira da lista): o que se escreve ali só vai para essa resposta e nada fica gravado no conhecimento, a não ser que
  se escolha «Só este imóvel» ou «Todos os imóveis (agência)».
- **As respostas ao inquérito pós-visita lidas antes de 26/09 ficam marcadas como tal na leitura seguinte**, e passam a
  ter o seu prompt («Resposta ao inquérito»). Até aqui iam à IA como uma interação normal (por exemplo, a 8.ª), para a
  qual não há prompt.

## α.64.9 — 27/09/2026

- **Em cada email, um pequeno ícone de copiar:** ao lado do email do cliente (copia o endereço) e em cada mensagem da
  conversa, ao lado da data (copia o texto dessa mensagem).

## α.64.8 — 27/09/2026

- **Comunicações: o PASSO 03 «Rever e enviar» passa a ser um cartão igual ao PASSO 02**, com as mesmas letras (título,
  texto e etiqueta), e **os botões 2 e 3 ficam à mesma altura**: os dois cartões partilham a grelha da linha.
- **O fundo dos textos das conversas em cada email fica um pouco mais claro** (#fbf8f2, era #f7f3ea).

## α.64.7 — 27/09/2026

- **Os ícones dos botões de cada email ficam duas vezes maiores** (32 px), e **os números 1, 2 e 3** de «Ler emails do
  Gmail», «Gerar respostas» e «Preparar envios dos selecionados» também crescem (30 px).

## α.64.6 — 27/09/2026

- **Comunicações: a escolha do imóvel sai do cartão «Ler emails» e fica antes, à parte**, como nos outros separadores.
  **No cartão ficam o título, a última leitura e, por baixo, o botão «1 Ler emails do Gmail»**, como nos passos 2 e 3.

## α.64.5 — 27/09/2026

- **Os botões de cada email ganham um ícone:** setas em círculo em «Atualizar resposta», um envelope em «Enviar já este
  por email» e um balão de conversa em «Enviar por WhatsApp».

## α.64.4 — 27/09/2026

- **Em cada email, sai a linha «Vai com «Atualizar resposta».»** por baixo de «+ Acrescentar ao conhecimento»: é
  sempre assim.

## α.64.3 — 27/09/2026

- **Voz e estilo, a consola da IA: o fundo passa a ser o do tema** (era uma grelha azul-escura); o título, o estado e a
  nota por baixo usam as cores do tema. **As caixas de dentro (um botão por modelo e os mostradores do cálculo) mantêm
  o fundo escuro, 10% mais claro.**

## α.64.2 — 27/09/2026

- **Em cada email, os botões mudam de nome:** «Gerar esta resposta» passa a **«Atualizar resposta»** e «Enviar
  individual» a **«Enviar já este por email»**.
- **«Enviar por WhatsApp»** (era «Abrir no WhatsApp») aparece ao lado, também só quando há texto no rascunho: abre o
  WhatsApp do Mac na conversa do cliente com o rascunho escrito, e envias tu, lá. Sem telemóvel do cliente, fica à vista
  mas desligado, e o hover diz porquê (antes nem aparecia).

## α.64.1 — 27/09/2026

- **Em cada email, «+ Acrescentar ao conhecimento» ganha a opção «Só para esta resposta»**, ao lado de «Só este imóvel»
  (a de partida) e «Todos os imóveis (agência)».
- **Sai «Guardar no conhecimento» dos emails: vai com «Gerar esta resposta».** Com texto escrito, o botão guarda-o
  primeiro no conhecimento (do imóvel ou da agência) e depois gera; com «Só para esta resposta», não guarda nada e
  junta-o às instruções só desta resposta. O aviso diz onde ficou. Num email bloqueado, sem «Gerar esta resposta», o
  botão de guardar continua lá; em Imóveis também.

## α.64.0 — 27/09/2026

- **Comunicações: o PASSO 02 («Gerar respostas») passa para baixo de «Emails em tratamento», lado a lado com «Rever e
  enviar».** «Ler emails» fica sozinho em cima, a toda a largura.
- **Os três botões que se carregam por ordem têm o número:** 1 «Ler emails do Gmail», 2 «Gerar respostas» e 3
  **«Preparar envios dos selecionados»** (era «Pré-visualizar envio dos selecionados»).
- **Sai a linha tracejada por cima de «Gerar respostas»**, e o botão sobe.

## α.63.1 — 27/09/2026

- **Painel: o calendário do cabeçalho fica 30% mais largo e 10% mais alto.**
- **«Resumo da atividade»: «O ritmo dos teus contactos» deixa de ocupar uma linha** e passa para a direita, ao lado do
  período.

## α.63.0 — 27/09/2026

- **Painel: os imóveis passam para cima, logo antes de «A fazer»**, sem o título «POR IMÓVEL · A tua carteira».
- **«Última leitura … · conta …» sobe para o cabeçalho**, por baixo de «Contactos, respostas e imóveis. Tudo no mesmo
  lugar.», numa linha à parte na cor de destaque do tema.
- **Ponto de situação e bloco de notas num só painel.** Saem os separadores do bloco de notas: clicar num imóvel da
  lista do ponto de situação (ou Enter, com o teclado) abre a página dele no bloco de notas, ao lado; o imóvel escolhido
  fica marcado, e a referência aparece por cima do bloco («PARA O PROPRIETÁRIO · REF»).
- **Depósitos: sai o título «Um depósito de tokens por imóvel»** (fica «DEPÓSITOS · API OPENAI»).

## α.62.1 — 27/09/2026

- **Painel, Depósitos: o gasto total de todos os imóveis passa a ser um mostrador de automóvel**, igual aos dos
  depósitos (era uma carteira e destoava): à esquerda, com a agulha azul, desde sempre; à direita, com a agulha
  vermelha, o último mês; os dois na mesma escala, em euros. Os pedidos e os tokens de cada um estão no hover de cada
  metade.
- **Os custos da API arredondam ao cêntimo, mais não** (eram até 4 casas): no mostrador, nos depósitos, na «Última
  geração» de cada email e no lote; um valor abaixo de meio cêntimo diz «< 0,01 €».

## α.62.0 — 27/09/2026

- **Painel: «Depósitos · API OpenAI» passa para antes do «Resumo da atividade».**
- **«Resumo da atividade» redesenhado.** Por cima do gráfico, três números do período: **pedidos recebidos** (com a
  média por dia), **respostas enviadas** (com o tempo médio até resposta) e o **dia (ou período) com mais pedidos**; as
  cores ao lado dos dois primeiros são a legenda. O gráfico ganha um eixo com valores redondos e linhas de grelha finas,
  colunas aos pares com o topo arredondado, o valor do dia com mais pedidos escrito por cima, e, ao passar o rato (ou
  com o teclado), uma faixa no dia e uma caixa com os dois valores. No tema Default, as respostas passam a verde-azulado
  (#00917f; o cinzento-verde de antes lia-se como cinzento), com as duas cores validadas para daltonismo e contraste. O
  gráfico de cada imóvel, em Imóveis, ganha o mesmo desenho.

## α.61.6 — 27/09/2026

- **Painel, Qualidade: sai a linha «Continua interessado: sim · talvez · não… O detalhe de cada imóvel está em
  Imóveis.»** por baixo dos mostradores.

## α.61.5 — 27/09/2026

- **Greylist e Blacklist, por baixo da tabela dos clientes: o motivo aparece a seguir ao nome**, quando há um (por
  exemplo «Cliente disse que não tem interesse.»).

## α.61.4 — 27/09/2026

- **Tabela dos clientes: sai a legenda das bolinhas de baixo da tabela;** cada bolinha diz o que quer dizer no seu
  próprio hover.

## α.61.3 — 27/09/2026

- **Comunicações: sai «Atualizar visitas»** do cartão «Ler emails». Fica só em Visitas, onde já estava: é lá que se
  tratam as visitas, e as respostas geradas pela API já registam as marcações que levam.

## α.61.2 — 27/09/2026

- **«Gerar respostas» ganha, por baixo e em pequeno, «Ou no ChatGPT (copiar/colar)»**: fechado por omissão; aberto,
  tem «Criar e copiar o prompt» (o mesmo prompt dos emails selecionados, com as instruções extra), o prompt à vista, e
  o campo para colar a resposta do ChatGPT com «Guardar rascunhos». Os rascunhos são os mesmos que os da API.

## α.61.1 — 27/09/2026

- **Sai «Email completo»: a conversa está sempre à vista**, a mais recente em cima, numa caixa de 300 px de altura que
  faz scroll. O que o cartão responde vem marcado «por responder»; a letra passa a ser a da página (era a de máquina
  de escrever). Um email preparado pelo programa (proposta de visita, lembretes…) tem por cima uma linha a dizer o
  que é. Os cartões dos enviados usam a mesma caixa (saem «O que enviámos por último» e «Conversa»).

## α.61.0 — 27/09/2026

- **Tabela dos clientes: bolinhas ao lado de cada nome, com a legenda por baixo da tabela.** 🟠 laranja: à espera de
  resposta nossa há mais de 48 h; 🔴 vermelha: nunca nos respondeu, ou respondeu sem nada do que pedimos; 🟢 verde:
  ficha completa, já sabemos tudo dele; 🔵 azul, em vez da verde: ficha completa há mais de 96 h e ainda sem data de
  visita da nossa parte. As horas mudam-se em **Voz e estilo**, na secção nova «Bolinhas da tabela de clientes». O
  hover de cada nome diz o que cada bolinha quer dizer.
- **Por baixo de «Sem resposta», mais duas linhas: a Greylist (ignorados por agora) e a Blacklist (ignorados
  sempre)** deste imóvel, só com o número, que se abrem para mostrar os nomes. Saem da coluna «Desistiu», que fica
  só com quem recusou a visita. Os nomes das três linhas também têm bolinhas.
- A ficha de cada cliente guarda quando ficou completa (`complete_at`), para a bolinha azul; as fichas completas de
  antes contam desde a última atualização.

## α.60.2 — 27/09/2026

- **Comunicações: «Emails pendentes» passa a «Emails em tratamento»** (e «Não há emails em tratamento» quando a lista
  está vazia): «pendentes» soava a falha do nosso lado, e a lista também tem rascunhos, lembretes e propostas de visita
  a caminho.

## α.60.1 — 27/09/2026

- **«Sem resposta» sai da tabela das fases** (eram muitos e a tabela ficava comprida): passa a uma linha por baixo dela,
  «Sem resposta N», que se abre para mostrar os nomes, seguidos, uns ao lado dos outros. Fica aberta ou fechada como a
  deixaste, enquanto a página não recarrega.

## α.60.0 — 27/09/2026

- **Comunicações: uma tabela com os clientes do imóvel por fase**, logo por baixo de «Emails pendentes». Uma coluna
  por fase, com quantos são: **1.º contacto** (ainda sem resposta nossa), **1.ª, 2.ª, 3.ª e Mais de 3** interações,
  **Visita marcada**, **Visitou**, **Short list** e, à parte e em tom mais apagado, **Sem resposta** (o nosso último
  email sem resposta há 3 dias ou mais, seja qual for a interação) e **Desistiu** (recusou a visita, greylist ou
  blacklist). Cada cliente aparece uma só vez, na fase mais avançada, com o nome e o apelido; um ponto laranja marca
  quem está à espera de resposta nossa. O hover diz o nome completo e o último contacto; clicar num nome leva ao
  cartão desse cliente na lista de baixo.

## α.59.2 — 27/09/2026

- **O botão «Ignorar sempre» passa a dizer «Ignorar sempre / Blacklist»**, com o mesmo nome da lista a que leva (a que
  aparece em Imóveis); o hover e a confirmação dizem-no também.

## α.59.1 — 27/09/2026

- **Comunicações, as ações de cada email pela ordem do trabalho** (à direita): «+ Acrescentar ao conhecimento», já
  aberto; «Gerar esta resposta», com os tokens e o custo da última geração por baixo («Última geração: 1 234 tokens ·
  0,0021 €»); e **«Enviar individual»** (era «Enviar só este»), que só aparece quando há texto no rascunho.
- **«Guardar rascunho» passa para baixo do rascunho**, à esquerda, e só aparece quando o texto mudou e ainda não foi
  guardado.
- **Sai «Guardar e refazer esta resposta (API)»:** fazia o mesmo que «Guardar no conhecimento» seguido de «Gerar esta
  resposta».
- **«Retirar da fila», «Não tem interesse» e «Ignorar sempre» passam para a esquerda**, por baixo do nome do cliente e
  das etiquetas, em botões pill com um hover que explica o que cada um faz. A confirmação de «Não tem interesse» deixa
  de dizer que o cliente nunca mais entra: se voltar a escrever, a mensagem entra, com um aviso (é assim desde 26/09).
- «Gerar respostas» (o lote) diz também o custo, ao lado dos tokens.

## α.59.0 — 27/09/2026

- **Sai «Dias para trás» de Comunicações:** «Ler emails do Gmail» continua sempre desde a véspera da última leitura de
  cada imóvel. Por baixo, a página diz desde quando lê.
- **Ao criar um imóvel, a página pergunta quantos dias ler para trás na primeira leitura (45 por omissão)**, com os
  emails recebidos e as tuas respostas no Gmail. Uma leitura assim só traz ao imóvel novo os emails antigos: os outros
  imóveis não recebem nada mais antigo do que a última leitura deles.
- **As tuas respostas escritas no Gmail a um cliente que chegou nessa mesma leitura passam a contar** (antes só
  contavam na leitura seguinte, se o cliente já estivesse na fila).
- O `bot-mail setup` deixa de perguntar os «Dias da primeira leitura» e o `lookback_days` do `config.json` deixa de
  contar; `bot-mail read --days N` (e o MCP) ainda pode recuar mais, numa leitura.

## α.58.3 — 27/09/2026

- **ARIA quer dizer «AI Real Estate Inquiry Assistant»** (era «Interactions»): diz-o o hover do próprio nome, «ARIA —
  AI Real Estate Inquiry Assistant, by BigLearn.pt». **O «©» volta a dizer «© 2026 BigLearn.pt — todos os direitos
  reservados».** O nome da empresa escreve-se sempre «BigLearn.pt», como no logótipo (também no LEIA-ME da
  demonstração).

## α.58.2 — 27/09/2026

- **A consola da IA usa os nomes dos próprios modelos, abreviados** (4.1 NANO, 4o MINI, 6 LUNA, 4.1 MINI, 4.1, 4o,
  5.6 TERRA, 6 SOL, 6 ASTRA), com uma cor por família; os modos tipo «Turbo» ficam para os temas. **Entra também o
  gpt-6-astra** ($10.00 / $50.00 por 1M tokens, experimentado com uma chamada como os outros): ficam todos os modelos com
  preço confirmado, e os valores afinam-se com o uso.

## α.58.1 — 27/09/2026

- **A consola da IA mostra o preço oficial de cada modelo como a OpenAI o escreve:** «Input $2.50 · Output $10.00 /
  1M tokens».

## α.58.0 — 27/09/2026

- **Mais seis modelos na consola da IA, todos com o preço confirmado na página da OpenAI (27/09):** NANO (gpt-4.1-nano,
  $0.10 / $0.40), ECO+ (gpt-4.1-mini, $0.40 / $1.60), LUNA (gpt-6-luna, $0.10 / $0.50), SPORT (gpt-4.1, $2 / $8), TERRA
  (gpt-5.6-terra, $2 / $12, talvez promocional) e SOL (gpt-6-sol, $2 / $10), ao lado de ECO (gpt-4o-mini) e TURBO
  (gpt-4o). Cada um foi experimentado com uma chamada em JSON, como as da app, antes de entrar. Ficam ordenados do mais
  leve ao mais forte, cada um com a sua cor e o seu preço por 100 interações. O modelo de partida continua o gpt-4o-mini.

## α.57.6 — 27/09/2026

- **Resumo da atividade: nova opção «Desde sempre», a primeira e a de partida.** O gráfico começa no primeiro dia com
  dados e ajusta as barras: por dia até um mês, por semana até meio ano, por 30 dias depois disso.

## α.57.5 — 27/09/2026

- **O período do gráfico fica com quatro opções: Semana, Quinzena, Mês e Trimestre** (sai «Últimos 3 dias»; um período
  guardado que já não exista volta à Quinzena).

## α.57.4 — 27/09/2026

- **Carteira do Painel: a linha de baixo é sempre o último mês**, já não o período escolhido no gráfico, em duas
  linhas: «Último mês: X €» e, por baixo, «N pedidos · T tokens».

## α.57.3 — 27/09/2026

- **A metade do depósito diz «Clicar para mudar os limites de gastos»** ao passar o rato e, ao clicar, pergunta o
  novo limite (como a bomba, que diz o mesmo). No Painel, a bomba já não leva ao painel do imóvel: muda o limite ali.

## α.57.2 — 27/09/2026

- **Painel: sai «Gasto neste período e desde sempre: … · N pedido(s)»** de ao lado do mostrador; aparece ao passar o
  rato na metade esquerda (a do gasto).

## α.57.1 — 27/09/2026

- **Painel: sai «Restam X de Y»**, que aparece ao passar o rato na metade direita do mostrador (a do depósito); só um
  depósito vazio continua a dizê-lo por extenso. **O mostrador diz só «TOKEN$»** (saiu «GASTO €»).

## α.57.0 — 27/09/2026

- **Voz e estilo, «Inteligência artificial»: a escolha do modelo passa a ser uma consola** escura, tipo painel de
  instrumentos, com **um botão por modelo, como modos: ECO (gpt-4o-mini) e TURBO (gpt-4o)**, cada um com a luz de
  ativo, um medidor de potência, os preços por milhão de tokens e o **preço por 100 interações**. Por baixo, os
  mostradores do cálculo: a amostra, a média de tokens, a **margem (+20%)** e o **câmbio (1 € = 1,1382 US$, 27/09)**.

## α.56.1 — 27/09/2026

- **A versão e a hora de arranque passam para o fundo da barra lateral**, por baixo de «Ambiente local», em texto
  simples (sem selo), com a versão a negrito.

## α.56.0 — 27/09/2026

- **Preço por 100 interações, por modelo**, para propor a um cliente: a média deste escritório (todos os tokens da API
  sobre os emails enviados desde a primeira chamada, sem os que escreveste no Gmail), mais 20% de margem, em euros ao
  câmbio do dia (1 € = 1,1382 US$ a 27/09) e arredondado (ao cêntimo, e aos 5 cêntimos a partir de 0,50 €). Hoje:
  gpt-4o-mini ≈ 0,11 € e gpt-4o ≈ 1,75 € por 100 interações.

## α.55.9 — 27/09/2026

- **O selo da versão fica numa só linha, sem «version:» e sem o ano:** «vα.55.9» e, ao lado, o dia e a hora do
  arranque («27/09 18:29»).

## α.55.8 — 27/09/2026

- **Voz e estilo: o painel ETIQUETAS passa a ocupar 2/5 da largura** ao lado de «O teu espaço» (era 1/4).

## α.55.7 — 27/09/2026

- **O cérebro da ARIA fica numa peça branca em relevo** (efeito 3D: luz por cima, sombra por baixo).

## α.55.6 — 27/09/2026

- **A versão e a hora de arranque ficam num só selo branco em relevo**, na barra lateral, uma por baixo da outra
  (eram duas etiquetas).

## α.55.5 — 27/09/2026

- **O símbolo da ARIA passa a ser o cérebro da BigLearn** (`frontend/brand/brain.png`, com fundo transparente), em
  vez da casinha «⌂».

## α.55.4 — 27/09/2026

- **O «©» ao lado de «ARIA» diz o que o nome quer dizer**, ao passar o rato: «ARIA — AI Real Estate Interactions
  Assistant by BigLearn.PT».

## α.55.3 — 27/09/2026

- **Barra lateral: «ARIA» mantém o tamanho e ganha um «©» em expoente**; ao passar o rato, diz «© 2026 BigLearn PT —
  todos os direitos reservados».

## α.55.2 — 27/09/2026

- **Barra lateral: por baixo de «ARIA», «AI for Real Estate»** (era «Assistente»), com a letra 10% mais pequena.

## α.55.1 — 27/09/2026

- **Voz e estilo: o logótipo fica 20% mais pequeno e alinhado com o título** «As tuas palavras. O teu estilo.», à
  direita. **A legenda das etiquetas (RAG, Prompt, Voz) passa para um painel de 1/4 ao lado de «O teu espaço»**.

## α.55.0 — 27/09/2026

- **O depósito da API passa a ser um mostrador real, com duas agulhas** (como um relógio de automóvel: aro cromado,
  fundo branco, escala azul): a metade esquerda, com a agulha azul, é o que a API deste imóvel já gastou (€); a
  metade direita, com a agulha vermelha, é o que resta no depósito de tokens, de E a F, com a reserva a vermelho. No
  Painel (um por imóvel) e no painel de cada imóvel do tema Default; os temas ricos ficam para a adaptação final.
- **Encher o depósito é só o ícone da bomba**, ao lado do mostrador: sai o campo «€» com «Encher»; o clique pergunta
  o valor.

## α.54.9 — 27/09/2026

- **O mostrador do depósito da API diz «TOKEN$»** em vez de «COMBUSTÍVEL», em todos os temas, e o do painel de cada
  imóvel deixa de ter por baixo «Depósito da API deste imóvel · gastou …».

## α.54.8 — 27/09/2026

- **O logótipo da BigLearn.pt aparece em grande no canto superior direito de «Voz e estilo»**, com a legenda das
  etiquetas por baixo (`frontend/brand/biglearn.png`, recortado e com o fundo transparente). **Sai o «by BigLearn
  PT»** da barra lateral.

## α.54.7 — 27/09/2026

- **O tema «Âmbar» passa a chamar-se «Default»** no menu de temas (continua a ser o primeiro e o de partida). Por
  dentro mantém o id `amber`, para quem já o tinha escolhido não o perder.

## α.54.6 — 27/09/2026

- **Qualidade (Painel e painel do imóvel): por baixo do ponteiro fica só «N resp.»** (sai o valor, que o ponteiro já
  mostra), com a letra 20% mais pequena.

## α.54.5 — 27/09/2026

- **Temas ricos: os mostradores dizem só o que medem** («Pedidos por dia», «Por responder», «Tempo médio de
  resposta»); saem «Velocímetro», «Conta-rotações», «Anemómetro», «Barómetro», «Temperatura» e «Velocidade», que o
  desenho de cada tema já mostra.

## α.54.4 — 27/09/2026

- **«O teu espaço · Pronto para trabalhar» sai do Painel e passa para o início de «Voz e estilo»**, como resumo das
  definições (sem o «Ajustar preferências →», que ali não faz falta). O gráfico do Painel fica a toda a largura.

## α.54.3 — 27/09/2026

- **Carteira do Painel: «GASTO TOTAL» numa linha e «TODOS OS IMÓVEIS» na seguinte.**

## α.54.2 — 27/09/2026

- **Comunicações: cada email por responder ocupa 2/3 da largura, com um painel de ações ao lado (1/3)** que o
  acompanha quando o email é comprido: «Guardar rascunho» (e «Guardado»), «Enviar só este», «Abrir no WhatsApp»,
  **«Gerar esta resposta» (API) só para esse email**, com as instruções extra do passo 02, «+ Acrescentar ao
  conhecimento» (com «Guardar e refazer esta resposta») e, no fim, «Retirar da fila», «Não tem interesse» e «Ignorar
  sempre». O email, o histórico e o rascunho ficam à esquerda.

## α.54.1 — 27/09/2026

- **Comunicações: «Ler emails» passa a ser um cartão (2/3) ao lado de «Gerar respostas» (1/3)**, com o imóvel, os
  dias para trás, «Ler emails do Gmail», «Atualizar visitas» e a última leitura. As duas colunas seguem pela página
  abaixo, com cada email e as suas ações.

## α.54.0 — 27/09/2026

- **A app passa a chamar-se ARIA** (antes «Real Estate AI Assistant»): no canto («ARIA · Assistente», by BigLearn PT),
  no título da página e no terminal. O pacote e os comandos continuam `bot_mail` e `bot-mail`.
- **Cada imóvel tem o email do proprietário** (Imóveis → dados do imóvel, opcional). Preencher o imóvel a partir do
  anúncio nunca o apaga.
- **O ponto de situação de cada imóvel sai de duas maneiras:** «Enviar ao proprietário», com cópia para o teu email
  de Voz e estilo, ou «Enviar para mim», só para ti, para o reencaminhares. Uma vez por dia e por imóvel.
- **Volta a opção de receberes o resumo de todos os imóveis:** «Enviar-me o resumo de todos», no cartão do ponto de
  situação (com mais do que um imóvel), junta as páginas do bloco de notas num só email e deixa-as por enviar.
- **O ponto de situação assina «ARIA Assistente»**, em vez da assinatura da agência.
- **O Âmbar passa a ser o primeiro tema da lista e o tema de partida** (antes o APalace), para quem ainda não
  escolheu nenhum.

## α.53.1 — 27/09/2026

- **Painel: ao passar o rato em «Pedidos por responder», «Rascunhos prontos», «Bloqueados» e «A precisar de
  atenção»** aparecem os últimos 10 emails de cada um, do mais recente para o mais antigo: o primeiro nome, o imóvel
  (com mais do que um), o dia e a hora e, quando foi o programa a escrevê-lo, o que é (lembrete, proposta de visita…).
  Se houver mais, o fim diz «+ x itens». Com vários imóveis, a divisão por imóvel continua por cima. O mesmo nos
  quatro números do painel de cada imóvel.

## α.53.0 — 27/09/2026

- **O ponto de situação passa a ser para o proprietário, um por imóvel.** Em vez de conversas, emails na fila,
  rascunhos e «por preparar», conta o que interessa ao dono do imóvel: **contactaram** (clientes, não conversas:
  inclui os pedidos novos ainda por responder), **responderam** à nossa primeira mensagem, **ainda ativos** (dos que
  responderam, sem os que deixaram de responder, recusaram a visita ou pediram para não serem contactados),
  **marcaram visita** e **visitaram**. O cartão do Painel mostra estes cinco números, no total e por imóvel, com os
  nomes de quem visitou.
- **O texto para o proprietário diz o que está feito e o que está em curso:** «Até hoje» (contactaram, responderam,
  visitas marcadas e feitas), «Em curso» (quem continua em conversa e as próximas visitas) e «Quem já visitou», com o
  nome e o que a ficha diz da situação profissional e do agregado familiar. Fecha com a assinatura da Voz.
- **Um bloco de notas à direita do cartão, no lugar da «Ronda de visitas»,** com uma página por imóvel (separadores).
  Substitui o «Ver e editar o texto do email». O texto escreve-se sozinho a partir dos dados; o que alterares fica
  guardado nesse dia ao sair do texto, e «Atualizar com a situação de agora» volta a escrevê-lo (pergunta antes, se
  o tinhas alterado). **«Copiar»** para o email ou o WhatsApp do proprietário; **«Enviar»** manda a página desse
  imóvel para o endereço de Voz e estilo, com o imóvel no assunto, depois de confirmares.
- **Já não depende da primeira leitura do dia nem de haver destinatário:** o bloco de notas tem sempre o texto de
  hoje; o destinatário só é preciso para «Enviar».
- **«Ronda de visitas · Avisa os clientes ativos» passa para o separador Visitas**, no fim da página.

## α.52.8 — 27/09/2026

- **Painel: sai o botão «Tratar respostas ↗»** do topo, ao lado do relógio. As Comunicações abrem-se na barra lateral.

## α.52.7 — 27/09/2026

- **Painel: sai o botão «Gerir imóveis →»** do título «A tua carteira». Os imóveis gerem-se no separador Imóveis, e
  cada cartão continua a ter «Painel do imóvel →».

## α.52.6 — 27/09/2026

- **Painel, cartões dos imóveis: «Ver respostas →» passa a «Comunicações do imóvel →»** (abre a fila desse imóvel,
  como antes).

## α.52.5 — 27/09/2026

- **«Depósitos · API OpenAI» passa a ser uma secção inteira, a toda a largura** do Painel, por baixo do gráfico e de
  «O teu espaço» (antes ocupava só a coluna da esquerda).
- **Os dois totais que estavam por baixo dos depósitos saem dali** (pareciam de cada imóvel e mostravam o mesmo). Em
  vez deles, à direita, uma **carteira com o gasto total de todos os imóveis**: o valor desde sempre, os pedidos e os
  tokens, e uma linha para o período escolhido no gráfico, que diz «o mesmo» quando tudo foi gasto nesse período. A
  nota de que é uma estimativa aparece ao passar o rato (ⓘ).

## α.52.4 — 27/09/2026

- **O cartão do gráfico no Painel muda de nome:** «Road Book» no 70's Scooter (era «Conta-quilómetros») e no 80's
  RacingCar (era «Telemetria»); «Resumo da atividade» nos temas sem palavras próprias (era só «Atividade»). O 90's
  Boat mantém «Diário de bordo».

## α.52.3 — 27/09/2026

- **Os seis números do Painel passam a só informar:** «Pedidos por responder», «Rascunhos prontos», «Bloqueados» e
  «A precisar de atenção» deixam de abrir as Respostas ao clicar, e o cursor deixa de ser a mão. O mesmo nos seis
  números do painel de cada imóvel. A divisão por imóvel continua a aparecer ao passar o rato; o que há para fazer
  está no «A fazer», que leva a cada sítio.

## α.52.2 — 27/09/2026

Registo do que já seguiu no código dos commits de α.51.0 e α.52.1 e ainda não estava aqui:

- **90's Boat: «Sensores a bordo», por baixo do leme** — um veleiro motorsailer de 40 pés de 1980 (ketch, casa do
  leme) à noite, com sensores que pulsam em verde, âmbar ou vermelho: rádio (a última leitura do Gmail), casa do leme
  (rascunhos por enviar), porão (emails por responder), motor (depósitos da API) e proa (visitas de hoje, a azul).
- **80's RacingCar: dez luzes de aviso por baixo da caixa de velocidades** — setas, médios, máximos, ECO, motor, óleo,
  gasolina, bateria, cinto e porta, apagadas até terem motivo (as setas piscam).
- **70's Scooter: a fila de vidros redondos por baixo do punho de mudanças** — farol verde, óleo, o preto (N) e a
  gasolina, como no tablier de uma scooter dos anos 70.
- Nos três, cada luz diz ao passar o rato o que mede, e um clique leva ao separador.
- **A barra lateral deixa de ter a frase «O envio fica sempre sob o teu controlo.»**, em todos os temas.

## α.52.1 — 27/09/2026

- **KW-Area:** a etiqueta da versão («version: vα…») passa a ter fundo preto, com a letra branca, sobre o vermelho da
  barra lateral.

## α.52.0 — 27/09/2026

- **Tema novo, «APalace»** (id `apalace`), com o aspeto do site da A|Palace: fundo branco com o padrão de hexágonos
  dourados, barra lateral preta como o menu do site, com o chevron prateado do logótipo e o separador escolhido a
  dourado; títulos em Montserrat, etiquetas das secções em maiúsculas espaçadas com um filete dourado, cartões
  brancos de cantos arredondados e botões principais em pílula dourada com letra preta.
- **É o primeiro da lista de temas e o tema de partida:** quem ainda não escolheu nenhum neste browser começa no
  APalace; quem já escolheu um fica com o seu.

## α.51.0 — 27/09/2026

- **Tema novo, «KW-Area»** (id `kw`), com a identidade da Keller Williams: o vermelho KW (#B40101), os cinzentos e o
  preto do guia de estilo; a barra lateral é a parede vermelha da receção, com «kw» e todo o texto em branco; a barra
  de cima branca, como no kw.com; os cartões brancos com a faixa vermelha à esquerda da assinatura de email; as
  etiquetas das secções na faixa vermelha da capa do guia; os botões principais em pílula escura, que ficam vermelhos
  ao passar o rato. Só cores e formas: os mostradores são os simples, nas cores da KW, e não tem sons.

## α.50.9 — 27/09/2026

- **Barra lateral 15 px mais larga:** 247 px (215 px em janelas até 1150 px); o conteúdo fica onde estava, e os 15 px
  a mais ocupam a margem interior dele.

## α.50.8 — 27/09/2026

- **O fim da página, em cada tema rico, fica 40 px acima da decoração do fundo:** as ondas do 90's Boat (onde o último
  cartão ficava por cima do mar), a rua do 80's RacingCar e a vila do 70's Scooter, em qualquer largura de janela.

## α.50.7 — 27/09/2026

- **O separador «Agenda» passa a chamar-se «Visitas», em todos os temas** (menu, título, e os avisos que diziam «vê na
  Agenda»); o botão «Atualizar agenda» passa a «Atualizar visitas».
- **Comunicações:** sai a barra de passos do topo (Selecionar · Preparar · Rever e enviar); cada cartão já diz o seu
  passo.

## α.50.6 — 27/09/2026

- **Comunicações: o texto dos clientes em papel claro e tinta preta, em todos os temas** — também nos escuros (Noite,
  Índigo, 80's RacingCar): a mensagem do cartão e cada troca do «Email completo» / «Conversa».

## α.50.5 — 27/09/2026

- **Voz e estilo:** a legenda das etiquetas (RAG, Prompt, Voz) passa para o canto superior direito do cabeçalho, em
  coluna, e deixa de ocupar uma linha por baixo do título; «Copiar/colar» só aparece no modo copiar/colar.

## α.50.4 — 27/09/2026

- **O «R» (Voz e estilo) fica à parte:** 20 px entre ele e o Painel, com um friso a meio — cromado no 80's
  RacingCar, no 90's Boat e no 70's Scooter; uma linha discreta nos temas simples. No telemóvel não muda.

## α.50.3 — 27/09/2026

- **«Voz e estilo» passa a ser o primeiro separador, antes do Painel, em todos os temas**, e é o **R** (marcha-atrás)
  onde há números: no 80's RacingCar (separador e caixa de velocidades), no 70's Scooter (o tambor e os botões do
  punho: R, 1, 2, 3, 4, 5) e no 90's Boat (a bandeira V primeiro no leme). Em todos, o R soa como o Painel.

## α.50.2 — 27/09/2026

- **80's RacingCar, mudanças:** «Voz e estilo» passa a ser a marcha-atrás (R), na caixa de velocidades e no número do
  separador, e soa como o Painel. Os separadores do meio (Comunicações, Imóveis, Contactos, Agenda) ganham um som de
  aceleração a fundo, tirado da gravação do carro de corrida (CC0), mais agudo a cada mudança.

## α.50.1 — 27/09/2026

- **O mesmo seletor de imóvel em todo o lado:** as Comunicações, a Agenda e Contactos passam a escolher o imóvel como em
  Imóveis — setas grandes, a referência, a descrição, os pontos e «1 / 3» (na Agenda e em Contactos, «Todos os imóveis»
  é a primeira posição). Setas do teclado também mudam. O filtro de imóvel da tabela de contactos continua um menu, ao
  lado do RGPD e da pesquisa.

## α.50.0 — 27/09/2026

- **Versão de demonstração em HTML estático, para vender:** `bot-mail webdemo <pasta>` gera uma pasta (e um .zip) com
  a página tal como está e uma agência fictícia (3 imóveis, 16 clientes), pronta a enviar para qualquer servidor HTTP.
  Sem Gmail, sem IA e sem servidor: as respostas de cada passo foram gravadas pelo backend verdadeiro com o relógio, o
  Gmail, a OpenAI e o SMTP simulados. Ler, gerar, editar, pré-visualizar e enviar funcionam; as datas acompanham o dia
  de quem vê; uma pílula no fundo diz que é uma demonstração e tem «Recomeçar».

## α.49.0 — 27/09/2026

- **Sons reais também no 80's RacingCar e no 90's Boat** (gravações CC0 do Freesound, créditos em
  `frontend/sounds/CREDITS.md`):
  - **80's RacingCar:** o arranque e a acelerada de um carro de corrida clássico quando chegam emails; ao enviar, um GT
    italiano a puxar a fundo, rematado pelo «pssh» de um turbo; a cada separador, aceleradas curtas, mais agudas a cada
    mudança.
  - **90's Boat:** o sino do navio, duas badaladas, quando chegam emails; a buzina ao enviar; e, novo, o motor diesel a
    trabalhar a cada separador.
  - Os sons sintetizados ficam como reserva.

## α.48.12 — 26/09/2026

- **Contactos:** «Descarregar CSV» sai do cabeçalho da página e passa para o canto direito da linha dos filtros, logo
  acima da tabela de todos os contactos.

## α.48.11 — 26/09/2026

- **Short list em Contactos: 3 cartões por linha**, a toda a largura; o quarto em diante passa para a linha de baixo
  (2 por linha em ecrãs médios, 1 no telemóvel).
- **Inquérito: o comentário acaba na despedida** («Obrigada», «Com os melhores cumprimentos»…) e já não apanha o
  cabeçalho do email citado no formato do Gmail («<…> escreveu (sexta, 25/09/2026 à(s) 18:17):»).

## α.48.10 — 26/09/2026

- **70's Scooter:** a versão, no logótipo, passa de uma pílula vermelha a uma plaquinha bege com moldura cromada.

## α.48.9 — 26/09/2026

- **Horas com três algarismos no máximo:** de 100 h para cima sem decimais («214 h»), abaixo com uma casa («45,3 h»);
  o «h» já não salta para a linha de baixo. No Painel, em cada imóvel e nos mostradores.

## α.48.8 — 26/09/2026

- **70's Scooter, logótipo tricolor completo:** «by BigLearn PT» passa a branco e a negrito, entre o verde de «AI
  ASSISTANT» e o vermelho de «Real Estate».

## α.48.7 — 26/09/2026

- **70's Scooter, logótipo tricolor:** «AI ASSISTANT» passa a verde italiano com um fio branco, ao lado do «Real
  Estate» vermelho.

## α.48.6 — 26/09/2026

- **Imóveis: o computador de bordo («Diário de viagem» no 70's Scooter) passa para o início, antes dos instrumentos,**
  numa só linha mais baixa: título, distância, consumo, guardar e a leitura à direita.

## α.48.5 — 26/09/2026

- **Imóveis: os seis números do Painel, só deste imóvel**, logo a seguir aos instrumentos — pedidos por responder,
  rascunhos prontos, bloqueados, a precisar de atenção, respostas enviadas e tempo médio até resposta. Um clique nos
  da fila abre as Comunicações já neste imóvel.

## α.48.4 — 26/09/2026

- **Comunicações: «Rever e enviar» junta-se aos rascunhos.** Deixa de ser um cartão à parte e passa a uma barra no topo
  da coluna dos emails, com «Pré-visualizar envio dos selecionados»; a pré-visualização abre logo abaixo, antes da
  lista. Em cima fica só «Gerar respostas», a toda a largura.
- **70's Scooter:** os três sons ganham mais 2 segundos, a desvanecer até ao silêncio (arranque 9 s, acelerada 8,3 s,
  mudança 4,3 s).
- **Corrigido:** o quadro da short list em Contactos usava o mesmo `id` que o contador de emails selecionados nas
  Comunicações, e o número de candidatos ia parar ao sítio errado. Um teste garante agora que nenhum `id` se repete.

## α.48.3 — 26/09/2026

- **Quarto mostrador de satisfação: «Interesse em arrendar»** — «sim» 100, «talvez» 50, «não» 0, em média — no Painel e
  em cada imóvel. Os mostradores ficam todos numa linha (até 4), dois por linha em ecrãs médios, um no telemóvel.

## α.48.2 — 26/09/2026

- **70's Scooter:** no fundo da barra lateral, a bota de Itália dá lugar a um emblema oval cromado — aro cromado, a
  tricolor sob uma cúpula de vidro com o reflexo, e «Italia» em cursiva preta cromada (sem marca).

## α.48.1 — 26/09/2026

- **Painel, depósitos da API:** cada imóvel mostra por baixo do seu depósito o seu próprio gasto (neste período e
  desde sempre); o total de todos os imóveis fica à parte, em linhas a toda a largura, com esse nome. Antes, as duas
  linhas do total ficavam lado a lado, uma debaixo de cada imóvel, e pareciam ser de cada um.
- **70's Scooter, sons mais longos:** o arranque com o ralenti (7 s), a acelerada com o andamento a seguir (6,3 s) e a
  mudança de separador (2,3 s), com saídas mais suaves; um separador novo esbate o som do anterior.

## α.48.0 — 26/09/2026

- **70's Scooter: som de uma scooter a sério.** Três cortes de uma gravação real de uma PX 200 a dois tempos
  (Freesound n.º 158891, *druki*, licença CC0 — domínio público, também para uso comercial): o arranque e o ralenti
  quando chegam emails, uma acelerada ao enviar, e um pedaço de andamento a cada separador, mais agudo a cada mudança.
  Ficam em `frontend/sounds/` (AAC, cerca de 100 KB no total), servidos pela própria página; os créditos estão em
  `frontend/sounds/CREDITS.md`. Os sons sintetizados ficam como reserva, se um corte não puder tocar.
- **«Escolher» o inquilino é um botão de emergência:** laranja, atrás de uma moldura às riscas amarelas e pretas; o
  primeiro clique levanta a tampa (fica vermelho, a pulsar, «Confirmar: … é o inquilino», com «cancelar»), o segundo
  escolhe; ao fim de 6 s sem confirmação, volta a fechar.
- **Mostradores de qualidade em grelha de 3 por linha** (3 lado a lado; 6 em duas linhas), e sem o «null» que aparecia
  no Painel.

## α.47.6 — 26/09/2026

- **Comunicações:** «Gerar respostas» e «Rever e enviar» passam para cima, lado a lado, e a lista de emails fica por
  baixo, a toda a largura.

## α.47.5 — 26/09/2026

- **Short list como interruptor**, em Imóveis («Quem já visitou») e nas fichas de Contactos: «☆ Short list» junta o
  cliente; aceso, «★ Na short list» (ou «★ Escolhido» / «★ Suplente»), tira-o, pedindo confirmação para o escolhido e o
  suplente. O cartão atualiza-se logo a seguir ao clique.

## α.47.4 — 26/09/2026

- **Os mostradores de satisfação mostram já as respostas guardadas.** As que ficaram sem notas (escritas por
  extenso) são relidas ao abrir a página, sem esperar pela leitura seguinte. O leitor também percebe respostas que
  descrevem em vez de dar nota: «Rápida e clara», «eficiente», «profissional» valem 5; «lenta», «confusa» valem 2.
- **70's Scooter: o tambor do punho de mudanças para sempre no número certo.** Antes, no Safari, ficava entre dois
  números (metade do 3, metade do 4). Agora desliza em unidades do próprio desenho, com um pequeno ressalto ao
  encaixar.

## α.47.3 — 26/09/2026

- **Mostradores de satisfação sempre à vista:** no Painel e, em Imóveis, num cartão novo «Satisfação dos clientes»
  logo a seguir aos instrumentos. Sem respostas, o ponteiro fica a meio (como o meio-dia) e o visor diz «sem
  respostas».

## α.47.2 — 26/09/2026

- **Inquérito: o leitor das respostas reescrito.** Lê pergunta a pergunta: a resposta é o que vem depois dos dois
  pontos, mesmo quando a pergunta ocupa duas linhas; o negrito do Gmail (*…*) e o email citado não contam; uma nota
  pode ser um algarismo ou uma palavra («Excelente», «Muito bom», «Razoável», «Fraco», «Mau», também em inglês e
  francês). Antes só contava um algarismo no fim da linha, e o interesse era tirado das opções «(sim / não / talvez)»
  da própria pergunta. As respostas já guardadas sem notas voltam a ser lidas na leitura seguinte — com os dados
  reais, a de uma cliente passa a dar 5, 5 e 5 nos mostradores.
- **80's RacingCar:** o número das Comunicações fica em expoente, junto ao nome, e não encostado ao lado direito.
- **Imóveis:** «Quem já visitou · finalistas» passa para logo a seguir aos instrumentos, antes da blacklist, da
  greylist e da última ronda.

## α.47.1 — 26/09/2026

- **90's Boat: os separadores cabem na barra lateral.** A bandeira, o ícone, o nome e o número não cabiam (cerca de
  210 px para «Comunicações»), e o separador passava por baixo da calha cromada: menos espaço entre eles, a bandeira
  um pouco mais pequena e o número numa bolha no canto do separador.

## α.47.0 — 26/09/2026

- **Imóveis: «Quem já visitou · finalistas».** Um cartão com quem apareceu às visitas do imóvel, do mais recente para
  o mais antigo: o dia, as notas do inquérito e o interesse, a ficha, e se está na short list, é o escolhido ou o
  suplente; «+ Short list» junta-o ao quadro no topo de Contactos. Quem faltou aparece numa linha à parte.
- **O gráfico do imóvel** («O ritmo deste imóvel», «O percurso deste imóvel» no 70's Scooter) sai do quadro de
  instrumentos e passa para o fim, depois da blacklist, da greylist e da última ronda.
- **70's Scooter:** a bandeira do separador aberto fica com o dobro da largura e já não deixa linhas a sair pelos
  outros lados.

## α.46.12 — 26/09/2026

- **70's Scooter:** os títulos ganham um toque de sol por baixo — uma só sombra mostarda, suave, a 2 px.

## α.46.11 — 26/09/2026

- **70's Scooter:** a tricolor no guiador dos instrumentos passa a ser um friso pintado nele — centrado, fino, com as
  pontas redondas e um fio cromado à volta — em vez de uma faixa retangular que saía pelos cantos redondos.

## α.46.10 — 26/09/2026

- **Os botões redondos «Apareceu / Não apareceu» (Agenda) ficam alinhados com o texto**, em todos os temas: a regra
  que faz os campos ocuparem a largura toda apanhava-os, e no 70's Scooter ainda levavam o aspeto de campo de texto.
- **70's Scooter, mais Itália:** as riscas passam de mostarda, laranja, vermelho e castanho ao verde, branco e vermelho
  (topo dos cartões e dos números, friso da barra de cima, barra sob os títulos, topo do guiador e os arcos do fundo).

## α.46.9 — 26/09/2026

- **70's Scooter:** os títulos perdem a sombra às riscas e ficam limpos, em Futura itálico castanho-escuro; as quatro
  riscas dos anos 70 passam a uma barra curta por baixo de cada título.

## α.46.8 — 26/09/2026

- **70's Scooter:** os painéis acabam antes da vila: no fim da página, o rodapé (a vila, os jardins e a estrada) vê-se
  inteiro.

## α.46.7 — 26/09/2026

- **70's Scooter:** as casinhas e os jardins saem da barra de cima e ficam só no rodapé; em cima fica o céu de fim de
  tarde, com a scooter a passar.

## α.46.6 — 26/09/2026

- **70's Scooter: a scooter redesenhada a partir de uma fotografia de referência** — cava traseira grande e redonda
  com o farolim, banco preto comprido, piso baixo com o quadro a descer do banco, escudo alto com friso cromado,
  farol redondo no guiador com espelho e punhos, guarda-lamas da frente grande, suspensão à vista, silenciador e
  rodas pequenas. Vermelha, sem marca nem nome, virada para onde anda (a esquerda); sem a bandeirinha.

## α.46.5 — 26/09/2026

- **70's Scooter:** a scooter passa a vermelha, com a silhueta de uma 125 clássica italiana do fim dos anos 70 (escudo
  alto com a grelha da buzina, guiador com o farol redondo, cavas traseiras redondas, banco comprido preto, grade
  cromada, rodas pequenas), sem marca nem nome. A vila tem casas mais largas de dois ou três pisos, jardins com
  árvores, ciprestes e sebes pelo meio, e cafés com toldos às riscas e mesinhas com guarda-sol. O título do Painel
  passa a «O teu dia, a passear numa vila costeira.»

## α.46.4 — 26/09/2026

- **WhatsApp: a linha 🏠 do imóvel junta-se à saudação.** «Cara Ana Exemplo, relativo ao seu contacto via Idealista
  do T3 na Rua … — link», em vez da linha solta «🏠 Apartamento T3 …». A frase segue a língua da saudação (inglês,
  francês ou espanhol, senão português); o título e o link do imóvel ficam exatamente como estão. O email não muda.

## α.46.3 — 26/09/2026

- **70's Scooter:** no rodapé, a estrada fica direita, com o lancil branco e o tracejado, e os prédios da vila, maiores,
  ficam por cima dela, com o mar por trás; a scooter passa pela estrada a direito, para a esquerda. Na barra lateral,
  as flores saem e entra uma faixa de corrida vermelha com um friso branco e um preto.

## α.46.2 — 26/09/2026

- **70's Scooter:** a sombra às riscas dos títulos fica colada às letras (6 px em vez de 15) e o título já não pisa
  o subtítulo.

## α.46.1 — 26/09/2026

- **70's Scooter, a costa:** no rodapé, uma vila à beira-mar (casinhas em tons pastel com portadas verdes e um
  campanário) e a estrada a descer da encosta, da direita para a esquerda, com o muro branco e o tracejado; a
  scooter desce por ela, inclinada, para a esquerda. Na barra de cima, a mesma vila ao longe, e a scooter a
  atravessá-la para a esquerda.

## α.46.0 — 26/09/2026

- **70's Scooter, muito mais anos 70:**
  - **Fundo:** um sol com raios no canto e as quatro riscas em grandes arcos, e cartões com uma faixa grossa às riscas
    e sombra sólida.
  - **Títulos e rótulos:** títulos maiores, com as riscas a sair por trás, e os rótulos são autocolantes colados tortos.
  - **Barra lateral:** florzinhas «flower power» e um autocolante da bota de Itália tricolor ao fundo, com espaço
    próprio (já não tapa o email da conta); o separador aberto leva a tricolor na ponta.
  - **Movimento:** os botões dão um «vroom» ao passar o rato, e a scooter passa maior, com fumo do escape, a cada 45 s.
- **Som de scooter a sério:** o motor de 125 a dois tempos passa a um zumbido agudo e metálico («ring-ding-ding»), mais
  estalidos por segundo e sem graves; a buzina também fica mais aguda.

## α.45.2 — 26/09/2026

- **Painel: o ponto de situação diário redesenhado.** Em vez de uma caixa de texto: para quem vai, quatro números
  grandes (conversas, na fila, rascunhos prontos, por preparar), um bloco por imóvel com os seus números e os nomes
  de quem falta preparar, e o botão «Enviar o ponto de situação». O texto do email fica em «Ver e editar o texto do
  email». Os números são sempre os de agora; **«Atualizar com a situação de agora»** reescreve o texto, que antes
  ficava como na primeira leitura do dia.

## α.45.1 — 26/09/2026

- **90's Boat: o separador aberto já não passa por baixo da calha cromada** da barra lateral, e o número das
  Comunicações volta a ver-se inteiro.

## α.45.0 — 26/09/2026

- **Tema novo: 70's Scooter.** Uma scooter italiana dos anos 70 na estrada da costa: creme e cromados, o escudo da
  scooter em verde-menta na barra lateral (com a tricolor ao fundo), o banco vermelho no separador aberto e nos
  botões principais, e as quatro riscas dos anos 70 (mostarda, laranja, vermelho, castanho) nos cartões, na barra de
  cima e na sombra dos títulos, em Futura itálico. Os instrumentos de cada imóvel são o guiador: mostradores creme
  com números em itálico e aros cromados. Os separadores mudam-se com um **punho de mudanças**, com o tambor numerado
  de 1 a 6. Os contadores são tambores de conta-quilómetros. Uma scooter com a sua bandeirinha passa na barra de
  cima e volta pela estrada, no fundo da janela. Sons: a buzina ao enviar, o arranque ao pedal quando chegam
  emails, uma mudança por separador e um clique cromado nos botões. Sem marcas nem nomes, como os outros temas.
- **O tema 90's RacingCar passa a chamar-se 80's RacingCar** (o `id` continua `racing`, a escolha guardada não se
  perde).
- **90's Boat, Contactos:** a tabela lê-se bem também no turno da noite (o email estava quase invisível), e os campos
  do nome e do telefone deixam de ter caixa até lhes passares o rato ou os editares.

## α.44.4 — 26/09/2026

- **90's RacingCar: o botão «Sons» fica à direita da barra de cima**, como no barco, com um altifalante que mostra
  desligado (riscado) ou ligado (com ondas), e fica vermelho quando está ligado. No telemóvel, só o ícone.

## α.44.3 — 26/09/2026

- **A Agenda mostra todas as visitas e janelas passadas**, em qualquer semana para trás: ficam registadas para
  sempre (só saem se apagares o contacto, pelo RGPD). A tarefa «visitas por registar» continua a olhar só para os
  últimos 14 dias.
- **«Preencher fichas com a IA (lê as conversas)»**, em Contactos: a API lê a conversa de cada cliente ativo e
  preenche a ficha, sem perder o que já se sabia. Em lotes de 10, com o modelo escolhido e o custo no depósito
  do imóvel.
- **A primeira mensagem do cliente (a do portal) passa a ficar no histórico** da conversa quando respondes. Até
  aqui só ficavam as mensagens seguintes, e por isso as fichas e os prompts perdiam o que o cliente disse
  primeiro. As conversas antigas não a têm e não é possível recuperá-la.

## α.44.2 — 26/09/2026

- **Imóveis numa só coluna:** os dados do imóvel em cima e, por baixo, cada painel (relatório dos inquéritos,
  clientes ativos, análise e visitas) sozinho, a toda a largura, em vez de ao lado dos dados do imóvel.

## α.44.1 — 26/09/2026

- **Avisos do portal sem Reply-To já não ficam bloqueados quando trazem o email no corpo.** Esse email passa a ser o
  destinatário, com o aviso «Sem Reply-To: o destinatário é o email do corpo do aviso… Confirma antes de enviar».
  No cartão há um campo **Destinatário** para o confirmares ou mudares à mão, que também desbloqueia um aviso sem
  email nenhum. Os que já estavam bloqueados na fila são corrigidos na leitura seguinte. O endereço do portal e a
  tua própria conta continuam recusados.
- **Lembretes de 2 e 4 dias só na qualificação** (antes da proposta de visita) e nunca depois de 6 dias de
  silêncio. Com os dados reais, a regra de α.44.0 criaria de uma vez 28 lembretes a clientes que receberam a
  proposta de uma ronda já passada.
- **Agenda: as janelas propostas dos últimos 14 dias continuam desenhadas**, como as marcações (antes, a janela de
  um dia que já passou desaparecia). As rondas e as propostas continuam a usar só as janelas por vir.

## α.44.0 — 26/09/2026

- **Inquérito pós-visita: agradecimento, aviso e relatório.** A resposta do cliente ao inquérito chega marcada
  «resposta ao inquérito» e a IA agradece-lhe, sem se justificar perante uma nota má. Uma nota 1 ou 2, ou um «não»
  ao interesse, aparece em destaque no cartão e em «A fazer». Cada imóvel tem o **relatório dos inquéritos**
  (Imóveis): um mostrador por parte perguntada (imóvel, consultor, marcação e emails), o interesse e cada resposta
  com o comentário. No **Painel**, os mesmos três mostradores com o total de todos os imóveis.
- **Mostradores de qualidade:** de 0 a 100, com verde a partir de 80 (excelente) e vermelho abaixo de 40. É uma
  média ponderada em que um 1 pesa três vezes e um 2 duas vezes: poucos 1 puxam o mostrador para baixo, e só 1
  dá 0.
- **Seleção em Contactos, logo no início:** a short list de 2 ou 3 candidatos, lado a lado, com a ficha, a visita
  (veio ou não, notas), o inquérito e os documentos. Escolhes o inquilino e um suplente. «+ Short list» em cada
  ficha. Os documentos (recibos de vencimento, IRS do ano anterior ou dos dois anteriores, e, opcionais, o email
  oficial do emprego e a declaração ou contrato de trabalho; os mesmos do fiador, se houver) pedem-se só à short
  list, com «Pedir documentos», que põe um rascunho nas Comunicações. Os ficheiros ficam no Gmail: aqui só se
  marca o que chegou.
- **Silêncio:** os lembretes de 2 e 4 dias, sem frase em Voz e estilo, passam a ser escritos pela IA, e não saem
  para quem tem visita marcada ou feita. Dois emails nossos seguidos sem resposta, o último há 4 dias, deixam o
  cliente **inativo**: sai das rondas, dos lembretes e das fichas, com a etiqueta «inativo» na lista de contactos.
  Se voltar a escrever e o imóvel estiver ativo, volta a ativo.
- **Faltou à visita:** marcar «não veio» na Agenda põe um rascunho a lamentar que não tenha sido possível, sem
  culpar ninguém, a dizer que pode responder e que ficamos a aguardar uma nova ronda. Se corrigires para «veio»,
  o rascunho sai.
- **Abrir no WhatsApp:** cada cartão com telefone abre o WhatsApp do Mac na conversa do cliente, com o rascunho
  escrito. Envias tu, lá. O telefone nunca vai para a IA.
- **Verificação do rascunho:** o cartão avisa se a assinatura não aparece uma vez, se ficou um <campo> por
  preencher, se falta a linha 🏠 que o know-how pede, ou se a hora da visita marcada não está no texto.
- **Colar perfil do Idealista** em cada ficha: o perfil do inquilino não vem no email (está atrás de «Ver
  perfil»); colas o texto e a API preenche a ficha.
- **RGPD, 6 meses:** os contactos sem consentimento com mais de 6 meses sem movimento aparecem em Contactos e em
  «A fazer», e apagam-se de vez com «Apagar agora», depois de confirmares.

## α.43.0 — 26/09/2026

- **«Modo: só API».** A página trabalha só com a API da OpenAI. As Comunicações passam a 3 passos: Selecionar,
  Gerar respostas e Rever e enviar. «Gerar respostas» parte seleções grandes em chamadas de 5 emails e mostra
  «Ver o que foi enviado à IA». O copiar/colar do ChatGPT e o MCP ficam escondidos, não apagados: voltam com
  `"ai_mode": "copy_paste"` no `config.json`.
- **Escolha do modelo em «Voz e estilo»:** `gpt-4o-mini` (por defeito) ou `gpt-4o`, com o preço de cada um. Um
  modelo para tudo; o custo continua a contar no depósito de cada imóvel.
- **Criar imóvel pelo texto do anúncio:** colas o texto copiado da página do portal (e o link) e a API extrai os
  campos, que revês antes de guardar.

## α.42.0 — 26/09/2026

- **Lembretes de visita: na véspera e no próprio dia.** A primeira leitura de cada um desses dias põe um rascunho
  nas Comunicações, marcado «lembrete de visita · amanhã/hoje» e a hora. A IA escreve-o no idioma do cliente, com o
  dia, a hora, onde fica o imóvel e o pedido de WhatsApp ao agente (se estiver no conhecimento do imóvel), e lembra
  o que ainda falta na ficha. Revês e envias como qualquer outro. No dia, o da véspera que ficou por enviar é
  substituído. Não conta como interação nem mexe nos lembretes de 2 e 4 dias. Não sai para quem já tem a visita
  registada, está numa lista, pediu outra data, ou se o retiraste da fila. As instruções editam-se em Voz e estilo.
- **Painel: «A fazer», logo a seguir aos números.** Calculado a partir dos dados, do mais urgente para o menos:
  lembretes de visita por enviar, envios incertos, emails bloqueados, emails por responder, rascunhos por enviar,
  horas aceites por confirmar, visitas por registar, agradecimentos por criar, clientes com ficha completa sem
  proposta, clientes no travão e textos em falta em Voz e estilo. Cada linha diz quantos, em que imóvel e os
  primeiros nomes, e leva ao separador onde se faz. Uma tarefa desaparece quando fica feita.

## α.41.0 — 26/09/2026

- **Ficha de cliente.** Em cada resposta, a IA devolve também a ficha do cliente: situação profissional e
  rendimentos, agregado familiar, datas ou duração do contrato, disponibilidade para visitas e, só se o cliente
  falar nisso, empresa e animais. Só com o que o cliente disse. O programa junta-a à que já havia (nada do que se
  sabe se perde) e guarda-a logo, como o estado da visita.
- **Contactos: fichas por imóvel, de 3 a 5 de cada vez** (quantas couberem na largura), com setas para as
  seguintes e um menu de imóvel só com os ativos. Mostra a fase (qualificação, proposta de visita, visita marcada,
  visitou…) e o que falta. A lista completa de contactos continua por baixo, igual.
- **A qualificação repete a 2.ª interação.** Até haver proposta de visita, cada email do cliente é a 2.ª, que
  pede só o que falta na ficha, e nunca a 3.ª só por contagem de emails. Ao fim de três pedidos de informação sem
  a ficha completa, a IA deixa de perguntar e o cartão avisa-te para decidires se propões visita na mesma.
- **Etiqueta «ficha 2/4» ou «ficha completa»** nos cartões da 2.ª interação, nas Respostas, e nos clientes ativos
  de cada imóvel.
- **A ficha incompleta não trava a visita.** O cliente recebe na mesma a proposta de visita, e a marcação da hora,
  com um lembrete no fim do que ainda precisamos de saber para a visita ficar confirmada. O cartão avisa-te de que
  decides tu se confirmas.
- **Cada marcação na Agenda mostra a ficha:** «ficha ok» ou «ficha 2/4», e ao abrir a visita diz o que falta. É
  atualizada à medida que as respostas chegam.

## α.40.0 — 26/09/2026

- **Imóveis ATIVOS e INATIVOS.** Em Imóveis, cada imóvel mostra a etiqueta ATIVO ou INATIVO e o botão
  «Marcar como inativo» / «Voltar a ativar». Um imóvel inativo sai dos menus de imóvel (Respostas, Agenda,
  Contactos e ronda de visitas), mas continua em Imóveis com tudo o que tem. Se ainda tiver emails por tratar,
  continua no menu das Respostas, marcado «(inativo)», para nenhum ficar perdido. Um imóvel novo começa sempre
  ativo.
- **Greylist diferente da blacklist.** Na greylist deixamos de escrever primeiro (lembretes, rondas,
  consentimento, fecho), mas se o cliente voltar a escrever o email entra na fila, com um aviso, e pode ser
  respondido. A blacklist continua a não deixar entrar nada.

## α.39.6 — 26/09/2026

- **90's RacingCar: na rua do fundo passa só o mesmo carro vermelho**, no regresso depois de passar no topo; a
  lambreta saiu.

## α.39.5 — 26/09/2026

- **O carro e o barco fazem a volta completa.** No 90's RacingCar, depois de passar no topo para a esquerda, o
  carro vermelho volta pela rua do fundo, virado ao contrário, para a direita (e a lambreta passa noutra altura).
  No 90's Boat, o veleiro atravessa o topo para a esquerda e depois volta espelhado pelo mar, para a direita, com
  as luzes de noite no quarto da noite.
- **Ícones do menu iguais em todos os temas:** Painel um mostrador, Comunicações a antena, Imóveis uma casa,
  Contactos uma pessoa, Agenda uma agenda e Voz e estilo uma roda dentada. No 90's RacingCar ficam ao lado do número
  da mudança e no 90's Boat ao lado da bandeira náutica; o microfone de rádio do barco sai e Comunicações volta à
  sua bandeira.

## α.39.4 — 25/09/2026

- **Agenda: quatro horas de cada vez.** A semana passa a ocupar cerca de metade da altura e rola por dentro, com o
  dia e a data sempre no topo; cada quarto de hora mantém o tamanho que tinha. Abre na primeira visita da semana
  (ou na hora atual, ou no início do dia) e, enquanto não mudares de semana nem de imóvel, fica onde a deixaste.
  No telemóvel os dias continuam uns por baixo dos outros, inteiros.
- **Linhas mais finas:** as de 15 minutos ficam o mais finas possível e as de meia hora um pouco mais marcadas; as
  das horas ficam como estavam.

## α.39.3 — 25/09/2026

- **90's RacingCar: uma rua de vila italiana no fundo da janela**, como o mar no 90's Boat. Casas em ocre,
  terracota e rosa com portadas verdes, uma arcada, um campanário, a cúpula de um duomo e ciprestes, por cima de
  um passeio de sampietrini, do lancil e do asfalto com a linha tracejada. A estrada corre depressa e a vila
  devagar, e de vez em quando passa uma lambreta creme. Fica por trás de tudo, e para com «reduzir movimento».

## α.39.2 — 25/09/2026

- **Agenda, «Depois das visitas»:** por cima da semana aparece a lista das visitas que já passaram (até 14 dias)
  e ainda não assinalaste, cada uma com um botão («Nome · 25/09 13:00») que abre o passo pós-visita: se
  apareceu, as notas e «Guardar e criar agradecimento». Antes só se chegava lá carregando no bloco da visita.
- **As horas a azul (proposta nossa) e a laranja (aceite pelo cliente) também se podem assinalar:** se o cliente
  apareceu a essa hora, a visita fica registada nela (verde) e segue para o agradecimento.

## α.39.1 — 25/09/2026

- **90's RacingCar, com «Sons» ligado: cada separador é uma mudança.** Ao mudar de separador (no menu ou na
  caixa de velocidades) ouve-se a alavanca a passar a grelha e o motor a puxar nessa mudança; cada mudança é
  mais aguda que a anterior (a 1.ª um rosnar grave, a 6.ª a mais alta). A subir, a rotação cai e volta a puxar; a
  descer, um golpe de acelerador antes de assentar. Os separadores deixam de dar o estalido dos outros botões.

## α.39.0 — 25/09/2026

- **Depois da visita, na Agenda:** cada visita marcada tem um «check» — apareceu ou não, uma **nota privada**
  (só para ti: nunca vai num email nem para a IA) e uma **nota pública**. «Guardar e criar agradecimento» põe na
  fila o rascunho pós-visita, escrito pela IA com as instruções «Pós-visita» de Voz e estilo: agradecimento com a
  nota pública, um **inquérito respondido no próprio email** (de 1 a 5: o imóvel, o consultor, a marcação e os
  emails; se continua interessado; um comentário) e a **ficha de visita** («Confirmo a visita»). A leitura
  seguinte guarda as respostas no cliente e mostra-as na visita. A Agenda mostra também as visitas dos últimos
  14 dias, para as assinalares depois.
- **Sons:** o 90's RacingCar também tem o interruptor «Sons» (um V12 a acelerar ao enviar, o rádio da box quando
  chegam emails), e os botões passam a ter som nos temas com sons. Continuam desligados até carregares em «Sons».
- **90's RacingCar:** um carro vermelho dos anos 90, em cunha e com a grande asa traseira (sem marca), passa de vez
  em quando no topo, por trás do texto, como o barco no 90's Boat. Com «reduzir movimento» não aparece.
- **Painel, «Depósitos · API OpenAI»:** os depósitos dos imóveis ficam lado a lado, a toda a largura; «Encher no
  painel do imóvel» passa a um ícone de bomba de gasolina; a nota sobre a estimativa passa para o «ⓘ» ao passar o
  rato nas linhas de gastos, que também ficam lado a lado. O cartão fica com menos de metade da altura.
- As regras para quem trabalha no projeto (testar só com código, sem browser; vários agentes, cada um nos seus
  ficheiros) ficam em `CLAUDE.md`.

## α.38.3 — 25/09/2026

- **O separador «Respostas» passa a chamar-se «Comunicações»** (no título da página: «Centro de Comunicações»),
  no menu e nas mensagens que apontam para a fila. «Respostas enviadas» (no Painel) e a coluna «Respostas» (nos
  Contactos) ficam como estão: contam respostas, não são o separador.

## α.38.2 — 25/09/2026

- **Cada troca da conversa mostra o dia e a hora** («qui., 24/09, 22:40»), no «Email completo» e nos cartões
  «Enviados»: com só o dia, não se percebia qual de duas mensagens do mesmo dia era a mais recente.
- As trocas antigas, que só tinham o dia, receberam a hora exata do Gmail (lido, nunca alterado): as 87
  trocas dos dois imóveis têm hora, e ficaram pela ordem certa.

## α.38.1 — 25/09/2026

- **90's Boat: os botões de envio deixam de parecer um botão de emergência.** Em vez de vermelho com riscas
  brancas e maiúsculas, «Enviar só este» (e o «Enviar» do lote e do ponto de situação) é agora uma tecla
  azul-marinho (#173B4D, com degradé discreto), letra marfim (#F5F2EA) em semibold, aro fino metálico
  (#A9B5BB) e uma pequena luz verde-água (#48B8AC), com relevo subtil. O vermelho fica para alarmes e ações
  destrutivas.

## α.38.0 — 25/09/2026

- **Vários emails do mesmo cliente passam a ser um só cartão**, com uma só resposta para todos (marca
  «N mensagens»). As mensagens aparecem juntas, da mais antiga para a mais recente, e a resposta vai em
  resposta à mais recente. Ao enviar, ficam todas respondidas e a conversa avança uma única etapa.
- Um email a que já respondeste no Gmail também entra no cartão, como contexto, com a nota «já respondida no
  Gmail»; se houver alguma mensagem ainda por responder, o cartão é uma resposta nova.
- Se já havia um rascunho escrito antes de chegarem as outras mensagens, volta a «por responder», com o
  aviso para o reveres antes de enviar.
- Lembretes, propostas de visita, acrescentos e emails bloqueados nunca se juntam.

## α.37.0 — 25/09/2026

- **«Atualizar agenda» passa a rever também quem já tem visita marcada**, e vale sempre a mensagem mais
  recente: se no Gmail mudaste a hora (por exemplo, de 12:00 para 13:00), a visita muda de hora, com a nota
  «antes: 12:00» ao passar o rato.
- **Azul: proposta nossa, à espera do cliente.** Quando a última palavra é tua a propor um dia e uma hora
  («It's available 14:30 tomorrow»), mesmo sem resposta do cliente, a Agenda mostra essa hora a azul. Se o
  cliente tinha outra hora marcada, essa sai (a proposta nova substitui-a) e fica a nota «antes: 14:00».
- Uma resposta vaga da IA sobre quem já está marcado nunca desmarca: só o laranja e o azul se apagam.

## α.36.1 — 25/09/2026

- **«Email completo» mostra a conversa inteira, da mais recente para a mais antiga**, e já não só o que havia
  antes desta mensagem. A mensagem do cartão aparece destacada («esta mensagem»). Se a última palavra for
  nossa — uma resposta que escreveste no Gmail, ou um acrescento —, aparece em cima, marcada «a nossa última
  resposta, ainda sem resposta do cliente». O mesmo nos cartões «Enviados» («Conversa»).
- Cada troca nova da conversa guarda também a hora, para as do mesmo dia ficarem pela ordem certa (a tua
  resposta no Gmail às 10h antes do email do cliente às 12h). As trocas antigas, só com o dia, mantêm a ordem
  que tinham.

## α.36.0 — 25/09/2026

- **«Atualizar agenda»** (em Respostas, ao lado de «Ler emails do Gmail», e na Agenda): a IA (API) lê as
  conversas dos clientes ativos de cada imóvel — os emails deles e os nossos, também os que escreveste
  diretamente no Gmail — e atualiza a Agenda sozinha, como escolheste:
  - **verde**: um dia e uma hora que nós confirmámos ao cliente ficam marcados como visita;
  - **laranja**: um dia e uma hora que o cliente propôs ou aceitou, mas que ainda não confirmámos.
  Passar o rato mostra a frase do email em que a IA se baseou. Nunca marca no passado nem inventa horas, não
  pergunta pelos clientes já marcados, que recusaram ou que ignoras, e os endereços nunca vão para a IA.
  Gasta do depósito de cada imóvel; um imóvel com o depósito vazio fica de fora e a mensagem diz porquê.
- **Os enviados ficam na fila.** Por baixo dos emails por responder, em «Enviados · clientes ativos», fica um
  cartão por cada cliente ativo já respondido (pela página ou no teu Gmail), com o que enviámos por último e
  a conversa. Sai quando há visita marcada, quando o cliente recusa ou é ignorado, quando fechas as visitas,
  ou quando carregas em «Retirar da fila» (volta se a conversa mexer outra vez).
  - **«Escrever mais»** cria um rascunho «acrescento» na conversa desse cliente (Re: o nosso último email):
    escreves tu, ou pedes à IA nas instruções extra, e segue o caminho de sempre até «Enviar». Não gasta
    uma etapa da conversa.

## α.35.1 — 25/09/2026

- **Uma resposta tua escrita no Gmail já não tira nada da fila.** Enquanto não há dia e hora acordados, podes
  sempre enviar mais um email; por isso os emails do cliente continuam na fila, com o aviso «Já respondeste a
  este email diretamente no Gmail em dd/mm às hh:mm» e o teu texto no histórico. Podes acrescentar algo pela
  página ou retirá-los da fila.
- **A etapa conta uma só vez:** a tua resposta no Gmail é essa interação. Um email que envies depois pela
  página a esse mesmo email é um acrescento: sai normalmente, mas não gasta outra etapa (nem volta a contar
  o tempo de espera do cliente no Painel).
- Os lembretes também ficam na fila, para decidires tu.

## α.35.0 — 25/09/2026

- **A leitura passa a ver também o que enviaste diretamente do Gmail.** Quando respondes a um cliente fora
  da página, a próxima leitura encontra essa resposta (pelo endereço do cliente ou pela conversa do Gmail; o
  assunto desempata quando o mesmo cliente está em dois imóveis) e:
  - tira da fila, como respondidos, os emails desse cliente que chegaram antes da tua resposta, e os
    lembretes que já não fazem sentido;
  - avança a conversa uma interação (quando respondeu a algum email), para a próxima resposta da IA ser a
    etapa certa;
  - junta ao histórico o que escreveste, sem o email citado por baixo, para a IA ter esse contexto — também
    nos emails do cliente que chegaram depois e ainda esperam resposta;
  - conta-a no Painel como uma resposta enviada, com o tempo que o cliente esperou.
- Os emails enviados pela própria página nunca contam duas vezes, e o correio para quem a página não
  conhece fica de fora. No fim da leitura, a mensagem diz quantas respostas tuas foram registadas.
- Num ensaio com uma cópia dos teus dados, a leitura encontrou 13 respostas tuas dos últimos 5 dias; na
  Ramada, 6 emails que continuavam por responder já tinham resposta tua.

## α.34.0 — 25/09/2026

- **Marcar visitas: quando o cliente pede uma hora fora do intervalo (ou já ocupada), a resposta oferece-lhe
  a hora que nos convém**, para juntar as visitas do dia: a primeira hora livre, com início e fim, por
  exemplo «Lamentamos, mas para esse dia já só temos o período das 15:00 (início da visita) às 15:30 (fim).
  Caso não encontremos um cliente indicado para o arrendamento nas visitas desse dia, voltaremos a organizar
  visitas e iremos propor outra data e horário em breve.» Não fica nada marcado até o cliente aceitar.
- **A resposta seguinte do cliente («pode ser às 15:00») continua a ser a 4.ª interação**, e por isso pode ser
  marcada. Antes passava a 5.ª, que não tem prompt, e ficava parada à espera do proprietário. Vale enquanto
  a janela para que o cliente foi convidado estiver aberta e ele ainda não tiver visita marcada; quem já tem
  visita marcada, ou disse que não quer visitar, continua a ir para o proprietário.
- O prompt da 4.ª interação dos dois imóveis foi atualizado com esta resposta (nos teus dados, não no Git).

## α.33.1 — 25/09/2026

- **90's RacingCar: o texto que vai ser enviado passa a estar em papel claro, com letra preta** — o rascunho de
  cada email, o ponto de situação diário e a pré-visualização do envio. É mais fácil de ler e de rever antes de
  enviar. As outras caixas (instruções, JSON, prompts) continuam escuras, como o resto do cockpit.

## α.33.0 — 25/09/2026

- **Agenda: dias em blackout.** Cada dia tem um botão «Blackout»: o dia sai da semana e os outros alargam.
  Os dias também se ligam e desligam na fila «Dias: Seg … Dom», por cima da semana, que é por onde voltas a
  pôr um dia em blackout como disponível. A escolha vale para esse dia da semana (todos os domingos, por
  exemplo) e fica guardada neste browser, como o tema. Um dia em blackout que ainda tenha visitas não
  desaparece: fica às riscas, com «Blackout, mas com visitas», para nenhuma visita ficar escondida.
- **As datas da semana ficam por cima dos botões** (por exemplo, «21/09 – 27/09/2026»), em vez do «Esta
  semana» repetido; o botão «Esta semana» fica apagado quando já estás nela.

## α.32.0 — 25/09/2026

- **Agenda com quatro cores**, com legenda por cima da semana:
  - **cinzento**: a janela de horários proposta na ronda de visitas;
  - **laranja**: a hora que o cliente aceitou, ainda num rascunho por enviar;
  - **verde**: a visita que confirmaste, ou seja, cujo email já foi enviado;
  - **tijolo, às riscas**: visitas sobrepostas (overbooking) — duas visitas, de qualquer imóvel, a horas que
    se cruzam. Aparece mesmo com o filtro num só imóvel, e passar o rato diz com que visita choca.
- Por baixo da data, o resumo do dia conta as confirmadas, as por confirmar e as sobrepostas.

## α.31.0 — 25/09/2026

- **Agenda: cada dia vai agora até ao fundo da janela**, com as horas escritas na margem e uma linha a cada
  15 minutos (a meia hora a tracejado, a hora cheia a traço contínuo). Cada visita marcada fica à sua hora,
  com a altura do tempo que ocupa, e a proposta de visitas aparece como uma faixa do início ao fim do
  intervalo. A largura dos dias não muda.
- O dia mostra sempre das 9h às 19h; uma visita mais cedo ou mais tarde alarga a semana toda, para os dias
  continuarem alinhados. Por baixo da data, uma linha resume o dia («Proposta: 12:00–16:00 · 2 marcadas»).
- Em «Todos», duas visitas à mesma hora (de imóveis diferentes) ficam lado a lado; as outras mantêm a
  largura inteira. Passar o rato por cima de uma marcação mostra o nome completo e o imóvel.

## α.30.0 — 24/09/2026

- **«90's Boat» ganha os extras:**
  - **sons de bordo**, desligados até carregares em «Sons» na barra de cima (o botão só aparece neste
    tema): a buzina de um navio quando emails saem de facto, e o sino de bordo, duas vezes, quando uma
    leitura traz emails novos. São feitos no próprio browser, sem ficheiros; a escolha fica neste browser,
    como o tema;
  - **cursor em forma de âncora** nas superfícies; nos botões e ligações continua a mão, e nos campos de
    texto o cursor de escrever;
  - **o quarto da noite, das 20h às 7h:** lá fora fica escuro — estrelas por cima da página, a lua no
    para-brisas, o mar e o veleiro de noite (com as luzes acesas), a luz vermelha de bombordo no topo do
    corrimão e a verde de estibordo no canto do para-brisas. O posto de comando (barra lateral, cartões,
    painéis) continua iluminado, com as cores de dia, e o texto que fica por cima da noite passa a claro.

## α.29.0 — 24/09/2026

- **«90's Boat» ganha mar em movimento:**
  - duas faixas de ondas no fundo da janela, a mais próxima mais depressa, com espuma branca; espreitam por
    trás dos cartões e nunca tapam o conteúdo;
  - um veleiro branco, com duas gaivotas atrás, atravessa devagar o para-brisas, por trás do texto da barra
    de cima;
  - enquanto a página trabalha, «A trabalhar…» leva um radar a varrer;
  - a bandeira do separador aberto esvoaça, e os botões balançam ao de leve quando passas o rato por cima.
- Com «reduzir movimento» ligado no Mac, nada disto se mexe.

## α.28.0 — 24/09/2026

- **«90's Boat» ganha os instrumentos de bordo em cada imóvel**, com mostradores brancos, aros cromados e
  ponteiros vermelhos, encastrados num tablier de teca envernizada de topo curvo, como nas fotografias:
  - **barómetro:** o tempo médio de resposta, de «bom tempo» a «tempestade», que chega no máximo de cada
    imóvel («Tempestade às … h», por baixo); acima dele acende a luz «Tempestade»;
  - **anemómetro:** os emails por responder;
  - **velocidade:** os pedidos recebidos por dia;
  - **depósito:** os tokens do imóvel e, mais pequeno, a gasolina das visitas;
  - cada leitura aparece num pequeno ecrã azul dentro do mostrador.
- O computador de bordo é um ecrã azul, os contadores são rodas brancas num aro cromado e as luzes de aviso
  ficam num painel de interruptores preto.
- **Os gráficos passam a plotter:** uma carta náutica (água, quadrícula e um bocado de costa) numa moldura de
  vidro preto, com os pedidos a azul e as respostas no magenta das rotas.
- A teca deixou de ter emendas onde o desenho se repete.

## α.27.0 — 24/09/2026

- **«90's Boat» ganha palavras, a roda do leme e o relógio de bordo:**
  - os títulos falam de bordo: «Ponte de comando — O teu dia, a todo o pano.», «Frota — Cada imóvel, o seu
    barco.», «Tábua de marés», «Lista de passageiros», «Pavilhão»… Só os títulos mudam; botões, campos e
    mensagens ficam iguais em todos os temas;
  - por baixo dos separadores, **a roda do leme** faz de seletor, como a caixa de velocidades no carro: seis
    raios cromados, um por separador, cada um a apontar para a sua bandeira. Ao mudar de separador, a roda gira
    pelo caminho mais curto até o raio certo ficar em cima, sob a marca vermelha, e as bandeiras ficam sempre
    direitas. Um clique numa bandeira muda de separador. Em ecrãs baixos e no telemóvel não aparece;
  - no Painel, **o relógio de bordo**: mostrador branco, aro cromado e ponteiro dos segundos vermelho, montado
    numa peça redonda de teca.

## α.26.0 — 24/09/2026

- **Tema novo, «90's Boat»: o posto de comando de um iate de luxo dos anos 90.** Casco creme brilhante em
  todo o lado, cromados nos acabamentos e teca envernizada só nos detalhes, para não parecer o carro:
  - a barra lateral tem um corrimão cromado; a marca é uma vigia com a casa lá dentro, e a versão é uma placa
    de teca;
  - cada separador tem a sua bandeira do Código Internacional de Sinais: P (Painel), R (Respostas),
    I (Imóveis), C (Contactos), A (Agenda) e V (Voz e estilo); o separador aberto é uma peça de teca com
    moldura cromada;
  - a barra de cima é o para-brisas, com o reflexo da luz, sobre um friso cromado;
  - os números do Painel estão em ecrãs azuis de bordo, com moldura de teca; os títulos pequenos são
    galhardetes azul-marinho, e os cartões têm a linha de água do casco;
  - os botões são de gelcoat com aro cromado, o principal é azul-marinho e os que enviam emails levam o aro
    vermelho e branco de uma boia; as caixas de seleção são interruptores basculantes, com luz azul;
  - os passos das Respostas são pontos da rota (WP1 a WP4), a Agenda é o diário de bordo e a caixa de
    entrada vazia lança âncora.
- É a base do tema: as palavras dos títulos, a roda do leme como seletor, o relógio de bordo e os
  instrumentos de cada imóvel chegam nas próximas versões. Os outros temas não mudam.

## α.25.1 — 24/09/2026

- **O tema «90's Ferrari» passa a chamar-se «90's RacingCar»:** um nome genérico, sem marca. Por dentro
  continua a ser `racing`, por isso quem o tinha escolhido continua com ele. O aspeto não muda.

## α.25.0 — 24/09/2026

- **Um depósito de tokens por imóvel**, porque é aí que se controla melhor. Enche-se no painel de cada imóvel,
  por baixo do mostrador do combustível («Encher»). Cada imóvel só gasta do seu e, vazio, só a API desse
  imóvel se desliga (o servidor também recusa); o copiar/colar continua. O depósito comum que já tinhas (5 €)
  passa a valer para cada imóvel, desde o mesmo momento, até encheres o de cada um. No Painel, o cartão
  mostra agora os depósitos de todos os imóveis, cada um com o seu mostrador.
- **€ = US$, sem conversões:** o câmbio desaparece da página, e os custos da OpenAI aparecem diretamente em
  euros.
- **Gasolina das visitas:** um mostrador pequeno ao lado do combustível, igual a ele, mas que só vai
  somando litros. Por baixo dos mostradores, o **computador de bordo** guarda a distância da agência ao
  imóvel (só ida) e o consumo do carro (7 L/100 km por omissão). Cada dia com visitas já começadas conta como
  uma ida e volta; os dias marcados à frente aparecem à parte.
- **O tema RedRacing passa a chamar-se «90's Ferrari».** A escolha fica guardada: quem o tinha escolhido
  continua com ele.

## α.24.0 — 24/09/2026

- **Tema RedRacing, segunda versão: um cockpit de GT italiano dos anos 90.** Fibra de carbono no fundo, no
  Painel e no quadro de instrumentos; nogueira lacada na barra lateral; pele preta com costura vermelha nos
  cartões; alumínio escovado e cromados. Tudo desenhado na própria página: nada vem de fora.
- **Botões como interruptores:** os normais são interruptores pretos que afundam ao clicar; os principais,
  o botão vermelho de arranque num aro cromado; os que enviam emails («Enviar só este», «Enviar N
  email(s)», o ponto de situação) têm a moldura amarela e preta de um interruptor protegido, para lembrar
  que dali sai algo a sério. As caixas de seleção são interruptores de alavanca cromados, as listas têm um
  botão rotativo serrilhado e as caixas de texto são de pele com costura.
- **A navegação é uma caixa de velocidades:** cada separador é uma mudança (1 Painel … 6 Voz e estilo) e,
  na barra lateral, uma grelha aberta com manete de nogueira muda de posição, passando pelo ponto morto,
  quando mudas de separador. Também podes clicar na mudança.
- **Dois mostradores novos no painel de cada imóvel.** A **temperatura** é o tempo médio de resposta, e o
  seu máximo (o H) define-se imóvel a imóvel, por baixo do mostrador (24 h por omissão). Acima do máximo, a
  agulha encosta ao H, o visor pisca e acende a luz «Sobreaquecido». O **velocímetro** mostra os pedidos
  por dia no período escolhido. Ficam quatro: temperatura, conta-rotações, velocímetro e combustível.
- Luzes de aviso com os símbolos dos carros (motor, travão, temperatura, bomba de gasolina); relógio
  analógico de tablier no Painel; luzes de mudança acesas enquanto a página trabalha; faixa tricolor no
  topo; os passos 1.ª a 4.ª em Respostas; a Agenda como livro de bordo de páginas creme; bandeira de xadrez
  quando não há emails pendentes; patilhas «−» e «+» para mudar de imóvel.
- **Palavras do tema:** no RedRacing os títulos falam de carros (Cockpit, Box, Garagem, Paddock,
  Afinação…). Os botões e as ações ficam com os nomes de sempre.
- **Nos temas simples, o máximo por imóvel também conta:** o mostrador de horas vai de 0 ao máximo desse
  imóvel e acende «Resposta lenta» quando a média o passa.
- **Preparado para mais temas ricos (iate, luxo…):** cada um é um ficheiro em `frontend/themes/` e uma
  entrada em `SKINS` no `app.js`, com as suas palavras, os seus mostradores, o seu seletor de separadores e
  o seu relógio, feitos a partir dos mesmos números.
- Corrigido: a faixa dos passos 01–04 tinha fixa a cor do tema Noite (ficava azul-escura e quase ilegível
  nos temas Dia e Âmbar); e a lista do «Fecho», em Voz e estilo, aparecia esticada.

## α.23.0 — 24/09/2026

- **Depósito da API, como combustível:** no Painel, o cartão da API passa a ser um depósito com
  indicador E–½–F. Enches com um valor em euros (5 € por omissão) e cada pedido à API vai gastando
  (estimativa a partir dos tokens, convertida com o câmbio que indicas). Na reserva (menos de 15 %) acende
  a luz «Reserva»; vazio, os três botões da API desligam-se até voltares a encher — e o servidor também
  recusa, não só os botões. O copiar/colar com o ChatGPT nunca é afetado. No painel de cada imóvel, o
  mostrador do custo passou a ser o do depósito, com o que esse imóvel já gastou.
- **Novo tema «RedRacing»:** preto e vermelho, fibra de carbono, títulos em itálico, números como
  mostradores digitais, relógio LCD vermelho, faixa vermelha e amarela no topo — e o painel de
  instrumentos completo, com o conta-rotações amarelo.
- **Nos outros temas (Noite, Dia, Índigo, Âmbar), mostradores redondos mais pequenos e simples:** nas
  cores do tema, só com os números das pontas, contadores simples e luzes discretas.
- O painel de cada imóvel atualiza-se sempre que abres Imóveis (antes podia mostrar números antigos
  depois de enviares ou encheres o depósito noutro separador).

## α.22.0 — 24/09/2026

- **«Enviar só este», em cada email de Respostas:** envia só esse, com o texto que está na caixa nesse
  momento (mesmo que o tenhas escrito ou alterado à mão), depois de confirmares o destinatário e o assunto,
  e ele sai da lista sozinho. É o mesmo caminho seguro do passo 04 (guardar → pré-visualizar → enviar), só
  que para um email, sem teres de desmarcar os outros.
- Know-how e voz (dados, não código): o lembrete do imóvel a seguir à saudação passa a ser «🏠 título —
  link», sem «Referente ao» nem nenhuma palavra a traduzir; e o tom fica sempre formal e impessoal, sem
  «estamos ansiosos», «até já» e semelhantes.

## α.21.0 — 24/09/2026

- **Imóveis: um imóvel de cada vez, num slider** (setas, pontos, as setas do teclado ou deslizar no
  telemóvel), em vez de cartões lado a lado. O imóvel escolhido fica lembrado neste browser.
- **Painel do imóvel, no topo, em estilo painel de instrumentos retro:** conta-rotações amarelo ao centro
  (emails por responder, zona vermelha a partir de metade da escala), mostradores escuros ao lado (tempo
  médio de resposta, com a zona vermelha a partir das 24 h; custo da API deste imóvel), conta-quilómetros
  (respostas enviadas, clientes ativos, contactos, visitas marcadas), luzes de aviso (rascunhos,
  bloqueados, atenção, só noutra data, blacklist, greylist) e o gráfico de pedidos e respostas só deste
  imóvel, com o mesmo período do Painel.
- **Blacklist e greylist lado a lado, com a última ronda de visitas**, logo por baixo: ver, tirar alguém
  da lista ou acrescentar um email à mão, em cada uma. «Ignorar sempre» vai para a blacklist; «Não tem
  interesse», para a greylist.
- **«+ Novo imóvel» é agora uma vista própria**, separada dos imóveis existentes; «Editar dados do anúncio»
  abre-a já preenchida («Editar REF»), e ao guardar volta ao slider nesse imóvel.
- No Painel, cada imóvel da carteira tem «Painel do imóvel →», que abre esse imóvel em Imóveis.
- Os envios e os pedidos à API passam a registar o imóvel. Os envios antigos são atribuídos pelos IDs que
  cada fila guarda; os pedidos à API anteriores a 24/09 não guardaram o imóvel e contam só no total do Painel.

## α.20.1 — 24/09/2026

- **A lista a ignorar passa a guardar o motivo.** Novo botão em cada email, «Não tem interesse», para
  quando é o próprio cliente a dizer que não quer continuar — o efeito é o mesmo do «Ignorar sempre»
  (nunca mais entra na fila, não recebe mais nada), mas fica registado o porquê, visível em Imóveis →
  «Clientes a ignorar».

## α.20.0 — 24/09/2026

- **Lista a ignorar, por imóvel.** Em cada email, «Ignorar sempre» retira-o da fila e passa esse cliente a
  ser ignorado nesse imóvel: escreva o que escrever, nunca mais entra em Respostas; também deixa de
  receber propostas de visita, lembretes, pedido de consentimento ou o email de «visitas fechadas». Nada é
  apagado (ao contrário do apagar por RGPD em Contactos) — só fica marcado. Gere-se em Imóveis → «Clientes
  a ignorar»: vê quem lá está, tira alguém da lista, ou acrescenta um email à mão, mesmo antes de escrever.

## α.19.0 — 23/09/2026

- **A «Ronda de visitas» agora mostra a última ronda de cada imóvel**, logo por baixo do botão «Iniciar
  ronda»: o dia e o intervalo propostos, e cada cliente com o estado atual — hora marcada (com a hora),
  enviado e a aguardar resposta, ainda não enviado (rascunho por tratar), ou recusou/só pode noutra data.
  Antes, depois de enviar os rascunhos não havia onde voltar a ver quem tinha recebido o quê.

## α.18.1 — 23/09/2026

- **Cada rascunho diz agora se está «Guardado» ou «Por guardar»**, junto ao botão "Guardar rascunho" —
  antes não havia nenhuma pista de que um texto editado (colado do ChatGPT ou escrito à mão) ainda não
  tinha sido gravado. Muda em tempo real enquanto escreves, sem esperares pelo clique.

## α.18.0 — 23/09/2026

- **Novo cartão no Painel, ao lado do Ponto de situação diário: «Ronda de visitas».** Escolhe o imóvel, o
  dia e o intervalo, clica «Iniciar ronda» e cria de imediato uma proposta de visita para todos os clientes
  ativos desse imóvel (os mesmos que já apareciam elegíveis em Imóveis → Visitas → Escolher clientes) —
  sem teres de os selecionar um a um. Pede confirmação antes de criar («Vais avisar N cliente(s)…»). As
  propostas ficam na fila de Respostas, por rever e enviar como qualquer outra; o painel detalhado em
  Imóveis continua para quando quiseres escolher só alguns clientes à mão.
- **As propostas de visita passam a levar o histórico da conversa para o prompt**, tal como as outras
  respostas — antes não levavam nenhum, porque são criadas fora da leitura normal de emails. Também deixa
  de dizer "Mensagem nova" quando na verdade é o proprietário a propor a visita, não o cliente a escrever.

## α.17.1 — 23/09/2026

- **O cartão «Ponto de situação diário» passa a aparecer sempre no Painel**, mesmo sem rascunho ainda —
  antes ficava completamente invisível, e por isso a funcionalidade era impossível de descobrir. Agora
  mostra «Ainda sem rascunho», com os botões «Guardar»/«Enviar» visíveis mas desativados, e o rato por
  cima explica porquê (aparece só depois da próxima leitura, e só com destinatário definido).

## α.17.0 — 23/09/2026

- **Campo novo em Voz e estilo: «Enviar o ponto de situação diário para».** O backend já sabia preparar e
  enviar este resumo (rascunho a cada leitura, envio só com clique em «Enviar», como tudo o resto) desde
  22/09, mas a página nunca teve onde escrever o destinatário — ficava sempre vazio e a funcionalidade,
  invisível, nunca chegou a arrancar. Configurei já o teu (fica só no `data/voice.json`), a pedido.
- O painel «Ponto de situação diário» aparece a partir da próxima leitura de emails (é aí que o rascunho
  é preparado); até lá continua vazio, como sempre esteve.

## α.16.3 — 23/09/2026

- **Causa real encontrada (não só "o modelo perde a atenção"):** a nota do exemplo era uma regra de
  comportamento ("não perguntes X salvo se o cliente falar nisso primeiro"), não um facto a citar — e a
  regra da base de conhecimento só falava em "responder a perguntas do cliente". A IA lia isso como
  contexto para consultar, não como uma instrução a cumprir sempre, por isso perguntou na mesma. A regra
  agora diz explicitamente que a base tem os dois tipos de conteúdo — factos e regras de comportamento —
  e que as regras contam tanto como a voz e as interações, não como um extra.
- Corrigido também `backend/templates/profile.example.json` (o modelo usado para imóveis novos, reais ou
  de demonstração): tinha uma cópia antiga desta regra, presa desde a criação de cada imóvel. Os dois
  imóveis reais já em uso nunca tinham este campo preenchido, por isso já usavam a regra nova assim que o
  código foi atualizado (α.16.2); só os imóveis criados a partir de agora precisavam desta correção.

## α.16.2 — 23/09/2026

- **Reforço no prompt para usar melhor as notas e o conhecimento do imóvel (RAG).** Confirmei que o
  `notas.md` chega sempre ao prompt, igual nos dois caminhos (API e copiar/colar) — não era aí o
  problema. O relatado foi a IA simplesmente ignorar uma nota relevante ao responder via API em lote.
  Regra da base de conhecimento mais direta ("usa-a sempre, por pequena que pareça"), e um lembrete
  igual repetido mesmo antes dos emails (perto do fim de um prompt longo, onde é mais fácil perder-se
  uma regra lida lá em cima). Mitiga uma falha de atenção do modelo; não é garantia — se voltar a
  acontecer, o texto exato da nota e da resposta ajuda a apanhar o resto.

## α.16.1 — 23/09/2026

- **A etiqueta da versão, no canto, agora diz «version: vα.X.Y» e, por baixo, a data e a hora em que esta
  página arrancou** (`mac/web.command`/`bot-mail web`) — não há um passo de compilação nesta app, por isso
  "build" aqui é literalmente quando este processo começou a correr com este código.

## α.16.0 — 23/09/2026

- **Novo separador «Agenda»**: a semana em página de papel, ao estilo Filofax — um dia por página, lado a
  lado, com as propostas de visita e as marcadas de todos os imóveis (ou de um só, a filtrar). Botões
  «Semana anterior / Esta semana / Semana seguinte» para navegar. Não usa nenhum pedido novo ao servidor:
  lê os mesmos dados que já estavam em Imóveis → Visitas.
- Exportar para o teu calendário (Google/Apple/.ics) fica para mais tarde, a pedido — por agora gere-se
  só aqui.

## α.15.0 — 23/09/2026

- **Lista de clientes ativos, persistente, em cada imóvel** (Imóveis → «Clientes ativos»): quem já
  escreveu, o estado (ativo, por responder, visita marcada, recusou, só noutra data) e quantas interações.
  Já não é preciso clicar em «Escolher clientes» para ver quem está em jogo.
- **«Analisar antes de propor»**: resume o que os clientes ativos já disseram — disponibilidade, urgência,
  preferências de horário — antes de escolheres o dia e o intervalo das visitas. Duas vias, como o resto:
  «Criar prompt de análise» + «Copiar» para o ChatGPT (a resposta lê-se lá, não precisa de voltar à
  página), ou «Analisar via API», que mostra o resumo logo na página. É só leitura: nunca grava nada.
- «Fechar visitas» continua a ser o único evento de fim de imóvel (vendido, arrendado ou desistiu contam
  todos como o mesmo «fechado» — decidido a pedido, para não criar um estado novo por agora).

## α.14.0 — 23/09/2026

- **O calendário retro voltou a aparecer.** Tinha uma regra que o escondia sempre que a janela ficava
  abaixo de 1150px de largura; agora nunca desaparece — o cabeçalho do Painel quebra linha em vez disso.
- **Novo botão, em cada email: «Guardar e refazer esta resposta (API)»**, ao lado de «Guardar no
  conhecimento». Guarda o facto novo e já pede à API da OpenAI um rascunho novo para esse email, a usar
  esse conhecimento — sem teres de ir a «Gerar respostas via API» à parte. Precisa da chave OpenAI
  configurada, como o resto da via API.

## α.13.0 — 23/09/2026

- **Relógio e calendário retro no Painel**, ao lado do título: hora ao segundo e um mês em miniatura, com
  hoje destacado e um pontinho nos dias em que já há uma visita marcada (em qualquer imóvel) — passa o
  rato por cima para ver quem. Não é só decorativo: usa as visitas que já estavam em «Imóveis → Visitas»,
  sem nenhum pedido novo ao servidor. Escondido em ecrãs estreitos, para não apertar o resto do cabeçalho.

## 0.12.0 — 23/09/2026

- **Via alternativa por API, ao lado de Criar prompt/Copiar:** no passo 02, o botão «Gerar respostas via
  API» faz o mesmo que os passos 02+03 à mão — cria o prompt, obtém a resposta e guarda os rascunhos —
  mas indo diretamente à API da OpenAI (modelo `gpt-4o` por omissão), sem passares pelo ChatGPT.
- **A regra de aprovação humana não tem exceções:** a API só produz rascunhos, tal como o copiar/colar;
  continuas a rever e a confirmar o envio da mesma forma, sempre.
- **Chave OpenAI opcional**, guardada no Keychain com `mac/openai_key.command` (confirmada contra a API
  antes de ser guardada, como a App Password). Sem chave, o botão explica o que falta e o copiar/colar
  continua a funcionar exactamente como antes.
- Sem dependências novas: o pedido à OpenAI usa só a biblioteca padrão do Python (`urllib`).

## 0.11.0 — 23/09/2026

- **Novo separador «Contactos»** para gerir o `data/contactos.csv`:
  - lista com filtros por imóvel, estado RGPD e texto (nome, email, telefone), e quantas respostas teve cada um;
  - nome, telefone e estado RGPD editáveis na própria linha; uma mudança de RGPD feita aqui fica com a data e
    «alterado à mão na página» como prova;
  - «Acrescentar à mão» para quem contactou por telefone ou pessoalmente, com a fonte à escolha;
  - «Apagar» a pedido do cliente (direito ao apagamento): sai do CSV, da conversa, dos emails por responder e
    das visitas marcadas desse imóvel; os mesmos emails nunca voltam a entrar;
  - «Descarregar CSV», pronto a abrir no Excel ou no Numbers.
- Os clientes respondidos antes de o registo existir (22/09) entram no CSV ao abrir o separador, com nome e
  imóvel; o dia do primeiro contacto fica em branco, porque não se sabe.

## 0.10.1 — 22/09/2026

- **«Pedidos recebidos» no gráfico passa a contar todos os emails de clientes**, pelo dia em que chegaram, e
  não só os que ainda estão na fila. Os antigos são datados pelo envio da resposta menos as horas que o
  cliente esperou; a partir de agora, cada leitura regista o dia de chegada de cada email.
- Emails feitos pelo programa (propostas de visita, lembretes, fecho, consentimento) deixam de contar como
  pedidos e deixam de mexer no «Tempo médio até resposta».

## 0.10.0 — 22/09/2026

- **Hover de «Respostas enviadas» com a lista de quem foi respondido:** primeiro nome, dia do primeiro
  pedido (quando já está no registo de contactos), dia da última resposta e número de interações. Primeira
  exceção à regra de o Painel não mostrar clientes: só o primeiro nome, nunca email nem telefone.

## 0.9.1 — 22/09/2026

- **Aviso quando se salta um passo:** pré-visualizar (passo 04) com emails ainda sem rascunho diz quais são e
  o que falta fazer, em vez de «reply_text vazio.». Com uma resposta colada no passo 03 por guardar, a página
  avisa antes de continuar.

## 0.9.0 — 22/09/2026

- **Gráfico do Painel com período à escolha:** últimos 3 dias, última semana, últimas 2 semanas, último mês e
  últimos 3 meses (este com uma barra por semana, para continuar legível). A escolha fica lembrada no browser.
- Passar o rato por cima de uma barra mostra o dia (ou a semana) e o número.

## 0.8.0 — 22/09/2026

- **Números do Painel clicáveis:** «Pedidos por responder», «Rascunhos prontos», «Bloqueados» e «A precisar de
  atenção» abrem a fila do imóvel em Respostas, onde estão esses emails.
- **Hover com a divisão por imóvel:** por cima de «Respostas enviadas» (e dos outros, quando há mais de um
  imóvel) aparece quantos são de cada imóvel. O Painel continua sem nomes nem contactos de clientes.

## 0.7.1 — 22/09/2026

- Nome e versão mais legíveis no canto: «Real Estate» e «AI Assistant» em duas linhas, «by BigLearn PT» por
  baixo, e a versão numa etiqueta própria. No telemóvel, tudo numa linha.

## 0.7.0 — 22/09/2026

- **Novo nome: «Real Estate AI Assistant, by BigLearn PT»**, no canto e no título da página (antes: bot_mail).
- **Versão visível na página** e este `CHANGELOG.md`.

## 0.6.0 — 22/09/2026 (ponto de partida)

Tudo o que existia antes de haver versões conta como 0.6.0, incluindo o que se fez neste dia: registo de
contactos com RGPD, lembretes aos 2 e 4 dias, visitas fechadas, pedido de consentimento, ponto de situação
diário, a opção de idioma com tradução em inglês, cartões de imóvel sem espaço para fotografia quando não há,
botões com «A trabalhar…» até terminarem, «Criar prompt» e «Copiar» separados, e os passos 01–04 marcados
como feitos (com a confirmação do passo 03 a ficar visível depois de guardar).
