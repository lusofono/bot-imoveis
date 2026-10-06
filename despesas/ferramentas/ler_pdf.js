/* Ler uma fatura real com o mesmo motor da página, aqui no Mac (para afinar as regras com o Claude).
   Uso:  sh ferramentas/ler_pdf.sh amostras/fatura.pdf [remetente] [assunto]
   Mostra o texto tal como o motor o vê e o que as regras tiram dele. Os PDFs reais ficam em amostras/ (fora do Git). */
var BASE = arguments[0], ficheiro = arguments[1], remetente = arguments[2] || '', assunto = arguments[3] || '';
load(BASE + '/publico/motor/util.js');
load(BASE + '/publico/motor/pdf.js');
load(BASE + '/publico/motor/regras.js');
var regras = JSON.parse(readFile(BASE + '/publico/motor/fornecedores.json'));
var imoveis = [];
try {
  var lista = readFile(BASE + '/dados/.lista-imoveis').split('\n').filter(function (l) { return l.trim(); });
  imoveis = lista.map(function (p) { var j = JSON.parse(readFile(p)); j.ref = j.ref || p.split('/').slice(-2)[0]; j.remetentes = (j.remetentes || []).concat(j.proprietario && j.proprietario.email ? [j.proprietario.email.toLowerCase()] : []); return j; });
} catch (e) { /* sem imóveis locais: a análise do imóvel fica por fazer */ }
var r = Despesas.pdf.extrair(readFile(ficheiro, 'binary'));
print('══ TEXTO (' + r.paginas.length + ' página(s); temTexto=' + r.temTexto + '; protegido=' + r.protegido + ') ══');
print(r.texto);
if (r.avisos.length) print('\n══ AVISOS DO PDF ══\n' + r.avisos.join('\n'));
var a = Despesas.regras.analisar(r.texto, { regras: regras, imoveis: imoveis, remetente: remetente.toLowerCase(), assunto: assunto });
var resumo = {};
Object.keys(a).forEach(function (k) { if (k !== 'valores' && k !== 'datas') resumo[k] = a[k]; });
print('\n══ ANÁLISE ══\n' + JSON.stringify(resumo, null, 2));
print('\n══ VALORES NO PDF ══\n' + a.valores.map(function (v) { return Despesas.util.formatarValor(v.cent) + '   ← ' + v.contexto; }).join('\n'));
print('\n══ DATAS NO PDF ══\n' + a.datas.join(', '));
