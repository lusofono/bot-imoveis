/* Despesas — a mensagem para o inquilino: a tabela das despesas novas e das que estão em dívida, o total, como
   pagar ao senhorio e o pedido de confirmação do pagamento (com o comprovativo); e o lembrete para quem não respondeu. Sai em três formas: HTML com estilos em linha (cola bem no Gmail), texto simples e texto para
   WhatsApp (que não tem tabelas: uma linha por despesa, *negrito* no valor). Mais as ligações que abrem o email ou o
   WhatsApp já preenchidos — quem envia é sempre a pessoa; a aplicação nunca envia nada. */
var Despesas = (typeof Despesas !== 'undefined') ? Despesas : {};

Despesas.tabela = (function () {
  'use strict';
  var U = Despesas.util;
  var NOME_TIPO = { agua: 'Água', eletricidade: 'Eletricidade', gas: 'Gás', internet: 'Internet', aquecimento: 'Aquecimento' };
  var NOTA_DIVIDA = 'Em dívida — caso já tenha pago, ignore esta linha.';

  function formatarPeriodo(p) {
    if (!p) return '—';
    if (p.mes) return U.formatarData(p.mes);
    if (p.de && p.ate) {
      var de = U.formatarData(p.de), ate = U.formatarData(p.ate);
      if (p.de.slice(0, 4) === p.ate.slice(0, 4)) de = de.slice(0, 5);
      return de + ' a ' + ate;
    }
    return '—';
  }

  function nomeDespesa(d) {
    var t = NOME_TIPO[d.tipo] || d.tipo || 'Despesa';
    return d.fornecedor ? t + ' (' + d.fornecedor + ')' : t;
  }

  // As despesas que entram: novas e enviadas por pagar (em dívida). Primeiro as em dívida, depois por data-limite.
  function selecionar(despesas) {
    return (despesas || []).filter(function (d) { return (d.estado === 'nova' || d.estado === 'enviada') && typeof d.valor === 'number'; })
      .sort(function (a, b) {
        if (a.estado !== b.estado) return a.estado === 'enviada' ? -1 : 1;
        return (a.data_limite || '9999').localeCompare(b.data_limite || '9999') || (a.tipo || '').localeCompare(b.tipo || '');
      });
  }

  // O inquilino paga ao senhorio: por transferência para o IBAN do contrato e/ou por MB WAY para o telemóvel dele.
  function formatarTelefone(t) {
    var d = String(t || '').replace(/[^\d+]/g, '');
    var m = /^(?:\+?351)?(9\d{2})(\d{3})(\d{3})$/.exec(d);
    return m ? m[1] + ' ' + m[2] + ' ' + m[3] : String(t || '').trim();
  }
  function linhaPagamento(imovel) {
    var p = (imovel && imovel.proprietario) || {}, formas = [];
    if (p.iban) formas.push('por transferência bancária para o IBAN ' + p.iban + (p.titular ? ' (titular: ' + p.titular + ')' : ''));
    if (p.mbway) formas.push('por MB WAY para o ' + formatarTelefone(p.mbway));
    if (!formas.length) return 'Pagamento: combinar com o senhorio.';
    return 'Pagamento ' + formas.join(' ou ') + '.';
  }

  function textoValor(d) {
    var s = U.formatarValor(d.valor);
    if (typeof d.percentagem === 'number' && d.percentagem !== 100 && typeof d.total === 'number')
      s += ' (' + d.percentagem + '% de ' + U.formatarValor(d.total) + ')';
    return s;
  }

  function preencher(s, largura, direita) {
    s = String(s);
    if (s.length >= largura) return s;
    var esp = new Array(largura - s.length + 1).join(' ');
    return direita ? esp + s : s + esp;
  }

  // imovel: {nome, proprietario:{iban,titular,mbway}, inquilino:{nome,email,whatsapp}, mensagem:{assinatura}}
  // opcoes: {hoje: 'AAAA-MM-DD', assinatura, emailRespostas (a caixa onde as confirmações chegam à aplicação)}
  function gerar(imovel, despesas, opcoes) {
    opcoes = opcoes || {};
    imovel = imovel || {};
    var lista = selecionar(despesas), avisos = [];
    var inq = imovel.inquilino || {}, nomeImovel = imovel.nome || imovel.ref || 'o imóvel';
    var total = lista.reduce(function (s, d) { return s + d.valor; }, 0);
    var temDivida = lista.some(function (d) { return d.estado === 'enviada'; });
    var hoje = opcoes.hoje || new Date().toISOString().slice(0, 10);
    var assinatura = (imovel.mensagem && imovel.mensagem.assinatura) || opcoes.assinatura || '';
    if (!(imovel.proprietario && (imovel.proprietario.iban || imovel.proprietario.mbway)))
      avisos.push('Falta o IBAN ou o MB WAY do senhorio na pasta do imóvel: a mensagem diz «combinar com o senhorio».');
    var saudacao = 'Olá' + (inq.nome ? ' ' + inq.nome : '') + ',';
    var intro = 'Seguem as despesas do apartamento ' + nomeImovel + ' para pagamento:';
    var pagamento = linhaPagamento(imovel);
    var pedido = pedidoConfirmacao(opcoes.emailRespostas);
    var assunto = 'Despesas — ' + nomeImovel + ' (' + U.formatarData(hoje.slice(0, 7)) + ')';

    // HTML (estilos em linha: o Gmail ignora <style>)
    var E = U.escaparHtml;
    var cel = 'padding:8px 12px;border:1px solid #d9d1bf;vertical-align:top;';
    var cab = 'padding:8px 12px;border:1px solid #0a2e19;background:#14532d;color:#ffffff;text-align:left;font-weight:bold;';
    var h = [];
    h.push('<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.45;color:#1d2a22">');
    h.push('<p style="margin:0 0 12px">' + E(saudacao) + '</p>');
    h.push('<p style="margin:0 0 12px">' + E(intro) + '</p>');
    h.push('<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1d2a22">');
    h.push('<thead><tr><th style="' + cab + '">Despesa</th><th style="' + cab + '">Período</th><th style="' + cab + '">Pagar até</th>' +
      '<th style="' + cab + 'text-align:right">Valor</th></tr></thead><tbody>');
    lista.forEach(function (d) {
      var divida = d.estado === 'enviada';
      var fundo = divida ? 'background:#fff4dc;' : '';
      var nota = divida ? '<br><span style="font-size:12px;color:#8a5200">' + E(NOTA_DIVIDA) + '</span>' : '';
      var pct = (typeof d.percentagem === 'number' && d.percentagem !== 100 && typeof d.total === 'number')
        ? '<br><span style="font-size:12px;color:#5f6b62">' + E(d.percentagem + '% de ' + U.formatarValor(d.total)) + '</span>' : '';
      h.push('<tr><td style="' + cel + fundo + '">' + E(nomeDespesa(d)) + nota + '</td>' +
        '<td style="' + cel + fundo + 'white-space:nowrap">' + E(formatarPeriodo(d.periodo)) + '</td>' +
        '<td style="' + cel + fundo + 'white-space:nowrap">' + E(U.formatarData(d.data_limite)) + '</td>' +
        '<td style="' + cel + fundo + 'text-align:right;white-space:nowrap">' + E(U.formatarValor(d.valor)) + pct + '</td></tr>');
    });
    h.push('<tr><td colspan="3" style="' + cel + 'text-align:right;font-weight:bold">Total</td>' +
      '<td style="' + cel + 'text-align:right;font-weight:bold;white-space:nowrap">' + E(U.formatarValor(total)) + '</td></tr>');
    h.push('</tbody></table>');
    h.push('<p style="margin:12px 0 0">' + E(pagamento) + '</p>');
    h.push('<p style="margin:12px 0 0">' + E(pedido) + '</p>');
    h.push('<p style="margin:12px 0 0">Obrigado' + (assinatura ? ',<br>' + E(assinatura) : '.') + '</p>');
    h.push('</div>');

    // Texto simples (colunas alinhadas para quem lê em letra de largura fixa)
    var linhas = lista.map(function (d) {
      return [nomeDespesa(d), formatarPeriodo(d.periodo), U.formatarData(d.data_limite), textoValor(d), d.estado === 'enviada' ? '*' : ''];
    });
    var titulos = ['Despesa', 'Período', 'Pagar até', 'Valor'];
    var larg = [0, 1, 2, 3].map(function (i) {
      return Math.max(titulos[i].length, i === 3 ? U.formatarValor(total).length : 5, Math.max.apply(null, linhas.map(function (l) { return l[i].length; }).concat([0])));
    });
    var t = [saudacao, '', intro, ''];
    t.push(titulos.map(function (x, i) { return preencher(x, larg[i], i === 3); }).join('  '));
    t.push(larg.map(function (n) { return new Array(n + 1).join('-'); }).join('  '));
    linhas.forEach(function (l) {
      t.push((l.slice(0, 4).map(function (x, i) { return preencher(x, larg[i], i === 3); }).join('  ') + (l[4] ? ' *' : '')).replace(/\s+$/, ''));
    });
    t.push(new Array(larg[0] + larg[1] + larg[2] + larg[3] + 7).join('-'));
    t.push(preencher('Total', larg[0] + larg[1] + larg[2] + 6) + preencher(U.formatarValor(total), larg[3], true));
    if (temDivida) t.push('', '* ' + NOTA_DIVIDA);
    t.push('', pagamento, '', pedido, '', 'Obrigado' + (assinatura ? ',\n' + assinatura : '.'));

    // WhatsApp
    var w = [saudacao, intro, ''];
    lista.forEach(function (d) {
      var p = formatarPeriodo(d.periodo), lim = d.data_limite ? ' — pagar até ' + U.formatarData(d.data_limite) : '';
      w.push('• ' + nomeDespesa(d) + (p !== '—' ? ', ' + p : '') + ': *' + textoValor(d) + '*' + lim +
        (d.estado === 'enviada' ? '\n   _' + NOTA_DIVIDA + '_' : ''));
    });
    w.push('', '*Total: ' + U.formatarValor(total) + '*', '', pagamento, '', pedido, '', 'Obrigado' + (assinatura ? ',\n' + assinatura : '.'));

    return {
      vazia: lista.length === 0, ids: lista.map(function (d) { return d.id; }), total: total, assunto: assunto,
      html: h.join(''), texto: t.join('\n'), whatsapp: w.join('\n'), avisos: avisos
    };
  }

  // Pedir ao inquilino que confirme o pagamento (de preferência com o comprovativo): com isso regista-se «paga».
  function pedidoConfirmacao(emailRespostas) {
    return 'Depois de pagar, por favor confirme respondendo a esta mensagem (se possível, com o comprovativo de pagamento).' +
      (emailRespostas ? ' Também pode enviar para ' + emailRespostas + '.' : '');
  }

  // A data a partir da qual se conta o silêncio de uma despesa em dívida: o envio, o último lembrete ou a última
  // resposta «ainda não paguei» — a mais recente.
  function referenciaSilencio(d) {
    var datas = [d.enviada_em || ''].concat(d.lembretes || []);
    if (d.ultima_resposta && d.ultima_resposta.quando) datas.push(d.ultima_resposta.quando);
    return datas.sort().pop().slice(0, 10);
  }
  function diasEntre(a, b) {
    var t = function (s) { var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s); return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : NaN; };
    return Math.round((t(b) - t(a)) / 864e5);
  }

  // As despesas em dívida sem resposta há «dias» ou mais. Devolve null se não houver nenhuma.
  function precisaLembrete(despesas, hoje, dias) {
    dias = (typeof dias === 'number' && dias > 0) ? dias : 5;
    var em = (despesas || []).filter(function (d) { return d.estado === 'enviada' && d.enviada_em; });
    if (!em.length) return null;
    var silencio = Math.min.apply(null, em.map(function (d) { return diasEntre(referenciaSilencio(d), hoje); }));
    return silencio >= dias ? { ids: em.map(function (d) { return d.id; }), dias: silencio } : null;
  }

  // O lembrete: «Já fez o pagamento? Basta responder sim ou não.»
  function lembrete(imovel, despesas, opcoes) {
    opcoes = opcoes || {};
    imovel = imovel || {};
    var lista = (despesas || []).filter(function (d) { return d.estado === 'enviada' && typeof d.valor === 'number'; });
    var inq = imovel.inquilino || {}, nomeImovel = imovel.nome || imovel.ref || 'o imóvel';
    var total = lista.reduce(function (s, d) { return s + d.valor; }, 0);
    var enviadas = lista.map(function (d) { return (d.enviada_em || '').slice(0, 10); }).filter(Boolean).sort();
    var assinatura = (imovel.mensagem && imovel.mensagem.assinatura) || opcoes.assinatura || '';
    var saudacao = 'Olá' + (inq.nome ? ' ' + inq.nome : '') + ',';
    var intro = 'Enviámos' + (enviadas.length ? ' a ' + U.formatarData(enviadas[0]) : '') + ' as despesas do apartamento ' + nomeImovel +
      ', no total de ' + U.formatarValor(total) + ':';
    var itens = lista.map(function (d) { return nomeDespesa(d) + ' — ' + U.formatarValor(d.valor); });
    var pergunta = 'Já fez o pagamento? Basta responder «sim» ou «não» (se já pagou e puder, envie o comprovativo).' +
      (opcoes.emailRespostas ? ' Também pode responder para ' + opcoes.emailRespostas + '.' : '');
    var fecho = 'Obrigado' + (assinatura ? ',\n' + assinatura : '.');
    var texto = [saudacao, '', intro].concat(itens.map(function (i) { return '• ' + i; })).concat(['', pergunta, '', fecho]).join('\n');
    var whatsapp = [saudacao, intro].concat(itens.map(function (i) { return '• ' + i; })).concat(['', '*' + pergunta.split('?')[0] + '?*' + pergunta.slice(pergunta.indexOf('?') + 1), '', fecho]).join('\n');
    return { vazia: !lista.length, ids: lista.map(function (d) { return d.id; }), total: total,
      assunto: 'Despesas — ' + nomeImovel + ': já fez o pagamento?', texto: texto, whatsapp: whatsapp };
  }

  // Ligações que abrem o email e o WhatsApp já preenchidos (a pessoa revê e envia). O CC leva a caixa das
  // confirmações: se o inquilino responder a todos, a resposta chega à aplicação.
  function ligacaoEmail(email, assunto, corpo, cc) {
    var e = function (x) { return encodeURIComponent(x || '').replace(/%40/g, '@'); };
    return 'mailto:' + e(email) + '?' + (cc ? 'cc=' + e(cc) + '&' : '') + 'subject=' + encodeURIComponent(assunto) + '&body=' + encodeURIComponent(corpo);
  }
  function numeroWhatsapp(numero) {
    var d = String(numero || '').replace(/[^\d]/g, '').replace(/^00/, '');
    if (/^9\d{8}$/.test(d)) d = '351' + d; // telemóvel português sem indicativo
    return d;
  }
  function ligacaoWhatsapp(numero, texto) {
    var n = numeroWhatsapp(numero);
    return 'https://wa.me/' + n + '?text=' + encodeURIComponent(texto);
  }

  return { gerar: gerar, selecionar: selecionar, formatarPeriodo: formatarPeriodo, nomeDespesa: nomeDespesa,
    ligacaoEmail: ligacaoEmail, formatarTelefone: formatarTelefone, linhaPagamento: linhaPagamento,
    pedidoConfirmacao: pedidoConfirmacao, precisaLembrete: precisaLembrete, lembrete: lembrete, diasEntre: diasEntre, ligacaoWhatsapp: ligacaoWhatsapp, numeroWhatsapp: numeroWhatsapp, NOME_TIPO: NOME_TIPO, NOTA_DIVIDA: NOTA_DIVIDA };
})();
