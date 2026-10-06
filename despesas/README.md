# Despesas

Uma pequena aplicação web (HTTPS) que lê as faturas dos serviços dos apartamentos arrendados: Internet, Água,
Eletricidade, Gás e Aquecimento. Com elas faz, para cada inquilino, a tabela do que tem a pagar ao senhorio.
**Nunca envia emails.** É independente da ARIA, embora viva no mesmo repositório.

## Como funciona

1. **A caixa das faturas.** Os proprietários (ou o administrador, a partir dos seus endereços) reencaminham as
   faturas para uma conta Gmail própria. A aplicação lê essa caixa **só para leitura**: usa EXAMINE e BODY.PEEK,
   não marca nada como lido e não mexe em pastas.
   - Só conta o que vem de remetentes da lista: os emails dos proprietários, os remetentes extra de cada imóvel e
     os endereços do administrador.
   - Os anexos PDF ficam guardados no servidor, em `dados/faturas/`, fora da pasta pública.
2. **Ler cada fatura, sem IA.** A página tira o texto do PDF com um leitor próprio em JavaScript (sem serviços
   externos) e aplica as regras de cada fornecedor (`publico/motor/fornecedores.json`). Daí saem:
   - o tipo, o fornecedor e o total;
   - o período e a data-limite;
   - como se paga (débito direto, Multibanco com entidade e referência, ou IBAN);
   - o imóvel. Vem do CPE ou do n.º de cliente da fatura, do assunto do email (o nome do imóvel, do proprietário
     ou uma alcunha) ou do remetente.
3. **Nada se adivinha.** Se o fornecedor for desconhecido, o tipo não for um dos cinco, o total não aparecer ou
   o PDF for digitalizado ou protegido, a fatura fica **por identificar** e mostra o aviso. O administrador clica no
   valor certo entre os que o PDF tem, escolhe o tipo e guarda. Se a regra do fornecedor ainda não foi verificada
   com uma fatura real, a fatura fica **por confirmar**.
4. **As despesas.** Cada fatura lida vira uma despesa do imóvel, com a parte do inquilino (100 %, ou a percentagem
   desse tipo na pasta do imóvel). Os estados são nova → enviada (em dívida) → paga.
5. **A confirmação do pagamento.** A mensagem pede ao inquilino que confirme depois de pagar, de preferência com
   o comprovativo.
   - Se responder por email para a caixa das faturas (vai em CC), a resposta aparece no Painel. Os anexos ficam em
     `dados/comprovativos/<imóvel>/`. Um clique em «Pagou» regista as despesas em dívida como pagas («o inquilino
     confirmou»).
   - Por WhatsApp ou telefone, regista-se com os mesmos botões e carrega-se o comprovativo na página.
   - Sem resposta há 5 dias, a página prepara um lembrete («Já fez o pagamento? Sim ou não»).
   - Confirmar se o dinheiro entrou mesmo fica para o proprietário.
6. **A mensagem para o inquilino.** Para cada imóvel há uma tabela das despesas novas e das em dívida, com o total,
   como pagar ao senhorio (transferência para o IBAN do contrato e/ou MB WAY) e a nota «caso já tenha pago, ignore esta linha» nas que
   estão em dívida.
   - Sai em HTML para colar no Gmail, em texto simples e em versão WhatsApp.
   - Os botões abrem o email ou o WhatsApp já preenchidos. **Quem envia é a pessoa**; depois marca «enviadas».
7. **Os proprietários** entram com o email e a password que o administrador lhes dá. Cada um vê só os seus
   imóveis: as despesas, o pagamento ao fornecedor (referência Multibanco) e o PDF. Marca «Recebi» quando o
   inquilino lhe paga, e a despesa passa a paga e sai da próxima mensagem.

## As pastas

| Pasta | O que tem | Vai para o servidor? | Vai para o Git? |
|---|---|---|---|
| `publico/` | `index.php` (a única porta PHP), `app.js`, `estilo.css`, o motor (`motor/*.js`, `fornecedores.json`) | sim: é a **raiz do subdomínio** | sim |
| `app/` | o PHP: login, estado, IMAP, MIME, API, verificação, testes do PHP, `ler.php` para o Cron | sim, **fora** da pasta pública | sim |
| `dados/` | `config.php` (App Password), `imoveis/<REF>/imovel.json`, `estado.json`, `faturas/`, `comprovativos/<REF>/`, `sessoes/` | sim, **fora** da pasta pública | **nunca** |
| `exemplos/` | `config.example.php` e um imóvel fictício | indiferente | sim |
| `testes/` | testes do motor (jsc), PDFs e emails **fictícios**, o gerador | sim (os testes do PHP usam-nos) | sim |
| `ferramentas/` | `ler_pdf.sh`: ler uma fatura real aqui no Mac, com o mesmo motor | não é preciso | sim |
| `amostras/` | PDFs reais trazidos para afinar regras | **não** | **nunca** |

Se a pasta `dados/` estiver dentro da pasta pública, a aplicação recusa-se a trabalhar.

## Instalar no alojamento (cPanel, o servidor dos POCs)

1. Copiar a pasta `despesas/` inteira (com a `dados/` deste Mac) para **fora** do `public_html`, por exemplo
   `/home/<conta>/despesas/`.
2. No cPanel → Domínios: criar o subdomínio (por exemplo `despesas.biglearn.pt`) com a **raiz do documento** em
   `/home/<conta>/despesas/publico`.
   - A raiz não pode ficar dentro da pasta do biglearn.pt: o `.htaccess` desse site redireciona todos os outros
     nomes para biglearn.pt.
   - Ligar o certificado (SSL/TLS Status → AutoSSL).
3. Permissões:
   - `publico/`, `app/`, `testes/` e `exemplos/`: ficheiros a 644 e pastas a 755. Os do site deram 403 por estarem
     a 600; ver o DEPLOY.md do biglearn.pt.
   - `dados/`: a pasta a 700 e o `config.php` a 600. O que a aplicação cria depois já sai assim.
4. No Gmail das faturas:
   1. Ligar a Verificação em 2 passos.
   2. Criar uma Palavra-passe de app («Despesas»).
   3. Colar as 16 letras em `dados/config.php` → `imap` → `app_password`. Nunca usar a password da conta.
5. Abrir o endereço. Na **primeira entrada**, escrever o código de instalação de `dados/config.php` e escolher a
   password do administrador.
6. Em **Acessos**, definir a password de cada proprietário e dar-lha por um canal seguro.
7. Em **Verificação**, carregar em «Verificar e testar o Gmail». Isto mostra:
   - a versão do PHP e as extensões;
   - se os dados estão fora da pasta pública;
   - se os imóveis estão completos;
   - o login no Gmail;
   - os **testes do PHP**.
8. Opcional: no cPanel → Cron Jobs, ler a caixa de 6 em 6 horas com `php /home/<conta>/despesas/app/ler.php`.
   As faturas que chegam assim ficam «por ler» até o administrador abrir a página, porque é a página que as lê.

## Quando entra um imóvel novo (IA pré-feita)

O trabalho faz-se aqui, com o Claude:

1. Criar `dados/imoveis/<REF>/imovel.json` a partir de `exemplos/imoveis/EXEMPLO-1/imovel.json`, com:
   - o proprietário (nome, email; o IBAN do contrato de arrendamento e/ou o telemóvel para MB WAY);
   - o inquilino (nome, email, WhatsApp);
   - alcunhas para o assunto dos emails;
   - os identificadores das faturas (CPE, n.º de cliente);
   - a partilha.
2. Copiar essa pasta para `dados/imoveis/` no servidor.

## Quando uma fatura não é lida

1. Na página: «Descarregar (para trazer ao Claude)» e guardar o PDF em `despesas/amostras/`.
2. Aqui, com o Claude: `sh despesas/ferramentas/ler_pdf.sh despesas/amostras/<ficheiro>.pdf` mostra o texto e o
   que as regras tiram dele. O Claude afina a regra em `publico/motor/fornecedores.json`, junta um teste com uma
   cópia fictícia e marca o fornecedor como `"verificado": true`.
3. Copiar o `fornecedores.json` novo para o servidor e, na página, «Voltar a ler».

## Testes

- **Motor e página:** `sh despesas/testes/correr.sh`. São 60 testes no jsc, o JavaScriptCore que já vem no macOS,
  sem instalar nada. Cobrem:
  - a leitura dos PDFs fictícios: fontes simples e compostas, «object streams», kerning, XObjects, /Differences,
    ASCII85, digitalizado e cifrado;
  - as regras dos fornecedores;
  - a tabela para o inquilino;
  - o HTML de cada vista.
- **PHP:** não há PHP neste Mac, por isso estes correm no servidor: `php app/testes.php` (Terminal do cPanel) ou a
  página Verificação. Cobrem:
  - o MIME dos emails fictícios;
  - o IMAP só de leitura, com respostas simuladas;
  - os estados das despesas;
  - a validação, o login e o limite de tentativas;
  - o estado em JSON;
  - a gravação dos PDFs.
- **Amostras:** `python3 despesas/testes/gerar_amostras.py` gera de novo os PDFs e os emails fictícios.

## RGPD

- **Nada sai para terceiros:** não há IA nem serviços externos. O PDF é lido no browser do administrador.
- **Faturas:** os PDFs lidos ficam em `dados/faturas/`, fora da pasta pública, e só se abrem com login (cada
  proprietário só abre os dos seus imóveis). Os ignorados são apagados.
- **Texto das faturas:** o texto completo nunca é guardado no servidor. Enquanto uma fatura está por identificar
  ficam os valores e as datas encontrados, com algumas palavras de contexto. Saem quando é guardada.
- **Passwords:** só o hash (Argon2id ou bcrypt). Sessões só por HTTPS, com cookie HttpOnly e SameSite=Strict,
  CSRF e um limite de tentativas.
- **App Password:** só em `dados/config.php` (600).
- **Repositório:** o repositório é público. Só tem exemplos fictícios; a pasta `dados/` e as `amostras/` nunca
  entram.

## Limites desta versão

- O PHP foi escrito e revisto, mas **ainda não correu**: a primeira instalação é o primeiro teste. Os erros ficam
  em `dados/erros.log` e na página Verificação.
- As regras dos fornecedores ainda **não foram verificadas com faturas reais**: as primeiras de cada um ficam
  «por confirmar».
- Os PDFs cifrados (mesmo sem password) e os digitalizados identificam-se à mão.
