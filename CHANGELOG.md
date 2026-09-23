# Changelog — Real Estate AI Assistant, by BigLearn PT

A versão aparece no canto superior esquerdo da página e vem de um só sítio: `version` em `pyproject.toml`.
Cada pedido que muda a página ou o backend sobe a versão e fica registado aqui, do mais recente para o mais
antigo:

- **PATCH** (0.7.0 → 0.7.1): uma afinação ou correção pequena;
- **MENOR** (0.7 → 0.8): uma funcionalidade ou pedido novo;
- **MAIOR** (0.x → 1.0, 1.x → 2.0): uma mudança grande no funcionamento.

O porquê de cada decisão está em `docs/DECISOES.md`; aqui fica só o quê.

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
