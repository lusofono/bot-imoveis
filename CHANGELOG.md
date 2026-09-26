# Changelog — Real Estate AI Assistant, by BigLearn PT

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
