# Changelog — ARIA, by BigLearn PT

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
