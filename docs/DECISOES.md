# Decisões

As decisões de produto e de arquitetura, da mais recente para a mais antiga. Cada uma diz o que se decidiu
e porquê. O código em pausa fica no histórico do Git, na tag `referencia-python`.

## 24/09/2026, noite (3): depósito por imóvel, € = US$ e a gasolina das visitas (α.25.0)

**Decisão.**
- **Um depósito de tokens por imóvel**, guardado em `properties/<REF>/painel.json` (`tank`: tamanho e quando
  foi cheio). Cada imóvel só conta os seus pedidos à API (os eventos `openai_usage` têm `reference` desde
  24/09). `require_fuel(ref)` recusa só o imóvel vazio, e na página os botões da API seguem o imóvel a que
  pertencem (`data-ref`, ou a fila aberta em Respostas).
- **O depósito comum antigo (`data/api_fuel.json`) é o ponto de partida**, sem migração escrita: um imóvel
  que ainda não foi cheio usa o tamanho e o momento desse depósito, mas só com o seu próprio gasto. Nos
  dados reais, cada imóvel fica com 5 €, quando antes eram 5 € para os dois. Como é o utilizador que controla
  cada depósito, isso fica à vista e ele ajusta cada um quando quiser.
- **€ = US$ para este assistente**, por escolha do utilizador: não há câmbio para escrever nem conversão
  na página. O custo estimado da OpenAI (em US$) conta como euros, e o `usd_to_eur` antigo é ignorado.
- **Gasolina das visitas = gasolina a sério**, escolhida numa pergunta com três opções: litros = dias de
  visita já começados × 2 × distância (só ida) × consumo ÷ 100. Um dia com várias visitas conta como uma só
  ida e volta; os dias à frente contam à parte e só entram quando chegam. A distância e o consumo ficam no
  `painel.json` de cada imóvel (sem distância, o mostrador diz «—», não zero). O consumo é por imóvel (7
  L/100 km por omissão) para não criar uma definição global só para isto.
- **O tema chama-se «90's Ferrari»**, a pedido. O `id` continua a ser `racing`, para não perder a escolha
  guardada no browser. Continua sem logótipos. Nota: é um nome de marca num repositório público, usado só
  como rótulo de tema, por decisão do utilizador.

**Porquê.** Pedido direto do utilizador: «depósito tokens por imóvel, pois é aí que se controla melhor»,
«€=USD… nada de conversões no UI, pode estar hardcoded», um mostrador «que vai somando… em litros, ao
lado, menor» e «tema passa a 90's Ferrari».

## 24/09/2026, noite (2): RedRacing, segunda versão, e a temperatura imóvel a imóvel (α.24.0)

**Decisão.**
- **Tema rico ("skin") separado dos temas simples.** O RedRacing passou para `frontend/themes/racing.css`
  (a API serve os `frontend/themes/*.css` que existirem ao arrancar) e para a entrada `SKINS.racing` do
  `app.js`, com quatro encaixes: palavras (os títulos marcados `data-word`), instrumentos (feitos a partir
  de `panelSignals`: por responder, tempo médio e o seu máximo, pedidos por dia, depósito), seletor de
  separadores (aqui, a caixa de velocidades) e relógio analógico. Os temas simples não usam nenhum. Um tema
  iate ou de luxo é outro ficheiro e outra entrada, sem mexer nos que existem.
- **Temperatura = tempo médio de resposta; o H é o máximo de cada imóvel.** Fica em
  `properties/<REF>/painel.json` (novo, local, fora do Git): 24 h por omissão, de 1 a 720 h, gravado pelo
  endpoint `property/panel`. A escala vai de 0 ao máximo e a zona vermelha é o último quarto. Acima do
  máximo, a agulha encosta ao H, o visor pisca e acende «Sobreaquecido» (nos temas simples, «Resposta
  lenta»). Antes, a escala era fixa (0–48 h, com vermelho a partir das 24 h) e igual em todos os imóveis.
- **O depósito continua a ser um só**, para todos os imóveis, e cada imóvel mostra o que gastou dele. O
  pedido dizia «tal como no depósito de combustível é colocado imóvel a imóvel»; como o depósito atual é
  comum, isto fica como pergunta ao utilizador. Um depósito por imóvel é possível, porque os pedidos à API
  guardam o imóvel desde 24/09.
- **Velocímetro = pedidos recebidos por dia, no período do gráfico**, e não respostas enviadas (essas já
  estão no conta-quilómetros). A escala ajusta-se e começa em 0–10.
- **Os botões mudam só de aspeto:** os rótulos e o comportamento ficam iguais, sem passos nem cliques a
  mais. O único sinal novo é a classe `send-action` nos botões que enviam emails, que o RedRacing veste de
  interruptor protegido.
- **As palavras do tema só mudam títulos e subtítulos**, nunca botões, campos ou mensagens: em qualquer
  tema, quem usa a página tem de reconhecer sempre as ações.
- **Nada vem de fora:** a madeira, a pele e o carbono são SVG (ruído e deslocamento) e gradientes dentro do
  CSS. As fontes são as do sistema: DIN Alternate e Avenir Next Condensed, que o macOS já traz, e
  alternativas noutros sistemas.
- **Sem marcas:** nenhum logótipo nem nome de marca. O volante do canto e as placas de alumínio são
  genéricos.

**Porquê.** Pedido direto do utilizador: «Ferrari, Lamborghini, touring, carbono, madeira, anos 90»,
«carifica», «a temperatura do carro poderia ser o tempo médio de resposta e o valor máximo… imóvel a
imóvel» e «podemos ser go wild». Também avisou que vêm aí temas Yacht e Rolls-Royce, e por isso os encaixes
ficaram preparados já.

## 23/09/2026, ainda mais tarde (5): know-how de visitas separado, e o indicador de rascunho por guardar

**Decisão.**
- **`data/knowledge/visitas.md` novo, à parte de `know-how.md`** (dados reais, não vai para o Git): a
  secção "Visitas" que já existia dentro do know-how geral da agência foi movida para o ficheiro próprio,
  a pedido explícito ("vai para o tal -md de visitas"). Mecanismo igual ao resto — qualquer ficheiro
  `.md`/`.txt` em `knowledge/` entra no prompt, concatenado por nome; não foi preciso código novo, só
  organizar o conteúdo.
- **Regras novas nesse ficheiro, só para a confirmação da hora (4.ª interação):** escrever a hora com
  referência clara ao período do dia (ex.: meio-dia/12:00, 16:00/4 da tarde) para nunca haver ambiguidade;
  confirmar a morada do imóvel, exatamente como está no anúncio; e, se o imóvel tiver indicações de como lá
  chegar (Google Maps incluído), só as dar nessa confirmação — nunca antes, e nunca a quem não confirmou
  uma hora.
- **Os dados de morada/Google Maps por imóvel ainda não foram adicionados** — isso é conteúdo real,
  específico de cada imóvel, que o utilizador ainda vai escrever (no conhecimento desse imóvel, não no
  ficheiro comum da agência). Sem essa informação, a regra só diz ao assistente para a incluir quando
  existir; não inventa nada na falta dela (mantém-se a regra de nunca inventar factos).

**Porquê.** Pedido direto do utilizador. Mais uma vez, a distinção entre "regra de comportamento" (quando
dizer algo) e "facto" (o que dizer) importa: a regra do timing vive no know-how comum; o facto (a morada em
si) vive no imóvel a que pertence.

**Adenda, ainda no mesmo dia:** o utilizador apanhou "Propusemos um intervalo..." (passado) num rascunho
real da ronda de 40, numa primeira proposta — devia ser presente ("Propomos-lhe"), por ser a primeira vez
que se propõe aquela visita àquele cliente. Acrescentada regra em `visitas.md`, secção "Ao propor o
intervalo de visita (3.ª interação)". Não é a única frase possível que a IA pode escrever mal; esta é a que
apareceu e foi corrigida — outras podem aparecer e merecer o mesmo tratamento, uma de cada vez.

**Segunda adenda, mesmo dia:** o utilizador deu um estilo concreto, com exemplo, para a proposta de
visita — estrutura em três partes (organizar para o dia X, pergunta a hora mais conveniente ou a mais
cedo/mais tarde possível, e se nada servir pergunta a disponibilidade habitual nos dias seguintes). Isto
fecha, só agora por completo, o pedido original da "ronda de visitas" (sessão anterior, mesmo dia): "qual
seria a altura mais cedo e mais tarde" só estava implícito no intervalo proposto ("das X às Y"); agora está
explícito como pergunta ao cliente.

## 23/09/2026, ainda mais tarde (6): resumo da ronda, para saber onde ficou cada envio (α.19.0)

**Decisão.**
- **A lista de destinatários fica gravada na própria janela** (`agenda["windows"][i]["recipients"]`, em
  `visitas.json`), não só como contagem no log de eventos — sem isso não havia como reconstruir "a quem
  foi esta ronda" depois de os rascunhos saírem da fila (o envio remove-os de `data["emails"]`).
- **O estado de cada destinatário reaproveita `candidates()`**, a mesma função que já decide quem é
  elegível para uma nova ronda — sem duplicar lógica: marcado (com a hora), enviado e a aguardar resposta
  (`ok`), ainda por enviar (`pending` — o rascunho da própria proposta ainda na fila) ou recusou/só outra
  data.
- **Sem separador novo:** o resumo aparece dentro do próprio cartão "Ronda de visitas", por baixo do
  formulário — atualiza ao mudar de imóvel e sempre que o cartão volta a desenhar-se (que já acontece a
  seguir a quase qualquer ação, por causa do `renderSettings()`).

**Porquê.** Pedido direto do utilizador, depois de mandar 37 emails de uma ronda e não ter onde confirmar
que tinham saído bem. Sem isto, "Iniciar ronda" era uma ação sem retorno visível passado o primeiro toast.

## 24/09/2026, ainda à noite: depósito da API e tema RedRacing (α.23.0)

**Decisão.**
- **Depósito = um teto de gasto local, não um pagamento.** `data/api_fuel.json` guarda o tamanho (€), o
  câmbio usado e quando foi cheio; o que resta é o tamanho menos o gasto estimado desde esse momento. Não
  toca na conta da OpenAI nem no que ela cobra — é só um travão nesta app.
- **Em euros, com câmbio à vista:** a OpenAI cobra em US$ e o custo já é uma estimativa (tokens × tabela
  de preços); o pedido foi em euros, por isso o câmbio (0,90 € por US$ por omissão) é indicado e guardado a
  cada enchimento, e pode ser mudado no próprio cartão. Não se vai buscar o câmbio a lado nenhum: a página
  não carrega nada de fora.
- **Travão no servidor, não só nos botões:** `require_fuel()` recusa `prompt/generate` e a análise de
  visitas com o depósito vazio. Os botões da API (marcados `needs-fuel`) desligam-se e explicam porquê, e
  `run()` passou a respeitar `data-hold` para não os voltar a ligar no fim de um clique. O último pedido
  pode passar um pouco abaixo de zero: não se sabe o custo de um pedido antes de o fazer.
- **Sem depósito ainda = sem limite**, como antes; a partir do primeiro enchimento, o gasto anterior não
  conta.
- **O visual "Ferrari" completo passou a ser do tema RedRacing**, a pedido; nos outros temas os mostradores
  ficam mais pequenos, planos e nas cores do tema (só os números das pontas, sem aro cromado nem fundo de
  carbono). É o mesmo SVG, só o CSS muda por tema.

**Porquê.** Pedido direto do utilizador ("o custo da API é tipo combustível"; "um novo tema darkRedBlack").

## 24/09/2026, à noite: «Enviar só este», e o tom impessoal na voz (α.22.0)

**Decisão.**
- **Um envio de um só email, sem atalho à aprovação:** o botão faz o mesmo que o passo 04 para um email —
  guarda o texto da caixa, pede a pré-visualização (o token fica preso a esse texto exato, 15 minutos) e
  só envia depois de um `confirm()` com o destinatário e o assunto. Nenhum endpoint novo: a regra "nada sai
  sem aprovação humana" fica igual, só com menos cliques. Um email bloqueado não tem o botão.
- **O tom formal e impessoal foi para a voz** (`application_instructions`, "Comportamento geral" em Voz e
  estilo), não para o know-how: o pedido foi "manter formal e impessoal na voz", e é aí que o prompt junta
  saudação, fecho e assinatura. Acrescentado ao texto que já lá estava, sem o reescrever.
- **O lembrete do imóvel usa um ícone (🏠), não uma palavra:** «Referente ao» ficava em português num email
  em inglês, ou saía meio traduzido («for the Apartamento…»). O título e o link do anúncio não se traduzem.

**Porquê.** Pedidos diretos do utilizador, com exemplos reais de rascunhos.

## 24/09/2026, ainda mais tarde: Imóveis em slider, com painel de instrumentos por imóvel (α.21.0)

**Decisão.**
- **Números por imóvel a partir do que já existe, sem ficheiro novo.** `metrics()` passa a devolver, para
  cada imóvel, o gráfico, o tempo médio de resposta, o custo da API, os clientes por estado, as visitas
  marcadas e as contagens de blacklist/greylist. Os eventos antigos de envio não tinham o imóvel, mas
  cada fila guarda para sempre os IDs respondidos e retirados (`replied_message_ids`,
  `dismissed_message_ids`): é por eles que se atribuem. Somados, os números por imóvel batem certo com o
  total (verificado nos dados reais).
- **O custo antigo da API fica por atribuir, às claras.** Os pedidos anteriores a hoje não guardaram o
  imóvel, e os eventos à volta (`drafts_saved`) também não; adivinhar pelo envio seguinte seria um palpite.
  Contam no custo total do Painel, e o painel de cada imóvel diz quantos são e quanto custaram. A partir de
  agora, `openai_usage`, `send` e `drafts_saved` levam `reference`.
- **Blacklist e greylist guardadas como tipo** (`ignored_kind`: black/grey), não deduzidas do motivo — o
  motivo é texto livre. Para a única entrada anterior (com motivo, sem tipo), o motivo diz "greylist".
- **Painel de instrumentos desenhado à mão (SVG e CSS), como o gráfico:** nada é carregado de fora. Um
  painel escuro fixo em todos os temas, como um objeto físico dentro da página; o conta-rotações amarelo é
  um estilo, sem logótipos nem marcas. As escalas são fixas onde a zona vermelha quer dizer algo (24 h de
  resposta; metade da escala de emails por responder) e a agulha encosta ao fim se passar — o mostrador
  digital dá sempre o valor exato. A agulha anda de onde estava, não recomeça do zero a cada redesenho.
- **Um imóvel de cada vez, não um carrossel de todos:** os cartões têm alturas muito diferentes, e um
  carrossel com todos deixaria espaço vazio por baixo dos mais curtos.
- **«Novo imóvel» é uma vista, não um separador novo na barra lateral:** o formulário também serve para
  editar os dados do anúncio de um imóvel existente, por isso vive junto dos imóveis.

**Porquê.** Pedido direto do utilizador, incluindo o estilo ("retro gauges tipo ferrari car").

## 24/09/2026, mais tarde: lembrete do imóvel logo após a saudação (só dados, sem versão)

**Decisão.** Nova secção em `know-how.md` (agência, todos os imóveis): toda e qualquer resposta, em
qualquer interação, leva uma linha curta logo após a saudação a lembrar de que imóvel se trata — título,
localidade e link do Idealista — com um exemplo real para a IA seguir de perto. Pedido explícito do
utilizador, "em todas as interações" (não só na 1.ª). Vive no know-how geral, não no `visitas.md`: aplica-
se a toda a correspondência, não só à fase de agendar/confirmar visitas.

**Porquê.** Conteúdo real (`data/`), não código — sem bump de versão, como as outras edições ao
know-how/notas hoje.

## 24/09/2026: lista a ignorar, por imóvel (α.20.0)

**Decisão.**
- **Marca, não apaga.** Diferente da eliminação por RGPD (Contactos → Apagar), que remove tudo, ignorar só
  põe `conversation["ignored"] = true` — a conversa e o histórico ficam, só deixam de gerar ação. Motivo:
  são pedidos diferentes — RGPD é um direito do cliente a ser esquecido; ignorar é uma decisão do
  proprietário sobre com quem continua a negociar, sem apagar o rasto de que houve contacto.
- **Por imóvel, não pela conta toda.** Um cliente pode não interessar-lhe o Ramada mas ainda ser legítimo
  no Campo de Ourique — a conversa já vive por imóvel (`data["conversations"]`), a marca segue a mesma
  divisão.
- **Silencioso a sério:** não é só "bloqueado, mostra um aviso" (como já existe em `never_reply_to`, para
  o remetente do portal e a própria conta — esse é um mecanismo de segurança diferente, visível de
  propósito). Ignorar não aparece em lado nenhum a pedir atenção: nunca mais entra na fila, e ficou de fora
  de todos os sítios que já juntam conversas em lote — `candidates()` (por isso também some de "Clientes
  ativos", da ronda de visitas e do prompt de análise), lembretes, pedido de consentimento e o email de
  «visitas fechadas».
- **`candidates()` como único sítio a filtrar**, em vez de espalhar o `if conversation.get("ignored")` por
  cada função que decide quem contactar: mais seguro (uma falha em vez de quatro a manter sincronizadas) —
  exceto os três lugares que juntam clientes em lote fora do candidates() (fechar visitas, lembretes,
  consentimento), que continuam a precisar da própria verificação, por não passarem por ali.

**Porquê.** Pedido direto do utilizador, a partir de um cliente real que respondeu "I am not interested."

**Adenda, ainda no mesmo dia:** pedido de uma "grey list" para clientes que se autoexcluem, distinta da
"blacklist". Perguntado o que devia mudar na prática: só o motivo fica registado, o efeito é igual. Em vez
de duplicar o mecanismo, `set_ignored` ganhou um `reason` opcional (guardado em
`conversation["ignored_reason"]`, limpo quando se deixa de ignorar) e um segundo botão no email, «Não tem
interesse», que chama o mesmo `api/contacts/ignore` com um motivo já preenchido. «Ignorar sempre» continua
sem motivo (a decisão é do proprietário, não precisa de justificação registada).

## 23/09/2026, ainda mais tarde (4): «Ronda de visitas» no Painel (α.18.0)

**Decisão.**
- **Atalho, não substituição:** o pedido do utilizador ("um botão que inicia uma ronda") reaproveita
  100% do backend já existente (`propose_visits`) — o único código novo é o botão que salta o passo
  "Escolher clientes" e seleciona automaticamente todos os elegíveis (estado `ok`). O painel detalhado em
  Imóveis → Visitas fica como está, para quando o proprietário quiser escolher só alguns.
- **Posição:** ao lado do «Ponto de situação diário» no Painel, a pedido explícito do utilizador — os dois
  ficam lado a lado na mesma linha (reaproveita a grelha de 2 colunas do dashboard).
- **Encontrado a construir isto:** as propostas de visita nunca levavam o histórico da conversa ao prompt,
  ao contrário de todas as outras respostas (a funcionalidade de histórico, de mais cedo neste mesmo dia,
  só cobria emails vindos de uma leitura — as propostas são criadas à parte). Corrigido: `propose_visits`
  agora tira uma fotografia do histórico da conversa, tal como o `read()` já fazia. Também deixou de dizer
  "Mensagem nova" nestas propostas — nunca é nova, é o proprietário a propor, não o cliente a escrever.
- Confirmação antes de criar («Vais avisar N cliente(s)…»), como o resto das ações em lote desta app
  (fechar visitas, etc.); nenhuma das propostas sai sem revisão — ficam `pending` na fila de Respostas.

**Porquê.** Pedido direto do utilizador (23/09), com a localização confirmada por eles próprios depois de
verem o cartão do ponto de situação. A falta de histórico nas propostas de visita era uma inconsistência
que só apareceu ao seguir o pedido "sai email de reply com o histórico" até ao fim — não avisada
previamente, mas claramente dentro do espírito do pedido.

## 23/09/2026, ainda mais tarde (3): campo em falta para o ponto de situação diário (α.17.0)

**Decisão.**
- **Encontrado a investigar uma pergunta do utilizador** ("estás a enviar algum resumo para a minha
  conta?"): o backend do ponto de situação diário (`service.prepare_digest`/`send_digest`, de 22/09) estava
  completo e testado (`tests/test_digest.py`), mas a página nunca teve um campo para o destinatário
  (`digest_recipient`) — só existia se alguém o escrevesse à mão no `voice.json`. Por isso a funcionalidade
  nunca arrancou nesta pasta: sem destinatário, `prepare_digest` nem cria o rascunho.
- Acrescentado o campo em Voz e estilo, e configurado o do utilizador (só no `data/voice.json`, fora do Git) via
  `service.save_voice`, com o resto dos campos lidos e reenviados sem alteração — o mesmo caminho de
  validação que a página usaria, sem editar o `voice.json` à mão.
- Confirmado, a investigar: não há nenhum agendamento (`launchd`) instalado neste Mac, e o envio continua a
  exigir sempre um clique («Enviar»); nada é enviado sozinho, agora nem antes.

**Porquê.** Um "já está construído" no código nem sempre quer dizer "usável" — vale a pena verificar a
interface, não só o backend e os testes, antes de dar uma funcionalidade por entregue.

## 23/09/2026, ainda mais tarde (2): separador Agenda, semana a semana (α.16.0)

**Decisão.**
- **Filofax a sério, não uma grelha tipo Google Calendar:** uma página por dia, lado a lado (7 numa semana),
  com as entradas listadas por hora — não uma grelha de horas vazias à espera de eventos. Mais simples de
  construir e de ler quando há poucas entradas por dia, que é o caso aqui (propostas e marcações de visita,
  não uma agenda cheia).
- **Sem pedido novo ao servidor:** lê `settings.properties[].visits.windows` e `.slots`, já carregados para
  o separador Imóveis. O backend já só devolve janelas/marcações a partir de hoje (`load_visits` filtrado em
  `service.py`), por isso a Agenda nunca mostra o passado — aceitável para um planeador, não um histórico.
- **Navegação por semana (anterior/esta/seguinte) e filtro por imóvel**, sem guardar estado entre sessões:
  reabrir o separador volta sempre à semana atual.
- **Exportar para um calendário externo continua por fazer**, tal como já estava decidido em 23/09 (entrada
  anterior): "por agora gerimos aqui" foi pedido explícito do utilizador, não esquecimento.

**Porquê.** Terceiro e último passo do pedido de 23/09 (depois da lista de clientes ativos e da análise por
IA), pela ordem que o utilizador escolheu quando perguntado. O desenho em páginas por dia (em vez de grelha)
foi escolha da IA, não confirmada previamente com o utilizador — fica registada como tal, para ajustar se o
utilizador preferir depois de usar.

## 23/09/2026, ainda mais tarde: clientes ativos, análise por IA e o plano da Agenda semanal (α.15.0)

**Decisão.**
- **Fim de imóvel é um só evento: «Fechar visitas».** Vendido, arrendado ou o proprietário desistir contam
  todos como o mesmo estado (`closed_at` em `visitas.json`), sem um campo novo para o motivo. Se algum dia
  fizer falta relatar o motivo, é mais barato acrescentar um campo opcional do que manter dois eventos
  paralelos a manter sincronizados desde já.
- **A lista de clientes ativos é persistente, não atrás de um clique.** Reaproveita `visit_candidates()`
  (sem alterações no backend): cada cartão de imóvel já a mostra aberta.
- **A análise por IA nunca escreve nada.** Só lê: histórico das conversas dos clientes ativos, resumido
  para ajudar a escolher o dia e o intervalo. Não usa `response_format: json_object` (só a geração de
  respostas precisa de JSON) nem passa por `parse_replies`; o resumo não é um rascunho.
- **Duas vias, as duas completas:** copiar/colar com o ChatGPT (a resposta fica só na conversa do ChatGPT;
  não é preciso trazê-la de volta à página) e via API, com o mesmo botão/padrão de «Gerar respostas via
  API». Ao contrário da decisão de 23/09 sobre o botão de geração de respostas (só API), aqui o pedido foi
  explícito para manter também o caminho sem chave.
- **Próximo passo, ainda por construir:** um separador «Agenda», semana a semana, com as propostas e
  marcações de todos os imóveis — visual novo, não uma tabela. Exportar para um calendário externo (.ics)
  fica para depois; por agora gere-se só aqui.

**Porquê.** Pedido direto do utilizador (23/09), com as escolhas confirmadas por perguntas diretas antes de
construir: uma exceção *deliberada* à regra de 23/09 (API path é sempre a via extra, nunca obrigatória) tem
de ficar registada como tal, não perdida como "esqueceram-se de fazer o copiar/colar".

## 23/09/2026, mais tarde: via alternativa por API da OpenAI (v0.12.0)

**Decisão.** Reverte, em parte, a decisão de 18/09 «Sem API de IA» — só para quem escolher configurá-la.

- **Botão extra, não substituição.** «Gerar respostas via API», ao lado de «Criar prompt», no passo 02. O
  copiar/colar com o ChatGPT continua a existir tal como está, para quem não quiser (ou não puder) usar a
  API da OpenAI.
- **A aprovação humana antes de enviar não tem exceção.** A API só substitui o troço «copiar o prompt →
  colar no ChatGPT → colar a resposta»: o resultado entra na fila como rascunho, revês no passo 01 e
  confirmas o envio no passo 04, exactamente como hoje.
- **Modelo: `gpt-4o`,** escolhido pelo utilizador; pode ser trocado por `openai_model` em `config.json`
  (por agora só à mão, sem campo na página).
- **Chave no Keychain,** com o mesmo padrão da App Password: `mac/openai_key.command` pede a chave, testa-a
  contra a API da OpenAI antes de a guardar (uma chave errada nunca fica gravada), e nunca passa pela
  página nem por um ficheiro do projeto.
- **Sem dependências novas.** O pedido à API da OpenAI usa só `urllib` (biblioteca padrão), como o resto do
  projeto (IMAP e SMTP também são só biblioteca padrão).

**Porquê.** O utilizador tem contas muito ativas e quer uma via mais rápida para lotes grandes; copiar e
colar deixa de compensar a partir de um certo volume. A chave é dele e o custo por pedido é dele: por isso
fica opcional, e nunca substitui a revisão humana, que continua a ser a proteção principal contra uma
resposta errada sair para um cliente.

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
