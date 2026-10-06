/* Testes da página (publico/app.js) sem browser: um «document» de faz-de-conta chega para carregar o ficheiro;
   depois desenham-se as vistas com dados fictícios e confere-se o HTML (conteúdo, etiquetas equilibradas, escapes).
   Carregado por testes/js/correr.js. */
var document = { addEventListener: function () {} };
var window = this;
load(BASE + '/publico/app.js');
var P = Despesas._pagina;

function equilibrado(html, nome) {
  ['div', 'section', 'article', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'form', 'ul', 'li', 'span', 'button', 'a', 'label', 'select', 'dl', 'dt', 'dd', 'p', 'h1', 'h3', 'datalist']
    .forEach(function (tag) {
      var abre = (html.match(new RegExp('<' + tag + '[ >]', 'g')) || []).length, fecha = (html.match(new RegExp('</' + tag + '>', 'g')) || []).length;
      if (abre !== fecha) throw new Error(nome + ': <' + tag + '> abre ' + abre + ' e fecha ' + fecha);
    });
}

IMOVEL.partilha = { agua: 100, eletricidade: 100, internet: 100, aquecimento: 50 };
var MAU = '<img src=x onerror=alert(1)>';
var DADOS_ADMIN = {
  utilizador: { email: 'admin@example.com', nome: 'Admin', papel: 'admin' },
  imoveis: [IMOVEL],
  faturas: [
    { id: 'f00000000001', estado: 'por_identificar', ficheiro: MAU, remetente: 'proprietario1@example.com', assunto: 'Fwd: fatura', recebido_em: '2026-10-01T09:00:00+01:00',
      fornecedor: '', tipo: null, total: null, imovel: 'EX-1', periodo: { mes: '2026-09' }, pagamento: { metodo: null },
      avisos: ['Não encontrei o total a pagar: escolher o valor certo entre os do PDF.'], valores: [{ cent: 3847, contexto: 'Total a pagar' }, { cent: 2130, contexto: 'Água' }],
      datas: ['2026-09-25'], sem_texto: false },
    { id: 'f00000000002', estado: 'por_confirmar', ficheiro: 'edp.pdf', remetente: 'admin@example.com', assunto: 'T2 Exemplo luz', recebido_em: '2026-10-02T09:00:00+01:00',
      fornecedor: 'EDP Comercial', fornecedor_id: 'edp-comercial', tipo: 'eletricidade', total: 6412, imovel: 'EX-1', periodo: { de: '2026-08-05', ate: '2026-09-04' },
      data_limite: '2026-09-28', pagamento: { metodo: 'multibanco', entidade: '54321', referencia: '987 654 321' }, avisos: ['A regra de EDP Comercial ainda não foi verificada'], valores: [], datas: [] },
    { id: 'a', estado: 'lida', ficheiro: 'epal.pdf', fornecedor: 'EPAL', tipo: 'agua', total: 3847, imovel: 'EX-1', periodo: { de: '2026-08-01', ate: '2026-08-31' }, recebido_em: '2026-09-10T10:00:00+01:00', pagamento: { metodo: 'multibanco', entidade: '12345', referencia: '123 456 789' } },
    { id: 'z', estado: 'ignorada', ficheiro: 'ginasio.pdf', remetente: 'x@example.com', recebido_em: '2026-09-01T10:00:00+01:00' }
  ],
  despesas: DESPESAS.map(function (d) { var c = clonar(d); c.imovel = 'EX-1'; c.fatura = d.id; c.criada = '2026-10-0' + (1 + DESPESAS.indexOf(d)); return c; }),
  caixa: { conta: 'contas@example.com', ultima_leitura: '2026-10-06T10:00:00+01:00', ultimo_erro: null, sem_pdf: [{ quando: '2026-10-06T10:00:00+01:00', nota: 'Email de x sem PDF anexado.' }] },
  remetentes_administrador: ['admin@example.com'], assinatura: 'Gestão Exemplo',
  utilizadores: [{ email: 'admin@example.com', nome: 'Admin', papel: 'admin', tem_senha: true }, { email: 'proprietario1@example.com', nome: 'Senhorio Exemplo', papel: 'proprietario', tem_senha: false }],
  registo: [{ quando: '2026-10-06T10:00:00+01:00', quem: 'admin@example.com', oque: 'entrou' }]
};

print('página');
P.S.regras = REGRAS;
P.S.dados = DADOS_ADMIN;
teste('painel do administrador', function () {
  var h = P.vistaPainelAdmin();
  equilibrado(h, 'painel');
  contem(h, 'Faturas por identificar');
  contem(h, 'contas@example.com');
  contem(h, 'T2 Exemplo');
  contem(h, 'Email de x sem PDF anexado.');
  contem(h, 'data-acao="ler-caixa"');
});
teste('faturas: formulário, valores para escolher e nomes escapados', function () {
  var h = P.vistaFaturas();
  equilibrado(h, 'faturas');
  contem(h, 'data-form="fatura" data-id="f00000000001"');
  contem(h, 'data-acao="escolher-total" data-cent="3847">38,47 €<small>Total a pagar</small>');
  contem(h, 'data-acao="escolher-data" data-iso="2026-09-25"');
  contem(h, 'Período na fatura: setembro 2026');
  contem(h, '<option value="EPAL">');
  contem(h, 'value="64,12"');
  contem(h, 'Pagamento ao fornecedor: Multibanco: entidade 54321, referência 987 654 321');
  contem(h, 'index.php?a=pdf&id=f00000000001&descarregar=1');
  naoContem(h, '<img', 'o nome do ficheiro tem de sair escapado');
  contem(h, '&lt;img src=x');
});
teste('imóvel: a mensagem para o inquilino e as ligações', function () {
  P.S.modo = {};
  var h = P.vistaImovelAdmin(IMOVEL);
  equilibrado(h, 'imóvel');
  contem(h, 'Mensagem para Inquilina');
  contem(h, '<div class="previa"><div style="font-family:Arial');
  contem(h, 'Marcar 3 como enviada(s)');
  contem(h, 'href="https://wa.me/351912345678?text=Ol%C3%A1%20Inquilina');
  contem(h, 'href="mailto:inquilina@example.com?subject=Despesas');
  igual(P.S.mensagens['EX-1'].ids, ['b', 'a', 'd']);
  contem(h, 'Aquecimento 50%');
  P.S.modo['EX-1'] = 'whatsapp';
  var w = P.vistaImovelAdmin(IMOVEL);
  equilibrado(w, 'imóvel (WhatsApp)');
  contem(w, '<div class="previa-texto">Olá Inquilina,');
  contem(w, '*Total: 116,26 €*');
  P.S.modo = {};
});
teste('confirmação do pagamento: resposta por ver, registo à mão e lembrete', function () {
  var D = clonar(DADOS_ADMIN);
  D.lembrete_dias = 5;
  D.email_respostas = 'contas@example.com';
  D.despesas.forEach(function (d) { if (d.estado === 'enviada') d.enviada_em = '2026-01-01T10:00:00+01:00'; });
  D.respostas = [{ id: 'r1', imovel: 'EX-1', de: 'inquilina@example.com', assunto: 'Re: Despesas', recebido_em: '2026-01-07T10:00:00+01:00',
    texto: 'Sim, já paguei.', comprovativos: ['c1'], sugestao: 'sim', estado: 'por_ver', origem: 'email' }];
  D.comprovativos = [{ id: 'c1', imovel: 'EX-1', nome: 'comprovativo.jpg', ficheiro: '2026-01-07_c1_comprovativo.jpg', tipo: 'image/jpeg', recebido_em: '2026-01-07T10:00:00+01:00', origem: 'email' }];
  P.S.dados = D;
  var h = P.vistaImovelAdmin(IMOVEL);
  equilibrado(h, 'imóvel com confirmação');
  contem(h, 'Confirmação do pagamento');
  contem(h, '<blockquote>Sim, já paguei.</blockquote>');
  contem(h, 'parece dizer que pagou');
  contem(h, 'data-acao="responder" data-valor="sim" data-ref="EX-1" data-resposta="r1">Pagou (1, 64,12 €)');
  contem(h, 'index.php?a=comprovativo&id=c1');
  contem(h, 'data-form="comprovativo" data-ref="EX-1"');
  contem(h, 'Sem resposta há');
  contem(h, 'Marcar lembrete como enviado');
  contem(h, 'mailto:inquilina@example.com?cc=contas@example.com&amp;subject=');
  contem(h, 'Comprovativos de pagamento');
  var p = P.vistaPainelAdmin();
  equilibrado(p, 'painel com pagamentos a confirmar');
  contem(p, 'Pagamentos a confirmar');
  contem(p, 'respondeu com comprovativo');
  contem(p, 'não responde há');
  contem(P.vistaFaturas(), 'É um comprovativo de pagamento');
  P.S.dados = DADOS_ADMIN;
});
teste('acessos e verificação', function () {
  var h = P.vistaAcessos();
  equilibrado(h, 'acessos');
  contem(h, '<span class="etiqueta e-paga">definida</span>');
  contem(h, 'por definir');
  P.S.verificacao = { itens: [{ nome: 'PHP 7.4', ok: true, detalhe: '8.2', grave: true }, { nome: 'Argon2id', ok: false, detalhe: 'bcrypt', grave: false }],
    testes: { passaram: 1, total: 2, resultados: [{ nome: 'a', ok: true }, { nome: 'b', ok: false, erro: 'x' }] } };
  var v = P.vistaVerificacao();
  equilibrado(v, 'verificação');
  contem(v, 'Testes do PHP: 1/2');
  contem(v, 'e-enviada">atenção');
});
teste('proprietário: só «Recebi» e o pagamento ao fornecedor', function () {
  P.S.dados = clonar(DADOS_ADMIN);
  P.S.dados.utilizador = { email: 'proprietario1@example.com', nome: 'Senhorio', papel: 'proprietario' };
  P.S.dados.faturas = P.S.dados.faturas.filter(function (f) { return f.estado === 'lida'; });
  var h = P.vistaPainelDono();
  equilibrado(h, 'proprietário');
  contem(h, 'Recebi');
  contem(h, 'A aguardar pagamento de Inquilina: <b>64,12 €</b>');
  contem(h, 'Multibanco: entidade 12345, referência 123 456 789');
  naoContem(h, 'Anular');
  naoContem(h, 'Desfazer envio');
  P.S.dados = DADOS_ADMIN;
});
teste('o que a página manda ao servidor depois de ler cada PDF', function () {
  ['epal_agua.pdf', 'edp_eletricidade.pdf', 'meo_internet.pdf', 'climaespaco_aquecimento.pdf', 'nos_internet.pdf', 'ginasio_outro.pdf', 'digitalizada.pdf'].forEach(function (nome) {
    var p = Despesas.pdf.extrair(pdf(nome));
    var a = Despesas.regras.analisar(p.texto, { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com', assunto: '' });
    var s = JSON.parse(JSON.stringify(P.paraServidor(a, p)));
    verdade(s.fornecedor_id === null || /^[a-z0-9-]{1,40}$/.test(s.fornecedor_id), nome + ' fornecedor_id');
    verdade(typeof s.fornecedor === 'string', nome + ' fornecedor');
    verdade(s.total === null || (typeof s.total === 'number' && Math.floor(s.total) === s.total), nome + ' total inteiro');
    verdade(['lida', 'por_confirmar', 'por_identificar'].indexOf(s.estado) >= 0, nome + ' estado');
    verdade(Array.isArray(s.avisos) && Array.isArray(s.valores) && Array.isArray(s.datas), nome + ' listas');
    s.valores.forEach(function (v) { verdade(typeof v.cent === 'number' && typeof v.contexto === 'string', nome + ' valores'); });
    igual(s.sem_texto, nome === 'digitalizada.pdf', nome + ' sem_texto');
  });
});
