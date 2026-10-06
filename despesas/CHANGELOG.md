# Despesas — alterações

A mais recente primeiro. A versão está no ficheiro `VERSION` (a página mostra-a no rodapé).

## 0.3.0 — 06/10/2026

- **Confirmação do pagamento:**
  - a mensagem para o inquilino pede que confirme depois de pagar, se possível com o comprovativo;
  - o «Abrir email» põe a caixa das faturas em CC, para a resposta chegar à aplicação.
- **Respostas dos inquilinos:**
  - os emails do inquilino (o endereço na pasta do imóvel) passam a ser lidos como respostas, não como faturas;
  - os anexos (PDF ou foto) ficam em `dados/comprovativos/<imóvel>/AAAA-MM-DD_<id>_<nome>`, fora da pasta pública;
  - no Painel e no imóvel aparece a resposta (sem o texto citado), com o que parece dizer;
  - «Pagou» regista as despesas em dívida como pagas («o inquilino confirmou», com o comprovativo); há também
    «Ainda não pagou» e «Não é sobre o pagamento». Confirmar se o dinheiro entrou fica para o proprietário
    («Recebi»).
- **Respostas por WhatsApp ou telefone:** registam-se com os mesmos botões, e o comprovativo carrega-se na página.
- **Lembretes:**
  - sem resposta há 5 dias (`lembrete_dias` na configuração), o imóvel mostra o lembrete pronto («Já fez o
    pagamento? Basta responder sim ou não») para email ou WhatsApp, e o botão «Marcar lembrete como enviado»;
  - um lembrete ou um «ainda não» recomeçam a contagem.
- **Comprovativo que chegou como fatura:** um PDF que entrou como fatura mas é um comprovativo passa para a pasta do
  imóvel com «É um comprovativo de pagamento».
- **Faturas reais** (luz da SU Eletricidade, aquecimento da VERDAI, gás da Lisboagás) lidas sem avisos, com estas
  alterações:
  - fontes com codificação MacRoman;
  - texto rodado da margem juntado em linhas;
  - bloco Multibanco lido em qualquer arrumação, e o MONTANTE passa a ser o total (o «total a pagar» confirma-o);
  - «Adira ao débito direto» deixa de contar como débito ativo;
  - rótulo «pague até».
- **Gás** passa a ser um tipo de despesa. Fornecedores novos: VERDAI (aquecimento) e Lisboagás Comercialização
  (gás). SU Eletricidade, VERDAI e Lisboagás ficam «verificados» (com NIF).
- **Identificadores do imóvel:** comparam-se sem acentos nem pontuação (NIF e nome do titular do contrato, código
  postal, CPE…). Campo novo `morada` na pasta do imóvel.

## 0.2.0 — 06/10/2026

- **MB WAY:** o inquilino pode pagar ao senhorio por MB WAY, além de por transferência para o IBAN do contrato de
  arrendamento. Fica no campo novo `proprietario.mbway` da pasta do imóvel e a mensagem mostra as formas que
  estiverem preenchidas, por exemplo «… para o IBAN … ou por MB WAY para o 912 345 678».
- A Verificação e o aviso da mensagem passam a pedir «IBAN ou MB WAY» (antes só o IBAN).

## 0.1.0 — 06/10/2026

Primeira versão.

- **Caixa das faturas:**
  - cliente IMAP próprio, só de leitura (EXAMINE e BODY.PEEK, sem comandos que mudem a caixa);
  - lê só os remetentes da lista: os proprietários, os remetentes extra de cada imóvel e os endereços do
    administrador;
  - grava os anexos PDF em `dados/faturas/` (fora da pasta pública, permissões 600) e não repete o mesmo PDF;
  - separa o MIME com reencaminhamentos «como anexo» e nomes de ficheiro com acentos.
- **Leitura das faturas sem IA:**
  - leitor de PDF em JavaScript, sem bibliotecas: Flate, ASCII85, «object streams», fontes simples, compostas
    com ToUnicode e /Differences, TJ, XObjects;
  - regras para cerca de 30 fornecedores da zona de Lisboa (água, eletricidade, internet e aquecimento), todas
    ainda «por verificar»;
  - tira o total, o período, a data-limite, o pagamento (débito direto, Multibanco ou IBAN) e o imóvel (pelo CPE
    ou n.º de cliente, pelo assunto do email ou pelo remetente);
  - o que falta ou não bate certo fica com aviso e «por identificar» ou «por confirmar»: nunca se adivinha;
  - para identificar à mão, clica-se no valor certo entre os do PDF.
- **Despesas:**
  - a parte do inquilino de cada fatura, com uma percentagem por tipo e por imóvel;
  - os estados são nova → enviada (em dívida) → paga, com desfazer e anular.
- **Mensagem para o inquilino:**
  - a tabela das despesas novas e das em dívida, com o total, o IBAN do senhorio e a nota de cortesia nas que
    estão em dívida;
  - sai em HTML para o Gmail, em texto e em WhatsApp, com botões que abrem o email e o WhatsApp preenchidos (quem
    envia é a pessoa).
- **Acessos:**
  - o administrador e os proprietários, com password fixa dada pelo administrador (hash Argon2id ou bcrypt);
  - sessões só por HTTPS, CSRF e limite de tentativas;
  - cada proprietário só vê os seus imóveis e marca «Recebi».
- **Verificação:** alojamento, dados fora da pasta pública, imóveis completos, teste do Gmail e testes do PHP no
  próprio servidor.
- **Aspeto:** a partir do tema «00's UK Cabrio» da ARIA. Capota de lona com costura creme, faixas-título em verde
  lacado, frisos cromados, mostradores, a bandeira e o carro a passar na estrada.
- **Testes e ferramentas:**
  - 49 testes do motor e da página no jsc do macOS;
  - testes do PHP para correr no servidor;
  - PDFs e emails fictícios gerados por `testes/gerar_amostras.py`;
  - `ferramentas/ler_pdf.sh` para afinar regras com faturas reais.
