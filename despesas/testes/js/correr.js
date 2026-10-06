/* Testes do motor (leitura de PDFs, regras dos fornecedores, tabela para o inquilino).
   Correm no jsc que vem com o macOS, sem instalar nada:  sh testes/correr.sh
   Os PDFs de testes/pdfs são fictícios e gerados por testes/gerar_amostras.py. */
var BASE = (typeof arguments !== 'undefined' && arguments[0]) ? arguments[0] : '.';
load(BASE + '/publico/motor/util.js');
load(BASE + '/publico/motor/pdf.js');
load(BASE + '/publico/motor/regras.js');
load(BASE + '/publico/motor/tabela.js');

var U = Despesas.util, falhas = 0, total = 0;
function teste(nome, fn) {
  total++;
  try { fn(); print('  ok    ' + nome); }
  catch (e) { falhas++; print('  FALHA ' + nome + '\n        ' + (e && e.message ? e.message : e)); }
}
function igual(veio, esperado, msg) {
  var a = JSON.stringify(veio), b = JSON.stringify(esperado);
  if (a !== b) throw new Error((msg ? msg + ': ' : '') + 'esperava ' + b + ', veio ' + a);
}
function verdade(c, msg) { if (!c) throw new Error(msg || 'condição falsa'); }
function contem(s, sub, msg) { if (String(s).indexOf(sub) < 0) throw new Error((msg ? msg + ': ' : '') + 'não contém «' + sub + '» em: ' + String(s).slice(0, 400)); }
function naoContem(s, sub, msg) { if (String(s).indexOf(sub) >= 0) throw new Error((msg ? msg + ': ' : '') + 'não devia conter «' + sub + '»'); }
function pdf(nome) { return readFile(BASE + '/testes/pdfs/' + nome, 'binary'); }
var REGRAS = JSON.parse(readFile(BASE + '/publico/motor/fornecedores.json'));
var IMOVEIS = [
  { ref: 'EX-1', nome: 'Exemplo 1', remetentes: ['proprietario1@example.com'], identificadores: ['9900112233', { fornecedor: 'climaespaco', valor: 'CT-000777' }] },
  { ref: 'EX-2', nome: 'Exemplo 2', remetentes: ['proprietario2@example.com'], identificadores: ['PT0002000012345678XY', '1122334455', '5566778899'] }
];
function analisar(nome, remetente, regras) {
  var p = Despesas.pdf.extrair(pdf(nome));
  return Despesas.regras.analisar(p.texto, { regras: regras || REGRAS, imoveis: IMOVEIS, remetente: remetente || 'proprietario1@example.com' });
}
function clonar(o) { return JSON.parse(JSON.stringify(o)); }

// ── util ─────────────────────────────────────────────────────────────────────────────────────
print('util');
teste('base64 nos dois sentidos', function () {
  igual(U.utf8ParaTexto(U.base64ParaBytes('SGVsbG8gw6fDo28=')), 'Hello ção');
  igual(U.bytesParaBase64(U.textoParaUtf8('Hello ção')), 'SGVsbG8gw6fDo28=');
  igual(U.bytesParaBase64(new Uint8Array([1])), 'AQ==');
});
teste('SHA-256 com os vetores conhecidos', function () {
  igual(U.sha256(new Uint8Array(0)), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  igual(U.sha256(U.textoParaUtf8('abc')), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  igual(U.sha256(U.textoParaUtf8('abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')), '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1');
});
teste('inflate: guardado, Huffman fixo e dinâmico, deflate cru', function () {
  var d = JSON.parse(readFile(BASE + '/testes/js/inflate.json'));
  var original = U.bytesParaBase64(U.base64ParaBytes(d.original));
  ['zlib0', 'zlib1', 'zlib9', 'cru'].forEach(function (k) { igual(U.bytesParaBase64(U.inflate(U.base64ParaBytes(d[k]))), original, k); });
  igual(U.bytesParaBase64(U.inflate(U.base64ParaBytes(d.curto))), d.curto_original, 'curto');
});
teste('ASCII85', function () {
  var d = JSON.parse(readFile(BASE + '/testes/js/inflate.json'));
  igual(U.bytesParaBase64(U.binarioParaBytes(Despesas.pdf._deA85(d.a85))), d.a85_original);
});
teste('dobrar tira acentos sem mudar o comprimento', function () {
  var s = 'Água — Período de Faturação: ÇÃO º';
  igual(U.dobrar(s), 'agua - periodo de faturacao: cao o');
  igual(U.dobrar(s).length, s.length);
});
teste('valores em euros', function () {
  igual(U.lerValor('1.234,56'), 123456);
  igual(U.lerValor('38,47 €'), 3847);
  igual(U.lerValor('-12,30'), -1230);
  igual(U.lerValor('abc'), null);
  igual(U.formatarValor(123456), '1 234,56 €');
  igual(U.formatarValor(5), '0,05 €');
  igual(U.formatarData('2026-09-25'), '25/09/2026');
  igual(U.formatarData('2026-08'), 'agosto 2026');
});

// ── pdf ──────────────────────────────────────────────────────────────────────────────────────
print('pdf');
teste('literais: escapes, octal e continuação de linha', function () {
  var lx = new Despesas.pdf._Lexer('(a\\(b\\)c\\101\\\n d(e)f)', 0);
  igual(lx.token().v, 'a(b)cA d(e)f');
});
teste('nomes de glifos', function () {
  var g = Despesas.pdf._glifo;
  igual([g('ccedilla'), g('Atilde'), g('uni00E7'), g('Euro'), g('a.sc'), g('u20AC'), g('naoexiste')], ['ç', 'Ã', 'ç', '€', 'a', '€', null]);
});
teste('fonte simples WinAnsi, rótulo e valor na mesma linha (água)', function () {
  var r = Despesas.pdf.extrair(pdf('epal_agua.pdf'));
  verdade(r.temTexto, 'tem texto');
  contem(r.texto, 'Empresa Portuguesa das Águas Livres');
  contem(r.texto, 'Período de faturação: 01/08/2026 a 31/08/2026');
  contem(r.texto, 'Total a pagar   38,47 €');
  contem(r.texto, 'Entidade: 12345   Referência: 123 456 789');
  igual(r.avisos, []);
});
teste('fonte composta Identity-H + ToUnicode em object stream, 2 páginas (eletricidade)', function () {
  var r = Despesas.pdf.extrair(pdf('edp_eletricidade.pdf'));
  igual(r.paginas.length, 2);
  contem(r.paginas[0], 'EDP Comercial — Comercialização de Energia');
  contem(r.paginas[0], 'Valor a pagar   64,12 €');
  contem(r.paginas[0], 'Data limite de pagamento\n28/09/2026');
  contem(r.paginas[1], 'Entidade 54321 Referência 987 654 321');
});
teste('TJ com kerning, cm com escala e XObject (internet)', function () {
  var r = Despesas.pdf.extrair(pdf('meo_internet.pdf'));
  contem(r.texto, 'MEO - Serviços de Comunicações e Multimédia');
  contem(r.texto, 'Fatura de serviços de telecomunicações');
  contem(r.texto, 'Total a pagar   41,99 €');
  contem(r.texto, 'Débito Direto');
});
teste('/Differences e ASCII85 + Flate (aquecimento)', function () {
  var r = Despesas.pdf.extrair(pdf('climaespaco_aquecimento.pdf'));
  contem(r.texto, 'Climaespaço — Sistema de distribuição de calor e frio');
  contem(r.texto, 'Energia térmica — calor   25,78 €');
  contem(r.texto, 'IBAN PT50 0000 0000 1234 5678 9013 5');
});
teste('TL, T* e apóstrofo (internet)', function () {
  var r = Despesas.pdf.extrair(pdf('nos_internet.pdf'));
  contem(r.texto, 'NOS Comunicações, S.A. (exemplo)\nFatura mensal de setembro de 2026\nCliente Exemplo Dois');
  contem(r.texto, 'Período de 15/08/2026 a 14/09/2026');
});
teste('fonte MacRoman, texto rodado letra a letra e Multibanco em colunas (luz)', function () {
  var r = Despesas.pdf.extrair(pdf('su_luz_macroman.pdf'));
  contem(r.texto, 'Página 1 de 2');
  contem(r.texto, 'Período de faturação: 13 jun 2026 até 12 jul 2026');
  contem(r.texto, 'Potência contratada');
  contem(r.texto, 'PROCESSADO POR COMPUTADOR - SU ELETRICIDADE (exemplo) - Sede: Rua Fictícia, 1');
  contem(r.texto, 'REFERÊNCIA\n222 333 444');
});
teste('digitalizada: sem texto e com aviso', function () {
  var r = Despesas.pdf.extrair(pdf('digitalizada.pdf'));
  igual(r.temTexto, false);
  contem(r.avisos.join(' '), 'digitalizada');
});
teste('cifrado: não tenta ler, avisa', function () {
  var r = Despesas.pdf.extrair(pdf('protegido.pdf'));
  igual(r.protegido, true);
  contem(r.avisos.join(' '), 'protegido');
});
teste('ficheiro que não é PDF', function () {
  var r = Despesas.pdf.extrair(U.textoParaUtf8('olá, isto não é um PDF'));
  igual(r.temTexto, false);
  contem(r.avisos.join(' '), 'não parece um PDF');
});

// ── regras ───────────────────────────────────────────────────────────────────────────────────
print('regras');
var ESPERADO = {
  'epal_agua.pdf': { f: 'epal', tipo: 'agua', total: 3847, periodo: { de: '2026-08-01', ate: '2026-08-31' }, lim: '2026-09-25',
    pag: { metodo: 'multibanco', entidade: '12345', referencia: '123 456 789', montante: 3847 }, imovel: 'EX-1' },
  'edp_eletricidade.pdf': { f: 'edp-comercial', tipo: 'eletricidade', total: 6412, periodo: { de: '2026-08-05', ate: '2026-09-04' }, lim: '2026-09-28',
    pag: { metodo: 'multibanco', entidade: '54321', referencia: '987 654 321', montante: 6412 }, imovel: 'EX-2' },
  'meo_internet.pdf': { f: 'meo', tipo: 'internet', total: 4199, periodo: { de: '2026-09-01', ate: '2026-09-30' }, lim: '2026-09-20',
    pag: { metodo: 'debito_direto' }, imovel: 'EX-2' },
  'climaespaco_aquecimento.pdf': { f: 'climaespaco', tipo: 'aquecimento', total: 2733, periodo: { de: '2026-08-01', ate: '2026-08-31' }, lim: '2026-10-15',
    pag: { metodo: 'transferencia', iban: 'PT50 0000 0000 1234 5678 9013 5' }, imovel: 'EX-1' },
  'nos_internet.pdf': { f: 'nos', tipo: 'internet', total: 3599, periodo: { de: '2026-08-15', ate: '2026-09-14' }, lim: '2026-09-30',
    pag: { metodo: 'multibanco', entidade: '11111', referencia: '222 333 444' }, imovel: 'EX-2' },
  'su_luz_macroman.pdf': { f: 'su-eletricidade', tipo: 'eletricidade', total: 2600, periodo: { de: '2026-06-13', ate: '2026-07-12' }, lim: '2026-08-01',
    pag: { metodo: 'multibanco', entidade: '11111', referencia: '222 333 444', montante: 2600 }, imovel: 'EX-1', estado: 'lida' }
};
Object.keys(ESPERADO).forEach(function (nome) {
  teste('lê ' + nome, function () {
    var e = ESPERADO[nome], r = analisar(nome);
    igual(r.fornecedor && r.fornecedor.id, e.f, 'fornecedor');
    igual(r.tipo, e.tipo, 'tipo');
    igual(r.total, e.total, 'total');
    igual(r.periodo, e.periodo, 'período');
    igual(r.data_limite, e.lim, 'data-limite');
    igual(r.pagamento, e.pag, 'pagamento');
    igual(r.imovel, e.imovel, 'imóvel');
    igual(r.estado, e.estado || 'por_confirmar', 'estado (por confirmar enquanto a regra não for verificada)');
  });
});
teste('regra verificada e tudo encontrado → lida, sem avisos', function () {
  var regras = clonar(REGRAS);
  regras.fornecedores.forEach(function (f) { if (f.id === 'epal') f.verificado = true; });
  var r = analisar('epal_agua.pdf', null, regras);
  igual(r.estado, 'lida');
  igual(r.avisos, []);
});
teste('sem «Total a pagar» mas com Multibanco → o total é o montante', function () {
  var r = analisar('epal_sem_total.pdf');
  igual(r.total, 3847);
  igual(r.estado, 'por_confirmar');
});
teste('sem total nenhum → por identificar, com os valores do PDF para escolher', function () {
  var t = 'EPAL\nÁgua — consumo 21,30 €\nSaneamento 14,99 €\nIVA 6,00 % 2,18 €\nData limite de pagamento: 25/09/2026';
  var r = Despesas.regras.analisar(t, { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com' });
  igual(r.total, null);
  igual(r.estado, 'por_identificar');
  contem(r.avisos.join(' '), 'Não encontrei o total');
  var cents = r.valores.map(function (v) { return v.cent; });
  verdade(cents.indexOf(2130) >= 0 && cents.indexOf(218) >= 0, 'valores ' + JSON.stringify(cents));
  verdade(cents.indexOf(600) < 0, 'a taxa de IVA (6,00 %) não é um valor');
});
teste('fornecedor desconhecido (ginásio) → por identificar, não adivinha o tipo', function () {
  var r = analisar('ginasio_outro.pdf');
  igual(r.fornecedor, null);
  igual(r.tipo, null);
  igual(r.estado, 'por_identificar');
  contem(r.avisos.join(' '), 'Fornecedor desconhecido');
});
teste('digitalizada → por identificar', function () {
  var r = analisar('digitalizada.pdf');
  igual(r.estado, 'por_identificar');
  contem(r.avisos.join(' '), 'Sem texto');
});
teste('MEO Energia não é a MEO das telecomunicações; NOS só em maiúsculas', function () {
  var t = 'MEO Energia\nFatura de eletricidade\nnos termos da lei\nTotal a pagar 10,00 €';
  igual(Despesas.regras.identificarFornecedor(t, REGRAS).fornecedor.id, 'meo-energia');
  igual(Despesas.regras.identificarFornecedor('Fatura\nnos termos da lei\n', REGRAS).fornecedor, null);
});
teste('dois fornecedores com os mesmos pontos → ambíguo', function () {
  var r = Despesas.regras.identificarFornecedor('EPAL e Climaespaço', REGRAS);
  igual(r.fornecedor, null);
  igual(r.ambiguo, true);
});
teste('fornecedor de luz que fala em gás natural → aviso, sem tipo', function () {
  var t = 'EDP Comercial\nFatura de eletricidade e gás natural\nkWh\nTotal a pagar 80,00 €\n';
  var r = Despesas.regras.analisar(t, { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com' });
  igual(r.tipo, null);
  igual(r.estado, 'por_identificar');
  contem(r.avisos.join(' '), 'gás natural');
});
teste('total diferente do montante Multibanco → aviso', function () {
  var t = 'EPAL\nÁgua\nTotal a pagar 40,00 €\nEntidade 12345 Referência 123 456 789 Montante 38,47 €\n';
  var r = Despesas.regras.analisar(t, { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com' });
  igual(r.total, 3847, 'o montante do Multibanco é o que se paga');
  igual(r.estado, 'por_confirmar');
  contem(r.avisos.join(' '), 'não bate');
});
teste('bloco Multibanco: na mesma linha, rótulo por cima do valor, ou rótulos seguidos e valores depois', function () {
  var B = Despesas.regras.blocoMultibanco;
  igual(B('Entidade: 12345   Referência: 123 456 789   Montante: 38,47 €'), { entidade: '12345', referencia: '123 456 789', montante: 3847 });
  igual(B('Pagar valor desta Fatura\nENTIDADE\n11111\nREFERÊNCIA\n222 333 444\nMONTANTE\n27,15 €'), { entidade: '11111', referencia: '222 333 444', montante: 2715 });
  igual(B('Pagável nas Caixas Multibanco\nENTIDADE:\nREFERÊNCIA:\nMONTANTE:\n33333\n444 555 666\n4,62 €'), { entidade: '33333', referencia: '444 555 666', montante: 462 });
  igual(B('ENTIDADE:   55555\nATENDIMENTO TELEFÓNICO\n210 000 000   REFERÊNCIA: 505 606 707\nMONTANTE:   41,23 €'), { entidade: '55555', referencia: '505 606 707', montante: 4123 });
  igual(B('Ao pagar confirme se a entidade MB é 66666 ou 77777\n(muito texto pelo meio)\n' + new Array(30).join('linha de texto qualquer\n') +
    'ENTIDADE 66666   REFERÊNCIA 808 909 101   MONTANTE 29,87 €'), { entidade: '66666', referencia: '808 909 101', montante: 2987 });
  igual(B('Telefone 213 171 170\nNIB 0000 0000 0000'), null);
});
teste('«Adira ao débito direto» é um convite, não um débito ativo', function () {
  igual(Despesas.regras.pagamento('Adira ao débito direto\nENTIDADE 11111 REFERÊNCIA 222 333 444 MONTANTE 9,99 €').metodo, 'multibanco');
  igual(Despesas.regras.pagamento('- Débito Direto: a forma mais cómoda. Se ainda não aderiu, envie um email\nENTIDADE: 11111\nREFERÊNCIA: 222 333 444').metodo, 'multibanco');
  igual(Despesas.regras.pagamento('O valor será debitado na sua conta a 20/10/2026').metodo, 'debito_direto');
  igual(Despesas.regras.pagamento('Pagamento por Débito Direto na conta indicada').metodo, 'debito_direto');
});
teste('fornecedores verificados com faturas reais: SU Eletricidade, VERDAI e Lisboagás (gás)', function () {
  var id = function (t) { var f = Despesas.regras.identificarFornecedor(t, REGRAS).fornecedor; return f && f.id; };
  igual(id('sueletricidade.pt\nPagamentos\nSU ELETRICIDADE, S.A. - NIPC 507 846 044'), 'su-eletricidade');
  igual(id('VERDAI\nA energia do seu conforto.\nNIPC PT518925498'), 'verdai');
  igual(id('Site: curgasnatural.pt\nLisboagás Comercialização, S.A., N.I.P.C.: 508156661'), 'lisboagas');
  var t = 'Lisboagás Comercialização, S.A.\nGás Natural\nPeríodo de Faturação: 18 JUN 2026 a 17 JUL 2026\nVALOR A PAGAR\n4,62€\nENTIDADE: 33333\nREFERÊNCIA: 444 555 666\nMONTANTE: 4,62 €\nData limite de pagamento: 21-08-2026';
  var r = Despesas.regras.analisar(t, { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com' });
  igual([r.tipo, r.total, r.periodo, r.data_limite, r.estado], ['gas', 462, { de: '2026-06-18', ate: '2026-07-17' }, '2026-08-21', 'lida']);
  igual(Despesas.tabela.NOME_TIPO.gas, 'Gás');
});
teste('valores: percentagens, preços unitários e datas não contam', function () {
  var v = Despesas.regras.valores('IVA 23,00 %\nPreço 0,1234 €/kWh\nData 01/08/2026\nTotal 1.234,56 €\nCrédito -5,00 €').map(function (x) { return x.cent; });
  igual(v, [123456, -500]);
});
teste('datas: números, ISO e por extenso', function () {
  var d = Despesas.regras.datas('Emitida a 5.10.2026; vence 2026-10-20; limite 15 de outubro de 2026; 31/02/2026 não existe');
  igual(d.map(function (x) { return x.iso; }), ['2026-10-05', '2026-10-20', '2026-10-15']);
});
teste('período por mês quando não há datas', function () {
  var r = Despesas.regras.analisar('EPAL\nÁgua\nPeríodo de faturação: setembro de 2026\nTotal a pagar 10,00 €', { regras: REGRAS, imoveis: IMOVEIS, remetente: 'proprietario1@example.com' });
  igual(r.periodo, { mes: '2026-09' });
});
teste('IBAN: módulo 97', function () {
  verdade(Despesas.regras.ibanValido('PT50 0000 0000 1234 5678 9013 5'));
  verdade(!Despesas.regras.ibanValido('PT50 0000 0000 1234 5678 9013 6'));
});
teste('no débito direto o IBAN (do cliente) não se guarda', function () {
  var p = Despesas.regras.pagamento('Pagamento por débito direto na conta PT50 0000 0000 1234 5678 9013 5');
  igual(p, { metodo: 'debito_direto' });
});
teste('imóvel: identificador com espaços diferentes; remetente com dois imóveis', function () {
  var im = IMOVEIS.concat([{ ref: 'EX-3', nome: 'Exemplo 3', remetentes: ['proprietario2@example.com'], identificadores: [] }]);
  igual(Despesas.regras.identificarImovel('CPE PT 0002 0000 1234 5678 XY', im, 'proprietario2@example.com').imovel, 'EX-2');
  var r = Despesas.regras.identificarImovel('sem identificadores', im, 'proprietario2@example.com');
  igual(r.imovel, null);
  contem(r.aviso, 'mais do que um imóvel');
  igual(Despesas.regras.identificarImovel('sem identificadores', im, 'Proprietario1@Example.com').imovel, 'EX-1');
});
teste('identificadores sem acentos nem pontuação: NIF, código postal, nome do titular', function () {
  var im = [{ ref: 'A', nome: 'A', remetentes: ['a@example.com'], identificadores: [{ tipo: 'titular', valor: 'Maria Simões Exemplo' }] },
            { ref: 'B', nome: 'B', remetentes: ['a@example.com'], identificadores: [{ tipo: 'nif', valor: '123 456 789' }, { tipo: 'codigo_postal', valor: '1000-001' }] }];
  igual(Despesas.regras.identificarImovel('Titular: MARIA SIMOES EXEMPLO', im, 'a@example.com').imovel, 'A');
  igual(Despesas.regras.identificarImovel('NIF: 123456789', im, 'a@example.com').imovel, 'B');
  igual(Despesas.regras.identificarImovel('Rua X, 1000 001 Lisboa', im, 'a@example.com').imovel, 'B');
});
teste('imóvel pelo assunto quando é o administrador a reencaminhar', function () {
  var im = [
    { ref: 'A', nome: 'T2 Exemplo — Edifício Azul', apelidos: ['Azul'], proprietario: { nome: 'Ana Exemplo' }, remetentes: ['ana@example.com'], identificadores: ['CPE-AAA-111'] },
    { ref: 'B', nome: 'T1 Exemplo', apelidos: ['Mouraria'], proprietario: { nome: 'Rui Exemplo' }, remetentes: ['rui@example.com'], identificadores: [] }
  ];
  var adm = 'admin@example.com';
  igual(Despesas.regras.identificarImovel('fatura sem identificadores', im, adm, 'Fwd: Rui Exemplo - água').imovel, 'B');
  igual(Despesas.regras.identificarImovel('fatura sem identificadores', im, adm, 'eletricidade do azul').imovel, 'A');
  igual(Despesas.regras.identificarImovel('fatura sem identificadores', im, adm, 'FW: Fatura').imovel, null);
  var r = Despesas.regras.identificarImovel('CPE-AAA-111', im, adm, 'Rui Exemplo');
  igual(r.imovel, null);
  contem(r.aviso, 'aponta para «T1 Exemplo» mas a fatura é de «T2 Exemplo — Edifício Azul»');
  igual(Despesas.regras.identificarImovel('CPE-AAA-111', im, adm, 'Ana Exemplo').imovel, 'A');
  var a = Despesas.regras.analisar('EPAL\nÁgua\nTotal a pagar 10,00 €', { regras: REGRAS, imoveis: im, remetente: adm, assunto: 'Mouraria agosto' });
  igual(a.imovel, 'B');
});
teste('todos os fornecedores têm id, nome, tipo válido e textos para identificar', function () {
  var ids = {};
  REGRAS.fornecedores.forEach(function (f) {
    verdade(f.id && f.nome && REGRAS.tipos[f.tipo], 'fornecedor ' + JSON.stringify(f).slice(0, 80));
    verdade(!ids[f.id], 'id repetido ' + f.id);
    ids[f.id] = 1;
    verdade((f.identificar.fortes || []).length > 0, f.id + ' sem textos fortes');
  });
  verdade(REGRAS.fornecedores.length >= 25, 'fornecedores: ' + REGRAS.fornecedores.length);
});

// ── tabela ───────────────────────────────────────────────────────────────────────────────────
print('tabela');
var IMOVEL = { ref: 'EX-1', nome: 'T2 Exemplo', proprietario: { nome: 'Senhorio Exemplo', iban: 'PT50 0000 0000 1234 5678 9013 5', titular: 'Senhorio Exemplo' },
  inquilino: { nome: 'Inquilina', email: 'inquilina@example.com', whatsapp: '912 345 678' }, mensagem: { assinatura: 'Gestão Exemplo' } };
var DESPESAS = [
  { id: 'a', tipo: 'agua', fornecedor: 'EPAL', periodo: { de: '2026-08-01', ate: '2026-08-31' }, data_limite: '2026-09-25', total: 3847, percentagem: 100, valor: 3847, estado: 'nova' },
  { id: 'b', tipo: 'eletricidade', fornecedor: 'EDP Comercial', periodo: { de: '2026-07-05', ate: '2026-08-04' }, data_limite: '2026-08-28', total: 6412, percentagem: 100, valor: 6412, estado: 'enviada' },
  { id: 'c', tipo: 'internet', fornecedor: 'MEO', periodo: { mes: '2026-07' }, data_limite: '2026-08-20', total: 4199, percentagem: 100, valor: 4199, estado: 'paga' },
  { id: 'd', tipo: 'aquecimento', fornecedor: 'Climaespaço', periodo: { de: '2026-08-01', ate: '2026-08-31' }, data_limite: '2026-10-15', total: 2734, percentagem: 50, valor: 1367, estado: 'nova' }
];
teste('só novas e em dívida; as em dívida primeiro; pagas ficam de fora', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06' });
  igual(t.ids, ['b', 'a', 'd']);
  igual(t.total, 6412 + 3847 + 1367);
  naoContem(t.html, 'MEO');
  naoContem(t.texto, 'MEO');
  naoContem(t.whatsapp, 'MEO');
});
teste('HTML: tabela limpa com estilos em linha, nota de cortesia só nas em dívida', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06' });
  contem(t.html, 'Olá Inquilina,');
  contem(t.html, 'Eletricidade (EDP Comercial)<br><span style="font-size:12px;color:#8a5200">Em dívida — caso já tenha pago, ignore esta linha.</span>');
  igual((t.html.match(/caso já tenha pago/g) || []).length, 1);
  contem(t.html, '13,67 €<br><span style="font-size:12px;color:#5f6b62">50% de 27,34 €</span>');
  contem(t.html, 'Total</td><td style="padding:8px 12px;border:1px solid #d9d1bf;vertical-align:top;text-align:right;font-weight:bold;white-space:nowrap">116,26 €');
  contem(t.html, 'IBAN PT50 0000 0000 1234 5678 9013 5 (titular: Senhorio Exemplo)');
  naoContem(t.html, '<style');
  ['tr', 'td', 'th', 'table', 'p', 'div', 'span'].forEach(function (tag) {
    igual((t.html.match(new RegExp('<' + tag + '[ >]', 'g')) || []).length, (t.html.match(new RegExp('</' + tag + '>', 'g')) || []).length, 'etiquetas ' + tag);
  });
});
teste('texto simples alinhado, com asterisco nas em dívida', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06' });
  var linhas = t.texto.split('\n');
  var cab = linhas.filter(function (l) { return /^Despesa/.test(l); })[0];
  var edp = linhas.filter(function (l) { return /^Eletricidade/.test(l); })[0];
  var total = linhas.filter(function (l) { return /^Total/.test(l); })[0];
  verdade(/ \*$/.test(edp), 'asterisco: ' + edp);
  igual(total.length, cab.length, 'Total alinhado com o cabeçalho');
  contem(t.texto, '* Em dívida — caso já tenha pago, ignore esta linha.');
  contem(t.texto, '01/08 a 31/08/2026');
  contem(t.texto, 'Obrigado,\nGestão Exemplo');
});
teste('WhatsApp: uma linha por despesa, total a negrito', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06' });
  contem(t.whatsapp, '• Água (EPAL), 01/08 a 31/08/2026: *38,47 €* — pagar até 25/09/2026');
  contem(t.whatsapp, '• Aquecimento (Climaespaço), 01/08 a 31/08/2026: *13,67 € (50% de 27,34 €)*');
  contem(t.whatsapp, '_Em dívida — caso já tenha pago, ignore esta linha._');
  contem(t.whatsapp, '*Total: 116,26 €*');
  naoContem(t.whatsapp, '<');
});
teste('assunto e ligações para o email e o WhatsApp', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06' });
  igual(t.assunto, 'Despesas — T2 Exemplo (outubro 2026)');
  igual(Despesas.tabela.ligacaoWhatsapp('912 345 678', 'olá'), 'https://wa.me/351912345678?text=ol%C3%A1');
  igual(Despesas.tabela.ligacaoWhatsapp('+44 7700 900123', 'x'), 'https://wa.me/447700900123?text=x');
  igual(Despesas.tabela.ligacaoEmail('inquilina@example.com', 'A b', 'c\nd'), 'mailto:inquilina@example.com?subject=A%20b&body=c%0Ad');
});
teste('pagamento ao senhorio: IBAN, MB WAY ou os dois', function () {
  var so = { nome: 'X', proprietario: { mbway: '912345678' } };
  igual(Despesas.tabela.linhaPagamento(so), 'Pagamento por MB WAY para o 912 345 678.');
  var ambos = { nome: 'X', proprietario: { iban: 'PT50 0000 0000 1234 5678 9013 5', titular: 'Senhorio', mbway: '+351 912 345 678' } };
  igual(Despesas.tabela.linhaPagamento(ambos), 'Pagamento por transferência bancária para o IBAN PT50 0000 0000 1234 5678 9013 5 (titular: Senhorio) ou por MB WAY para o 912 345 678.');
  var t = Despesas.tabela.gerar(so, DESPESAS, { hoje: '2026-10-06' });
  igual(t.avisos, []);
  contem(t.whatsapp, 'Pagamento por MB WAY para o 912 345 678.');
  contem(t.html, 'Pagamento por MB WAY para o 912 345 678.');
});
teste('a mensagem pede a confirmação do pagamento (com comprovativo) e o email leva a caixa em CC', function () {
  var t = Despesas.tabela.gerar(IMOVEL, DESPESAS, { hoje: '2026-10-06', emailRespostas: 'contas@example.com' });
  var pedido = 'Depois de pagar, por favor confirme respondendo a esta mensagem (se possível, com o comprovativo de pagamento). Também pode enviar para contas@example.com.';
  contem(t.html, pedido);
  contem(t.texto, pedido);
  contem(t.whatsapp, pedido);
  igual(Despesas.tabela.ligacaoEmail('inquilina@example.com', 'A', 'b', 'contas@example.com'), 'mailto:inquilina@example.com?cc=contas@example.com&subject=A&body=b');
});
teste('lembrete: sem resposta há 5 dias; um lembrete ou um «ainda não» recomeçam a contagem', function () {
  var base = { id: 'x', tipo: 'agua', fornecedor: 'EPAL', valor: 3847, estado: 'enviada', enviada_em: '2026-10-01T10:00:00+01:00' };
  var P = Despesas.tabela.precisaLembrete;
  igual(P([base], '2026-10-05', 5), null);
  igual(P([base], '2026-10-06', 5), { ids: ['x'], dias: 5 });
  igual(P([JSON.parse(JSON.stringify(base)), { id: 'p', estado: 'paga', enviada_em: '2026-09-01' }], '2026-10-06', 5).ids, ['x']);
  var lembrado = clonar(base); lembrado.lembretes = ['2026-10-06T09:00:00+01:00'];
  igual(P([lembrado], '2026-10-10', 5), null);
  igual(P([lembrado], '2026-10-11', 5).dias, 5);
  var nao = clonar(base); nao.ultima_resposta = { quando: '2026-10-08T09:00:00+01:00', valor: 'nao' };
  igual(P([nao], '2026-10-12', 5), null);
  var l = Despesas.tabela.lembrete(IMOVEL, [base], { emailRespostas: 'contas@example.com' });
  contem(l.texto, 'Olá Inquilina,\n\nEnviámos a 01/10/2026 as despesas do apartamento T2 Exemplo, no total de 38,47 €:\n• Água (EPAL) — 38,47 €');
  contem(l.texto, 'Já fez o pagamento? Basta responder «sim» ou «não»');
  contem(l.whatsapp, '*Já fez o pagamento?*');
  igual(l.assunto, 'Despesas — T2 Exemplo: já fez o pagamento?');
  igual(l.ids, ['x']);
});
teste('sem IBAN do senhorio → aviso; sem despesas → vazia', function () {
  var t = Despesas.tabela.gerar({ nome: 'X' }, DESPESAS, { hoje: '2026-10-06' });
  contem(t.avisos.join(' '), 'Falta o IBAN ou o MB WAY');
  contem(t.texto, 'combinar com o senhorio');
  contem(t.texto, 'Olá,');
  igual(Despesas.tabela.gerar(IMOVEL, [DESPESAS[2]]).vazia, true);
});

load(BASE + '/testes/js/pagina.js');

print('\n' + (total - falhas) + '/' + total + ' testes passaram' + (falhas ? ' — ' + falhas + ' FALHARAM' : ''));
if (falhas) throw new Error(falhas + ' testes falharam');
