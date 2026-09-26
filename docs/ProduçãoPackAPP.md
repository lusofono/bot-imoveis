# Produção e empacotamento da app: Mac e Windows, vendida em pen USB

> **Estado a 26/09/2026 (α.41.0).** O caminho está decidido; ainda não há nada implementado. O que está marcado
> como **proposta** espera pela confirmação do utilizador. A decisão está resumida em [DECISOES.md](DECISOES.md).

## Decisão

- **A ferramenta passa a ser um produto vendido:** uma app de secretária para **Mac e Windows**, entregue numa
  **pen USB**, **sem lojas** (nem a App Store nem a Microsoft Store). Pedido do utilizador, 26/09/2026.
- **Cada cliente instala a app no seu computador** e usa o seu Gmail. Mantém-se a regra de sempre: uma pasta de
  dados = uma conta Gmail.
- **O servidor alojado continua em pausa** (cPanel e AWS). A app vem primeiro, como o
  [PLANO-VERSAO-LOCAL.md](PLANO-VERSAO-LOCAL.md) já dizia («uma .app para distribuir. Depois, a AWS»).

## Porquê uma app e não o cPanel

Antes desta decisão, foi estudado pôr a página num alojamento cPanel (o guia antigo está na tag
`referencia-python`, em `docs/CPANEL.md`). Com uma app, os problemas do servidor desaparecem, porque a página
continua em `127.0.0.1`, num só computador e num só processo.

| | cPanel | App Mac | App Windows |
|---|---|---|---|
| Login | novo, obrigatório | não é preciso | não é preciso |
| Portas do Gmail (993, 465) | muitas vezes fechadas no alojamento partilhado | abertas | abertas |
| Vários processos | o `threading.Lock` da página não chega; o segundo clique falha no bloqueio | um processo | um processo |
| Pedidos longos (API OpenAI até 90 s) | o alojamento costuma cortar aos 60–120 s | sem limite | sem limite |
| Código a mudar | login, bloqueios, tempos, dependências | configuração na página | o mesmo, mais as falhas do Windows |
| Distribuir a outros | um endereço | conta Apple | certificado de assinatura |
| Abrir no telemóvel | sim | não | não |

**O que a app não resolve:** não abre no telemóvel nem noutro computador, e duas pessoas não trabalham na mesma
fila. Para isso é preciso um servidor, que fica para depois.

## Por decidir antes do código

1. **O repositório é público e não tem licença.** Como está, qualquer pessoa descarrega do GitHub o que se vende
   na pen. **Proposta:** o repositório passa a privado antes da primeira venda, com um contrato de licença de
   utilizador (EULA) na app. O que já foi clonado não se recupera; as versões novas deixam de estar à vista.
2. **O produto depende das App Passwords do Gmail.** O cliente tem de ativar a verificação em dois passos e
   gerar uma App Password: é o passo mais difícil para um agente imobiliário.
   - Se a Google fechar as App Passwords, a app deixa de ler e enviar.
   - A alternativa é o login da Google (OAuth). Numa app vendida a muitos clientes, exige a verificação da Google
     aos acessos ao Gmail e, em alguns casos, uma auditoria de segurança paga.
   - **Proposta:** começar com App Passwords, com um guia passo a passo dentro da app e no guia da pen.
3. **Atualizações.** A pen é uma fotografia de uma versão, e o projeto muda várias vezes por semana. Quando o
   Idealista mudar o formato dos avisos, os clientes precisam de uma versão nova.
   - **Proposta:** uma página de downloads no biglearn.pt, com as versões assinadas.
   - A app mostra «há uma versão nova». Só consulta o número da versão e não envia dados.
4. **O nome da app.** O [DECISOES.md](DECISOES.md) deixou-o para este momento. Hoje há três nomes: a pasta
   `Lead_Imoveis`, o repositório `bot-imoveis` e o pacote `bot_mail`. Resolvem-se de uma vez com o nome da app.

## Assinaturas: continuam a fazer falta

- **Uma app copiada de uma pen, em princípio, não leva a marca de «veio da internet»** (a quarentena no Mac, a
  Mark of the Web no Windows). Por isso o macOS e o SmartScreen não a travam como travariam um download.
- **Mas as atualizações chegam por download**, e aí o bloqueio volta:
  - no Mac: «não é possível verificar o programador»;
  - no Windows: «O Windows protegeu o PC». Sem assinatura, o antivírus também desconfia muitas vezes dos
    executáveis feitos com o PyInstaller.
- **Mac:** conta de programador da Apple (99 USD por ano), com assinatura Developer ID e notarização.
- **Windows:** certificado de assinatura de código, pago todos os anos (algumas centenas de euros), hoje sempre
  num token físico ou na nuvem. O serviço de assinatura da Microsoft na Azure pode sair mais barato, se a BigLearn
  cumprir os requisitos de empresa. **A confirmar** antes de comprar.

## O que vai na pen

```
Mac/      <Nome>.dmg            arrastar para Aplicações (Apple Silicon e Intel)
Windows/  <Nome>-Instalar.exe   instala em Programas; dados em %APPDATA%
Guia.pdf                        instalar, criar a App Password, primeira leitura
```

- A app **instala-se no computador**; nunca corre a partir da pen.
- Os dados ficam na pasta do utilizador: `~/Library/Application Support/<Nome>/` no Mac, `%APPDATA%\<Nome>\` no
  Windows. O caminho já é configurável (`--instance` ou `BOT_MAIL_INSTANCE`).

## Trabalho no código, por etapas

### Etapa 1: o código a correr no Windows

Hoje a app nem arranca no Windows. As falhas encontradas a 26/09/2026:

| Onde | O que falha | Correção |
|---|---|---|
| `backend/store.py`, `import fcntl` (em `locked`) | o módulo não existe no Windows: nada arranca | um bloqueio que funcione nos dois sistemas (`msvcrt.locking` no Windows) |
| `backend/store.py`, `save_json` | abre a pasta para fazer `fsync`; o Windows recusa, por isso nenhuma gravação funciona | saltar esse passo no Windows |
| `backend/secrets.py`, `app_password` e `openai_api_key` | não há Keychain; os ficheiros são sempre recusados porque o Windows não tem permissões 600 | a biblioteca `keyring`: Keychain no Mac, Gestor de Credenciais no Windows, com o mesmo código |
| `backend/secrets.py`, `save_password` e `save_openai_key` | `os.fchmod` só existe no Windows a partir do Python 3.13 | desaparece com o `keyring` |
| `backend/api.py`, `ours` | usa o comando `ps` para fechar a página anterior | numa app, uma só instância garante-se de outra forma |
| `mac/*.command` e o agendamento (launchd) | só existem no Mac | a própria app e, no Windows, o Agendador de Tarefas |

- **Os acentos já estão seguros:** os ficheiros de dados leem-se e gravam-se com UTF-8 explícito.
- **Os testes passam a correr em Mac e Windows** no GitHub Actions, para apanharem estas falhas automaticamente.
- A verificar nos testes em Windows: o `os.replace` pode falhar se outro programa (por exemplo o antivírus)
  tiver o ficheiro aberto nesse instante.

Esta etapa não muda nada no Mac e serve qualquer caminho futuro.

### Etapa 2: a app

- **Uma janela própria (pywebview)**, com a página lá dentro. No Mac usa o WebKit; no Windows usa o Edge
  WebView2, que já vem com o Windows 10 e 11. O servidor corre por dentro, em `127.0.0.1`, e a app entrega o
  token diretamente à janela, sem link.
- **A configuração passa para a página**, a substituir os `.command`: a App Password (com o guia), a chave OpenAI
  (opcional) e o primeiro imóvel. As chaves gravam-se no Keychain ou no Gestor de Credenciais e nunca passam por
  ficheiros do projeto nem pelos registos.
- **Uma só instância aberta de cada vez.**
- **Cópia de segurança:** um botão para exportar e importar a pasta de dados, porque os dados só existem naquele
  computador.
- **Leitura automática:** enquanto a app estiver aberta, ou agendada (launchd no Mac, Agendador de Tarefas no
  Windows). O envio continua sem agendamento: precisa sempre de aprovação.
- **Opcional:** o MCP para o Claude Desktop, apontado para o executável dentro da app com `stdio`.

### Etapa 3: licença

- **Proposta:** um ficheiro de licença assinado digitalmente (Ed25519, com a biblioteca `cryptography`), com o
  nome do cliente e o endereço Gmail autorizado. A app verifica-o sem internet e guarda só a chave pública.
- Não trava quem sabe mexer em Python (o código vai legível dentro da app), mas trava quem simplesmente copia a pen.
- Encaixa na regra «uma pasta = uma conta Gmail»: uma licença por conta.
- Falta decidir como o cliente recebe a licença: pelo email, depois da compra, ou já na pen, se o endereço Gmail
  for conhecido no momento da venda.

### Etapa 4: generalizar para outros clientes

- **Hoje só entende avisos do Idealista:** `CONTACT_SOURCE = "Idealista"` em `backend/service.py` e
  `IDEALISTA_LINK` em `backend/rules.py`. Outros clientes vão pedir o Imovirtual, o SUPERCASA e o Casa Sapo.
- **O exemplo de voz traz a assinatura da APalace** (`backend/templates/voice.example.json`): passa a um texto
  neutro.
- A página está só em português de Portugal; chega para o mercado português.

### Etapa 5: compilar e gravar a pen

- **Mac:** compila-se no Mac do utilizador, com o PyInstaller (ou o Briefcase), assinado com o Developer ID e
  notarizado. Uma versão universal2 (Apple Silicon e Intel) ou duas versões separadas.
- **Windows:** o PyInstaller não gera um `.exe` a partir do Mac. Compila-se no GitHub Actions, numa máquina
  Windows, assinado, com um instalador (por exemplo o Inno Setup). Num repositório privado os minutos gratuitos
  são limitados, mas chegam para compilações de vez em quando.
- **Antes de gravar a primeira pen:** testar num PC Windows limpo e num Mac sem Python instalado.

## Argumento de venda: RGPD

- Os dados dos clientes **nunca passam pela BigLearn**: ficam no computador do agente. Pelo RGPD, o responsável
  pelos dados é o próprio agente, e a BigLearn não é subcontratante.
- A única saída é a IA pela API da OpenAI, que é opcional. Mesmo aí, o prompt vai sem emails nem telefones.
  Isto tem de constar do contrato de licença e do guia.

## Custos conhecidos

| O quê | Quanto | Quando |
|---|---|---|
| Conta de programador da Apple | 99 USD por ano | antes da primeira venda |
| Certificado de assinatura para o Windows | algumas centenas de euros por ano (a confirmar) | antes da primeira venda |
| Pens USB e impressão do guia | por unidade | em cada venda |
| Página de downloads | já existe o biglearn.pt | com a primeira atualização |

## Riscos

- **As App Passwords do Gmail** (ver acima): é o maior risco do produto.
- **Os portais mudam o formato dos avisos** sem aviso prévio: cada mudança obriga a uma atualização para todos
  os clientes.
- **O apoio:** a configuração do Gmail e da chave OpenAI vai gerar pedidos de ajuda. O guia e a configuração na
  página têm de os reduzir ao mínimo.
- **Os dados só existem num computador:** sem cópia de segurança, perder o portátil é perder a fila e os
  contactos.
