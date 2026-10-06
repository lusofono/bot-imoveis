/* Despesas — ler uma fatura a partir do texto do PDF, com regras (sem IA).
   1. Identifica o fornecedor pelas regras de publico/motor/fornecedores.json (pontos por textos e NIF).
   2. O tipo vem do fornecedor (água, eletricidade, internet, aquecimento); outro tipo ou dúvida → aviso.
   3. O total, a data-limite e o período procuram-se a seguir aos rótulos («Total a pagar», «Data limite»…),
      na mesma linha ou nas duas seguintes. O pagamento: débito direto, Multibanco (entidade + referência) ou IBAN.
   4. O imóvel sai dos identificadores da pasta do imóvel (CPE, n.º de cliente…), do assunto do email (o nome do imóvel,
      do proprietário ou uma alcunha) ou do remetente.
   Nada se adivinha: o que falta fica com aviso e a fatura fica «por identificar» (ou «por confirmar» quando a regra
   do fornecedor ainda não foi verificada com uma fatura real). */
var Despesas = (typeof Despesas !== 'undefined') ? Despesas : {};

Despesas.regras = (function () {
  'use strict';
  var U = Despesas.util;

  var MESES = { janeiro: 1, fevereiro: 2, marco: 3, abril: 4, maio: 5, junho: 6, julho: 7, agosto: 8, setembro: 9, outubro: 10,
    novembro: 11, dezembro: 12, jan: 1, fev: 2, mar: 3, abr: 4, mai: 5, jun: 6, jul: 7, ago: 8, set: 9, out: 10, nov: 11, dez: 12 };
  var NOMES_MESES = 'janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez';

  function escaparRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  // Procura um texto «palavra inteira»: no texto dobrado (sem acentos, minúsculas) ou, para siglas curtas em
  // maiúsculas (MEO, NOS, EDP), no texto original com as maiúsculas exatas.
  function encontra(texto, dobrado, alvo) {
    if (!alvo) return -1;
    var exato = /^[A-Z0-9]{2,5}$/.test(alvo);
    var base = exato ? texto : dobrado, a = exato ? alvo : U.dobrar(alvo);
    var re = new RegExp('(^|[^A-Za-z0-9])' + escaparRe(a) + '(?=$|[^A-Za-z0-9])', exato ? '' : 'i');
    var m = re.exec(base);
    return m ? m.index + m[1].length : -1;
  }

  function semEspacos(s) { return U.dobrar(String(s || '')).replace(/[\s.,\-\/]/g, '').toLowerCase(); }

  // ── Valores e datas ──────────────────────────────────────────────────────────────────────────
  var RE_VALOR = /(-\s?)?(?:€\s?)?(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(?![\d,])(\s?(?:€|EUR))?(?!\s?%)/g;

  function valores(texto) {
    var lista = [], m;
    RE_VALOR.lastIndex = 0;
    while ((m = RE_VALOR.exec(texto))) {
      var antes = texto.charAt(m.index - 1);
      if (antes && /[\d\/]/.test(antes)) continue; // parte de outro número ou data
      var cent = parseInt(m[2].replace(/\./g, ''), 10) * 100 + parseInt(m[3], 10);
      if (m[1]) cent = -cent;
      var iniLinha = texto.lastIndexOf('\n', m.index) + 1;
      var contexto = texto.substring(iniLinha, m.index).replace(/\s+/g, ' ').trim();
      if (contexto.length > 60) contexto = '…' + contexto.slice(-60);
      lista.push({ cent: cent, inicio: m.index, fim: m.index + m[0].length, euro: !!m[4] || m[0].indexOf('€') >= 0, contexto: contexto });
    }
    return lista;
  }

  var RE_DATA = new RegExp('(?:^|[^\\d])(?:(\\d{1,2})[\\/.\\-](\\d{1,2})[\\/.\\-](\\d{4})|(\\d{4})-(\\d{2})-(\\d{2})|(\\d{1,2})\\s+(?:de\\s+)?(' +
    NOMES_MESES + ')\\.?\\s+(?:de\\s+)?(\\d{4}))(?![\\d])', 'g');

  function datas(dobrado) {
    var lista = [], m;
    RE_DATA.lastIndex = 0;
    while ((m = RE_DATA.exec(dobrado))) {
      var a, me, d;
      if (m[3]) { d = +m[1]; me = +m[2]; a = +m[3]; }
      else if (m[4]) { a = +m[4]; me = +m[5]; d = +m[6]; }
      else { d = +m[7]; me = MESES[m[8]]; a = +m[9]; }
      var inicio = m.index + (m[0].length - m[0].replace(/^[^\d]/, '').length);
      if (U.dataValida(a, me, d)) lista.push({ iso: U.iso(a, me, d), inicio: inicio, fim: m.index + m[0].length });
      RE_DATA.lastIndex = m.index + m[0].length;
    }
    return lista;
  }

  function mesAno(dobrado) {
    var re = new RegExp('(?:^|[^a-z])(' + NOMES_MESES + ')\\.?\\s*(?:de\\s+|\\/\\s*|-\\s*)?(\\d{4})(?!\\d)'), m = re.exec(dobrado);
    if (m) return U.iso(+m[2], MESES[m[1]], 1).slice(0, 7);
    m = /(?:^|[^\d\/])(\d{2})\/(\d{4})(?![\d\/])/.exec(dobrado);
    if (m && +m[1] >= 1 && +m[1] <= 12) return m[2] + '-' + m[1];
    return null;
  }

  // Texto a seguir a um rótulo: o resto da linha e as «extra» linhas seguintes.
  function trechoDepois(dobrado, posFim, extra) {
    var fim = posFim;
    for (var i = 0; i <= extra; i++) {
      var nl = dobrado.indexOf('\n', fim + (i ? 1 : 0));
      if (nl < 0) { fim = dobrado.length; break; }
      fim = nl;
    }
    return { inicio: posFim, fim: fim };
  }

  function ocorrencias(dobrado, rotulo) {
    var r = U.dobrar(rotulo), re = new RegExp('(^|[^a-z0-9])' + escaparRe(r) + '(?=$|[^a-z0-9])', 'g'), lista = [], m;
    while ((m = re.exec(dobrado))) { lista.push(m.index + m[1].length + r.length); re.lastIndex = m.index + m[0].length; }
    return lista;
  }

  function procurarTotal(texto, dobrado, rotulos, lista) {
    for (var i = 0; i < rotulos.length; i++) {
      var pos = ocorrencias(dobrado, rotulos[i]);
      for (var k = 0; k < pos.length; k++) {
        var tr = trechoDepois(dobrado, pos[k], 2);
        for (var j = 0; j < lista.length; j++) {
          var v = lista[j];
          if (v.inicio >= tr.inicio && v.inicio < tr.fim) return { cent: v.cent, rotulo: rotulos[i] };
        }
      }
    }
    return null;
  }

  function procurarData(dobrado, rotulos, lista) {
    for (var i = 0; i < rotulos.length; i++) {
      var pos = ocorrencias(dobrado, rotulos[i]);
      for (var k = 0; k < pos.length; k++) {
        var tr = trechoDepois(dobrado, pos[k], 1);
        for (var j = 0; j < lista.length; j++) if (lista[j].inicio >= tr.inicio && lista[j].inicio < tr.fim) return lista[j].iso;
      }
    }
    return null;
  }

  function procurarPeriodo(dobrado, rotulos, lista) {
    for (var i = 0; i < rotulos.length; i++) {
      var pos = ocorrencias(dobrado, rotulos[i]);
      for (var k = 0; k < pos.length; k++) {
        var tr = trechoDepois(dobrado, pos[k], 1);
        var dentro = lista.filter(function (d) { return d.inicio >= tr.inicio && d.inicio < tr.fim; });
        if (dentro.length >= 2 && dentro[0].iso <= dentro[1].iso) return { de: dentro[0].iso, ate: dentro[1].iso };
        var linha = dobrado.substring(tr.inicio, dobrado.indexOf('\n', tr.inicio) < 0 ? dobrado.length : dobrado.indexOf('\n', tr.inicio));
        var mes = mesAno(linha);
        if (mes) return { mes: mes };
      }
    }
    // Sem rótulo: duas datas ligadas por «a», «até» ou um traço.
    for (var j = 0; j + 1 < lista.length; j++) {
      var entre = dobrado.substring(lista[j].fim, lista[j + 1].inicio);
      if (/^\s*(?:a|ate|-|–|—)\s*$/.test(entre) && lista[j].iso <= lista[j + 1].iso) return { de: lista[j].iso, ate: lista[j + 1].iso };
    }
    return null;
  }

  function ibanValido(iban) {
    var s = iban.replace(/\s+/g, '').toUpperCase();
    if (!/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/.test(s)) return false;
    var r = s.slice(4) + s.slice(0, 4), resto = 0;
    for (var i = 0; i < r.length; i++) {
      var c = r.charCodeAt(i), v = (c >= 65) ? String(c - 55) : r[i];
      for (var k = 0; k < v.length; k++) resto = (resto * 10 + (+v[k])) % 97;
    }
    return resto === 1;
  }
  function agruparIban(iban) { return iban.replace(/\s+/g, '').toUpperCase().replace(/(.{4})/g, '$1 ').trim(); }

  // Um número que não é pedaço de outro maior (sem lookbehind: os Safari antigos não o conhecem).
  function primeiroNumero(s, re) {
    re.lastIndex = 0;
    var m;
    while ((m = re.exec(s))) { if (m.index === 0 || !/\d/.test(s.charAt(m.index - 1))) return m; re.lastIndex = m.index + 1; }
    return null;
  }

  // O bloco Multibanco (entidade, referência, montante), seja qual for a arrumação: tudo na mesma linha, o rótulo em
  // cima e o valor em baixo, ou os três rótulos seguidos e depois os três valores. Parte de cada «referência» com nove
  // algarismos à frente e procura a «entidade» e o «montante» mais perto dela.
  function blocoMultibanco(dobrado, lista) {
    var reRef = /referencia|ref\./g, m;
    while ((m = reRef.exec(dobrado))) {
      var ini = m.index + m[0].length;
      var mr = primeiroNumero(dobrado.substring(ini, ini + 160), /(\d{3}) ?(\d{3}) ?(\d{3})(?!\d)/g);
      if (!mr) continue;
      var ent = null, reEnt = /entidade/g, me;
      while ((me = reEnt.exec(dobrado))) {
        var dist = Math.abs(me.index - m.index);
        if (dist > 250) continue;
        var ne = primeiroNumero(dobrado.substring(me.index + 8, me.index + 128), /(\d{5})(?!\d)/g);
        if (ne && (!ent || dist < ent.dist)) ent = { dist: dist, valor: ne[1] };
      }
      if (!ent) continue;
      var bloco = { entidade: ent.valor, referencia: mr[1] + ' ' + mr[2] + ' ' + mr[3] }, mont = null, reM = /montante/g, mm;
      while ((mm = reM.exec(dobrado))) {
        var d2 = Math.abs(mm.index - m.index), desde = mm.index + 8;
        if (d2 > 300) continue;
        var v = lista.filter(function (x) { return x.inicio >= desde && x.inicio < desde + 140; })[0];
        if (v && (!mont || d2 < mont.dist)) mont = { dist: d2, cent: v.cent };
      }
      if (mont) bloco.montante = mont.cent;
      return bloco;
    }
    return null;
  }

  // Débito direto só conta se estiver ativo («será debitado na sua conta»); «adira ao débito direto» é um convite.
  var DD_ATIVO = /(sera|vai ser|e|foi) (debitad|cobrad)|debitad[oa] na (sua )?conta|pagamento (sera |e )?(efetuado |feito )?por debito dire(c)?to|cobranca por debito dire(c)?to|valor a debitar|data (de|do) debito|cobrado na sua conta/;
  var DD_CONVITE = /(adira|aderir|adesao|ative|ativar|subscreva|ainda nao aderiu|pode ativa)[^\n]{0,80}debito dire(c)?to|debito dire(c)?to[^\n]{0,120}(aderir|adira|ativar|ative|ainda nao aderiu)/;

  function pagamento(texto, dobrado, lista) {
    var p = { metodo: null };
    if (dobrado.split(/\n|\.\s/).some(function (f) { return DD_ATIVO.test(f) && !DD_CONVITE.test(f); })) p.metodo = 'debito_direto';
    var mb = blocoMultibanco(dobrado, lista);
    if (mb) {
      p.entidade = mb.entidade;
      p.referencia = mb.referencia;
      if (mb.montante !== undefined) p.montante = mb.montante;
      if (!p.metodo) p.metodo = 'multibanco';
    }
    var reIban = /\bPT\s?50(?:\s?\d){21}(?!\d)/g, mi;
    while ((mi = reIban.exec(texto))) {
      if (ibanValido(mi[0])) {
        // No débito direto o IBAN que aparece é o do cliente: não se guarda.
        if (p.metodo !== 'debito_direto') { p.iban = agruparIban(mi[0]); if (!p.metodo) p.metodo = 'transferencia'; }
        break;
      }
    }
    return p;
  }

  // ── Fornecedor e imóvel ──────────────────────────────────────────────────────────────────────
  function identificarFornecedor(texto, dobrado, regras, remetente) {
    var pontos = [], plano = semEspacos(texto);
    (regras.fornecedores || []).forEach(function (f) {
      var id = f.identificar || {}, p = 0, contados = {};
      if ((id.excluir || []).some(function (t) { return encontra(texto, dobrado, t) >= 0; })) return;
      // Variantes do mesmo texto (com e sem acentos) contam uma só vez.
      var conta = function (t, valor) {
        var k = U.dobrar(t);
        if (!contados[k] && encontra(texto, dobrado, t) >= 0) { contados[k] = 1; p += valor; }
      };
      (id.fortes || []).forEach(function (t) { conta(t, 3); });
      (id.fracos || []).forEach(function (t) { conta(t, 1); });
      (id.nif || []).forEach(function (n) { if (n && plano.indexOf(semEspacos(n)) >= 0) p += 5; });
      (id.remetentes || []).forEach(function (r) { if (remetente && remetente.toLowerCase().indexOf(r.toLowerCase()) >= 0) p += 3; });
      if (p > 0) pontos.push({ f: f, p: p });
    });
    pontos.sort(function (a, b) { return b.p - a.p; });
    if (!pontos.length || pontos[0].p < 3) return { fornecedor: null, ambiguo: false };
    if (pontos.length > 1 && pontos[1].p === pontos[0].p) return { fornecedor: null, ambiguo: true, candidatos: [pontos[0].f.nome, pontos[1].f.nome] };
    return { fornecedor: pontos[0].f, ambiguo: false };
  }

  // Termos que identificam um imóvel no assunto do email: a referência, o nome, o nome do proprietário e as alcunhas.
  function termosImovel(im) {
    return [im.ref, im.nome, (im.proprietario || {}).nome].concat(im.apelidos || [])
      .filter(function (t) { return t && String(t).trim().length >= 3; });
  }
  function noAssunto(assunto, im) {
    var d = U.dobrar(assunto || '');
    return termosImovel(im).some(function (t) {
      return new RegExp('(^|[^a-z0-9])' + escaparRe(U.dobrar(String(t).trim())) + '(?=$|[^a-z0-9])').test(d);
    });
  }

  // Ordem: identificadores na fatura (CPE, n.º de cliente…), depois o assunto do email (quando é o administrador a
  // reencaminhar, escreve lá o proprietário ou o imóvel), depois o remetente. Se discordarem, não se escolhe.
  function identificarImovel(texto, imoveis, remetente, assunto) {
    imoveis = imoveis || [];
    var plano = semEspacos(texto);
    var porId = imoveis.filter(function (im) {
      return (im.identificadores || []).some(function (idt) {
        var v = (typeof idt === 'string') ? idt : (idt && idt.valor);
        return v && semEspacos(v).length >= 4 && plano.indexOf(semEspacos(v)) >= 0;
      });
    });
    var porAssunto = assunto ? imoveis.filter(function (im) { return noAssunto(assunto, im); }) : [];
    var rem = (remetente || '').toLowerCase();
    var porRem = imoveis.filter(function (im) { return (im.remetentes || []).some(function (r) { return r && r.toLowerCase() === rem; }); });
    var nomes = function (l) { return l.map(function (i) { return '«' + i.nome + '»'; }).join(', '); };
    var comum = function (a, b) { return a.filter(function (x) { return b.indexOf(x) >= 0; }); };

    if (porId.length === 1) {
      if (porAssunto.length === 1 && porAssunto[0] !== porId[0])
        return { imovel: null, aviso: 'O assunto do email aponta para ' + nomes(porAssunto) + ' mas a fatura é de ' + nomes(porId) + ' (pelos identificadores): escolher o imóvel.' };
      return { imovel: porId[0].ref, por: 'identificador' };
    }
    if (porId.length > 1) {
      var ambos = comum(porId, porAssunto.length ? porAssunto : porRem);
      if (ambos.length === 1) return { imovel: ambos[0].ref, por: 'identificador' };
      return { imovel: null, aviso: 'A fatura corresponde a mais do que um imóvel (' + nomes(porId) + '): escolher o imóvel.' };
    }
    if (porAssunto.length === 1) return { imovel: porAssunto[0].ref, por: 'assunto' };
    if (porAssunto.length > 1) {
      var r2 = comum(porAssunto, porRem);
      if (r2.length === 1) return { imovel: r2[0].ref, por: 'assunto' };
      return { imovel: null, aviso: 'O assunto do email corresponde a mais do que um imóvel (' + nomes(porAssunto) + '): escolher o imóvel.' };
    }
    if (porRem.length === 1) return { imovel: porRem[0].ref, por: 'remetente' };
    if (porRem.length > 1) return { imovel: null, aviso: 'Este remetente tem mais do que um imóvel e nem a fatura (CPE, n.º de cliente…) nem o assunto dizem qual: escolher o imóvel.' };
    return { imovel: null, aviso: 'Não sei de que imóvel é esta fatura (escreve o proprietário ou o imóvel no assunto quando reencaminhares): escolher o imóvel.' };
  }

  // ── Análise completa ─────────────────────────────────────────────────────────────────────────
  // contexto: { regras (fornecedores.json), imoveis: [{ref, nome, apelidos, proprietario, remetentes, identificadores}], remetente, assunto }
  function analisar(texto, contexto) {
    contexto = contexto || {};
    var regras = contexto.regras || { fornecedores: [], tipos: {}, rotulos_padrao: {} };
    var r = { fornecedor: null, tipo: null, total: null, periodo: null, data_limite: null, pagamento: { metodo: null },
      imovel: null, estado: 'por_identificar', avisos: [], valores: [], datas: [] };
    texto = String(texto || '');
    var dobrado = U.dobrar(texto);
    var lista = valores(texto), listaDatas = datas(dobrado);
    var vistos = {};
    r.valores = lista.filter(function (v) { var k = v.cent + '|' + v.contexto; if (vistos[k]) return false; vistos[k] = 1; return v.cent > 0; })
      .slice(0, 80).map(function (v) { return { cent: v.cent, contexto: v.contexto }; });
    r.datas = listaDatas.map(function (d) { return d.iso; }).filter(function (d, i, a) { return a.indexOf(d) === i; }).slice(0, 30);

    if (texto.replace(/[\s�]/g, '').length < 20) {
      r.avisos.push('Sem texto para ler: identificar à mão.');
      return r;
    }

    var idf = identificarFornecedor(texto, dobrado, regras, contexto.remetente);
    var f = idf.fornecedor;
    if (f) r.fornecedor = { id: f.id, nome: f.nome, verificado: !!f.verificado };
    else if (idf.ambiguo) r.avisos.push('Não consegui decidir o fornecedor (' + idf.candidatos.join(' ou ') + '): identificar à mão.');
    else r.avisos.push('Fornecedor desconhecido: não é nenhum dos fornecedores de água, eletricidade, gás, internet ou aquecimento que conheço. Se for um destes tipos, identificar à mão (e trazer o PDF ao Claude para a regra).');

    var tipos = regras.tipos || {};
    if (f) {
      if (!tipos[f.tipo]) r.avisos.push('O tipo «' + f.tipo + '» não é um dos tipos de despesa (água, eletricidade, gás, internet, aquecimento).');
      else r.tipo = f.tipo;
      if (f.gas && /gas natural|\bgas\b.*\bkwh\b/.test(dobrado)) {
        r.tipo = null;
        r.avisos.push('A fatura fala em gás natural: pode ser de gás ou de luz e gás juntas. Confirmar o tipo (e, se forem as duas, dividir à mão).');
      }
      if (r.tipo && tipos[r.tipo].sinais && !tipos[r.tipo].sinais.some(function (s) { return encontra(texto, dobrado, s) >= 0 || dobrado.indexOf(U.dobrar(s)) >= 0; }))
        r.avisos.push('Não encontrei palavras de ' + tipos[r.tipo].nome.toLowerCase() + ' na fatura: confirmar o tipo.');
    }

    var rot = function (campo) {
      var proprios = f && f.rotulos && f.rotulos[campo];
      return (proprios && proprios.length) ? proprios : ((regras.rotulos_padrao || {})[campo] || []);
    };
    // O total: o montante da referência Multibanco (é o que se paga); o «total a pagar» da fatura confirma-o.
    r.pagamento = pagamento(texto, dobrado, lista);
    var tot = procurarTotal(texto, dobrado, rot('total'), lista), mont = r.pagamento.montante;
    if (typeof mont === 'number' && mont > 0) r.total = mont;
    else if (tot && tot.cent > 0) r.total = tot.cent;
    else if (tot) r.avisos.push('O total encontrado é zero ou negativo (nota de crédito?): identificar à mão.');
    else r.avisos.push('Não encontrei o total a pagar: escolher o valor certo entre os do PDF.');

    r.data_limite = procurarData(dobrado, rot('data_limite'), listaDatas);
    r.periodo = procurarPeriodo(dobrado, rot('periodo'), listaDatas);

    var im = identificarImovel(texto, contexto.imoveis, contexto.remetente, contexto.assunto);
    r.imovel = im.imovel;
    if (im.aviso) r.avisos.push(im.aviso);

    var avisosLeves = [];
    if (!r.data_limite) avisosLeves.push('Sem data-limite de pagamento.');
    if (!r.periodo) avisosLeves.push('Sem período.');
    if (!r.pagamento.metodo) avisosLeves.push('Não encontrei como se paga (débito direto, Multibanco ou IBAN).');
    var conflito = typeof mont === 'number' && mont > 0 && tot && tot.cent > 0 && tot.cent !== mont;
    if (conflito) r.avisos.push('O total da fatura (' + U.formatarValor(tot.cent) + ') não bate com o montante da referência Multibanco (' + U.formatarValor(mont) + '): confirmar.');

    if (!r.fornecedor || !r.tipo || r.total === null || !r.imovel) r.estado = 'por_identificar';
    else if (!r.fornecedor.verificado || conflito || r.avisos.length) r.estado = 'por_confirmar';
    else r.estado = 'lida';
    if (r.estado === 'por_confirmar' && !r.fornecedor.verificado) r.avisos.push('A regra de ' + r.fornecedor.nome + ' ainda não foi verificada com uma fatura real: confirmar os valores.');
    r.avisos = r.avisos.concat(avisosLeves);
    return r;
  }

  return {
    analisar: analisar, valores: valores, blocoMultibanco: function (t) { return blocoMultibanco(U.dobrar(t), valores(t)); }, datas: function (t) { return datas(U.dobrar(t)); }, ibanValido: ibanValido,
    identificarFornecedor: function (texto, regras, remetente) { return identificarFornecedor(texto, U.dobrar(texto), regras, remetente); },
    identificarImovel: identificarImovel, pagamento: function (t) { var d = U.dobrar(t); return pagamento(t, d, valores(t)); }
  };
})();
