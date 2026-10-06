/* Despesas — a página. Desenha as vistas (Painel, Faturas, um separador por imóvel, Acessos, Verificação), fala
   com a API (index.php?a=…) e usa o motor (Despesas.pdf, .regras, .tabela) para ler as faturas novas no browser.
   Sem frameworks e sem código em linha no HTML (a CSP não deixa): os botões têm data-acao e um só ouvinte. */
(function () {
  'use strict';
  var U = Despesas.util, T = Despesas.tabela, E = U.escaparHtml;
  var S = { csrf: '', sessao: null, dados: null, regras: null, aLer: false, mensagens: {}, modo: {}, verificacao: null, lembretes: {}, carregados: {} };
  var NOME_ESTADO = { nova: 'nova', enviada: 'em dívida', paga: 'paga', anulada: 'anulada', por_ler: 'por ler', lida: 'lida',
    por_confirmar: 'por confirmar', por_identificar: 'por identificar', ignorada: 'ignorada' };
  var $app, $menu, $quem;

  // ── Comunicação ──────────────────────────────────────────────────────────────────────────
  function api(acao, dados, extra) {
    var o = { method: dados === undefined ? 'GET' : 'POST', headers: {}, credentials: 'same-origin' };
    if (dados !== undefined) {
      o.headers['Content-Type'] = 'application/json';
      o.headers['X-CSRF'] = S.csrf;
      o.body = JSON.stringify(dados);
    }
    return fetch('index.php?a=' + encodeURIComponent(acao) + (extra || ''), o).then(function (r) {
      return r.json().catch(function () { return { erro: 'Resposta inválida do servidor (' + r.status + ').' }; }).then(function (j) {
        if (!r.ok || j.erro) {
          var e = new Error(j.erro || ('Erro ' + r.status));
          e.status = r.status;
          throw e;
        }
        return j;
      });
    });
  }

  var temporizador = null;
  function avisar(msg, mau, fixo) {
    var el = document.getElementById('aviso');
    el.textContent = msg;
    el.className = 'aviso ver' + (mau ? ' mau' : '');
    clearTimeout(temporizador);
    if (!fixo) temporizador = setTimeout(function () { el.className = 'aviso'; }, mau ? 7000 : 3500);
  }
  function falhou(e) {
    if (e && e.status === 401) { S.dados = null; vistaEntrar(); return; }
    avisar(e && e.message ? e.message : String(e), true);
  }

  // ── Pequenos desenhos ────────────────────────────────────────────────────────────────────
  function etiqueta(estado) { return '<span class="etiqueta e-' + E(estado) + '">' + E(NOME_ESTADO[estado] || estado) + '</span>'; }
  function quando(iso) {
    if (!iso) return '—';
    var m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso);
    return m ? m[3] + '/' + m[2] + '/' + m[1] + (m[4] ? ' ' + m[4] + ':' + m[5] : '') : E(iso);
  }
  function imovelDe(ref) {
    var l = (S.dados && S.dados.imoveis) || [];
    for (var i = 0; i < l.length; i++) if (l[i].ref === ref) return l[i];
    return null;
  }
  function faturaDe(id) {
    var l = (S.dados && S.dados.faturas) || [];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i];
    return null;
  }
  function textoPagamento(p) {
    if (!p || !p.metodo) return '—';
    if (p.metodo === 'debito_direto') return 'Débito direto';
    if (p.metodo === 'multibanco') return 'Multibanco: entidade ' + (p.entidade || '?') + ', referência ' + (p.referencia || '?');
    if (p.metodo === 'transferencia') return 'Transferência: IBAN ' + (p.iban || '?');
    return p.metodo;
  }
  function ligacaoPdf(id, descarregar) { return 'index.php?a=pdf&id=' + encodeURIComponent(id) + (descarregar ? '&descarregar=1' : ''); }
  function ligacaoComprovativo(id) { return 'index.php?a=comprovativo&id=' + encodeURIComponent(id); }
  var ORIGEM_PAGA = { inquilino: 'o inquilino confirmou', proprietario: 'o proprietário recebeu', admin: 'registada pelo administrador' };
  function hoje() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function despesasDe(ref) { return S.dados.despesas.filter(function (d) { return d.imovel === ref; }); }
  function respostasPorVer(ref) {
    return (S.dados.respostas || []).filter(function (r) { return r.estado === 'por_ver' && (!ref || r.imovel === ref); });
  }
  function comprovativosDe(ref) { return (S.dados.comprovativos || []).filter(function (c) { return c.imovel === ref; }); }
  function listaComprovativos(ids) {
    return (ids || []).map(function (id) {
      var c = (S.dados.comprovativos || []).filter(function (x) { return x.id === id; })[0];
      return c ? '<a class="ligacao" href="' + ligacaoComprovativo(c.id) + '" target="_blank" rel="noopener">' + E(c.nome || c.ficheiro) + '</a>' : '';
    }).filter(Boolean).join(' · ');
  }
  function vazio(titulo, texto) { return '<div class="vazio"><strong>' + E(titulo) + '</strong>' + E(texto || '') + '</div>'; }
  function admin() { return S.dados && S.dados.utilizador && S.dados.utilizador.papel === 'admin'; }

  // ── Arranque e navegação ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    $app = document.getElementById('app');
    $menu = document.getElementById('menu');
    $quem = document.getElementById('quem');
    document.addEventListener('click', aoClicar);
    document.addEventListener('submit', aoSubmeter);
    window.addEventListener('hashchange', desenhar);
    api('sessao').then(function (s) {
      S.csrf = s.csrf;
      S.sessao = s;
      if (!s.instalado) return vistaInstalar();
      if (!s.utilizador) return vistaEntrar();
      return carregar();
    }).catch(function (e) {
      $app.innerHTML = '<div class="cartao erro entrada"><span class="faixa vermelha">Não arrancou</span><p>' + E(e.message) + '</p></div>';
    });
  });

  function carregar() {
    var regras = S.regras ? Promise.resolve(S.regras) : fetch('motor/fornecedores.json?v=' + encodeURIComponent(S.sessao.versao), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); });
    return Promise.all([regras, api('estado')]).then(function (r) {
      S.regras = r[0];
      S.dados = r[1];
      desenhar();
      if (admin()) lerPendentes();
    }).catch(falhou);
  }

  function recarregar() {
    return api('estado').then(function (d) { S.dados = d; desenhar(); }).catch(falhou);
  }

  function vistaAtual() {
    var h = decodeURIComponent((location.hash || '').replace(/^#/, ''));
    return h || 'painel';
  }

  function desenhar() {
    if (!S.dados) return;
    var vista = vistaAtual(), adm = admin();
    var itens = [{ v: 'painel', t: adm ? 'Painel' : 'Os meus imóveis' }];
    if (adm) {
      var pend = S.dados.faturas.filter(function (f) { return f.estado === 'por_identificar' || f.estado === 'por_confirmar' || f.estado === 'por_ler'; }).length;
      itens.push({ v: 'faturas', t: 'Faturas', n: pend, alerta: pend > 0 });
    }
    S.dados.imoveis.forEach(function (im) {
      var novas = S.dados.despesas.filter(function (d) { return d.imovel === im.ref && (adm ? d.estado === 'nova' : d.estado === 'enviada'); }).length;
      itens.push({ v: 'imovel/' + im.ref, t: im.nome, n: novas });
    });
    if (adm) { itens.push({ v: 'acessos', t: 'Acessos' }); itens.push({ v: 'verificacao', t: 'Verificação' }); }
    $menu.innerHTML = itens.map(function (i) {
      return '<button type="button" class="separador' + (i.v === vista ? ' ativo' : '') + '" data-acao="ir" data-vista="' + E(i.v) + '">' + E(i.t) +
        (i.n ? ' <span class="contador' + (i.alerta ? ' alerta' : '') + '">' + i.n + '</span>' : '') + '</button>';
    }).join('');
    var u = S.dados.utilizador;
    $quem.innerHTML = '<span>' + E(u.nome) + '</span><button type="button" class="botao pequeno" data-acao="sair">Sair</button>';
    S.mensagens = {};
    S.lembretes = {};
    if (vista === 'faturas' && adm) $app.innerHTML = vistaFaturas();
    else if (vista.indexOf('imovel/') === 0 && imovelDe(vista.slice(7))) $app.innerHTML = adm ? vistaImovelAdmin(imovelDe(vista.slice(7))) : vistaImovelDono(imovelDe(vista.slice(7)), true);
    else if (vista === 'acessos' && adm) $app.innerHTML = vistaAcessos();
    else if (vista === 'verificacao' && adm) $app.innerHTML = vistaVerificacao();
    else $app.innerHTML = adm ? vistaPainelAdmin() : vistaPainelDono();
  }

  // ── Entrar e instalar ────────────────────────────────────────────────────────────────────
  function vistaEntrar() {
    $menu.innerHTML = '';
    $quem.innerHTML = '';
    $app.innerHTML = '<form class="cartao entrada" data-form="entrar"><span class="faixa">Entrar</span>' +
      '<div class="campos"><label class="campo largo">Email<input name="email" type="email" autocomplete="username" required></label>' +
      '<label class="campo largo">Password<input name="senha" type="password" autocomplete="current-password" required></label></div>' +
      '<button class="botao primario" type="submit">Entrar</button>' +
      '<p class="mudo pequeno" style="margin-top:12px">A password é dada pelo administrador.</p></form>';
  }

  function vistaInstalar() {
    $menu.innerHTML = '';
    $app.innerHTML = '<form class="cartao entrada" data-form="instalar"><span class="faixa">Primeira entrada</span>' +
      '<p>Escolhe a password do administrador. O código de instalação está em <code>dados/config.php</code>.</p>' +
      '<div class="campos"><label class="campo largo">Código de instalação<input name="codigo" type="password" required></label>' +
      '<label class="campo largo">Password nova (10+ caracteres)<input name="senha" type="password" autocomplete="new-password" minlength="10" required></label>' +
      '<label class="campo largo">Repetir<input name="senha2" type="password" autocomplete="new-password" minlength="10" required></label></div>' +
      '<button class="botao primario" type="submit">Guardar e entrar</button></form>';
  }

  // ── Administrador: Painel ────────────────────────────────────────────────────────────────
  function soma(lista) { return lista.reduce(function (s, d) { return s + (d.valor || 0); }, 0); }

  function vistaPainelAdmin() {
    var D = S.dados, f = D.faturas, d = D.despesas;
    var porId = f.filter(function (x) { return x.estado === 'por_identificar'; }).length;
    var porConf = f.filter(function (x) { return x.estado === 'por_confirmar'; }).length;
    var novas = d.filter(function (x) { return x.estado === 'nova'; });
    var divida = d.filter(function (x) { return x.estado === 'enviada'; });
    var c = D.caixa || {};
    var h = '<h1>Painel</h1><div class="metricas">' +
      metrica(porId, 'Faturas por identificar', porId ? 'mau' : 'bom') +
      metrica(porConf, 'Faturas por confirmar', porConf ? 'atencao' : 'bom') +
      metrica(novas.length, 'Despesas por enviar · ' + U.formatarValor(soma(novas)), novas.length ? 'atencao' : 'bom') +
      metrica(divida.length, 'Em dívida · ' + U.formatarValor(soma(divida)), divida.length ? 'mau' : 'bom') + '</div>';
    h += '<div class="grelha"><section class="cartao"><span class="faixa">Caixa de correio</span><dl class="dados">' +
      '<dt>Conta</dt><dd>' + E(c.conta || '—') + '</dd><dt>Última leitura</dt><dd>' + quando(c.ultima_leitura) + '</dd>' +
      '<dt>Remetentes extra</dt><dd>' + E((D.remetentes_administrador || []).join(', ') || '—') + '</dd></dl>' +
      (c.ultimo_erro ? '<p class="caixa-erro">' + E(c.ultimo_erro.erro) + ' <span class="pequeno">(' + quando(c.ultimo_erro.quando) + ')</span></p>' : '') +
      '<div class="linha"><button class="botao primario" type="button" data-acao="ler-caixa">Ler caixa agora</button>' +
      '<span class="mudo pequeno">Só leitura: não marca nada como lido.</span></div>' +
      ((c.sem_pdf || []).length ? '<ul class="avisos" style="margin-top:12px">' + c.sem_pdf.slice(-5).map(function (n) { return '<li>' + E(n.nota) + '</li>'; }).join('') + '</ul>' : '') +
      '</section>';
    var porVer = respostasPorVer(), aLembrar = D.imoveis.filter(function (im) { return T.precisaLembrete(despesasDe(im.ref), hoje(), D.lembrete_dias); });
    if (porVer.length || aLembrar.length) {
      h += '<section class="cartao atencao"><span class="faixa">Pagamentos a confirmar</span><ul>' +
        porVer.map(function (r) {
          var im = imovelDe(r.imovel);
          return '<li><b>' + E(im ? im.inquilino.nome || im.nome : r.imovel) + '</b> respondeu' + (r.comprovativos.length ? ' com comprovativo' : '') +
            ' (' + quando(r.recebido_em) + '): <button class="ligacao" type="button" data-acao="ir" data-vista="imovel/' + E(r.imovel) + '">ver e registar</button></li>';
        }).join('') +
        aLembrar.map(function (im) {
          var l = T.precisaLembrete(despesasDe(im.ref), hoje(), D.lembrete_dias);
          return '<li><b>' + E(im.inquilino.nome || im.nome) + '</b> não responde há ' + l.dias + ' dias: <button class="ligacao" type="button" data-acao="ir" data-vista="imovel/' +
            E(im.ref) + '">preparar lembrete</button></li>';
        }).join('') + '</ul></section>';
    }
    h += '<section class="cartao"><span class="faixa">Imóveis</span>';
    if (!D.imoveis.length) h += vazio('Ainda não há imóveis.', 'Cada imóvel é uma pasta em dados/imoveis.');
    else {
      h += '<div class="tabela-envolta"><table class="lista"><thead><tr><th>Imóvel</th><th>Inquilino</th><th class="num">Por enviar</th><th class="num">Em dívida</th></tr></thead><tbody>';
      D.imoveis.forEach(function (im) {
        var n = d.filter(function (x) { return x.imovel === im.ref && x.estado === 'nova'; });
        var e = d.filter(function (x) { return x.imovel === im.ref && x.estado === 'enviada'; });
        h += '<tr><td><button class="ligacao" type="button" data-acao="ir" data-vista="imovel/' + E(im.ref) + '">' + E(im.nome) + '</button></td><td>' + E(im.inquilino.nome || '—') +
          '</td><td class="num">' + (n.length ? U.formatarValor(soma(n)) : '—') + '</td><td class="num">' + (e.length ? U.formatarValor(soma(e)) : '—') + '</td></tr>';
      });
      h += '</tbody></table></div>';
    }
    h += '</section></div>';
    return h;
  }

  function metrica(valor, rotulo, classe) {
    return '<div class="metrica ' + classe + '"><span class="valor">' + E(valor) + '</span><span class="rotulo">' + E(rotulo) + '</span></div>';
  }

  // ── Administrador: Faturas ───────────────────────────────────────────────────────────────
  function vistaFaturas() {
    var f = S.dados.faturas.slice().sort(function (a, b) { return (b.recebido_em || '').localeCompare(a.recebido_em || ''); });
    var grupo = function (e) { return f.filter(function (x) { return x.estado === e; }); };
    var h = '<h1>Faturas</h1><div class="linha" style="margin-bottom:18px"><button class="botao primario" type="button" data-acao="ler-caixa">Ler caixa agora</button>' +
      (S.aLer ? '<span class="mudo">A ler as faturas novas…</span>' : '') + '</div>';
    var porLer = grupo('por_ler');
    if (porLer.length) h += '<section class="cartao"><span class="faixa">Por ler</span><p>' + porLer.length + ' PDF(s) à espera de ser lidos' + (S.aLer ? '…' : ' (recarregar a página).') + '</p></section>';
    grupo('por_identificar').forEach(function (x) { h += cartaoFatura(x); });
    grupo('por_confirmar').forEach(function (x) { h += cartaoFatura(x); });
    var lidas = grupo('lida');
    h += '<section class="cartao"><span class="faixa">Lidas</span>';
    if (!lidas.length) h += vazio('Ainda nenhuma.', 'As faturas lidas e confirmadas aparecem aqui.');
    else {
      h += '<div class="tabela-envolta"><table class="lista"><thead><tr><th>Recebida</th><th>Imóvel</th><th>Despesa</th><th>Período</th><th class="num">Total</th><th></th></tr></thead><tbody>';
      lidas.slice(0, 60).forEach(function (x) {
        var im = imovelDe(x.imovel);
        h += '<tr><td>' + quando(x.recebido_em) + '</td><td>' + E(im ? im.nome : x.imovel) + '</td><td>' + E(T.nomeDespesa(x)) + '</td><td>' + E(T.formatarPeriodo(x.periodo)) +
          '</td><td class="num">' + E(U.formatarValor(x.total)) + '</td><td class="acoes"><a class="ligacao" href="' + ligacaoPdf(x.id) + '" target="_blank" rel="noopener">PDF</a>' +
          '<button class="ligacao" type="button" data-acao="reabrir" data-id="' + E(x.id) + '">Reabrir</button></td></tr>';
      });
      h += '</tbody></table></div>';
    }
    h += '</section>';
    var ign = grupo('ignorada');
    if (ign.length) {
      h += '<section class="cartao"><span class="faixa cinza">Ignoradas</span><ul class="pequeno mudo">' + ign.slice(0, 20).map(function (x) {
        return '<li>' + quando(x.recebido_em) + ' · ' + E(x.ficheiro) + ' · ' + E(x.remetente) + '</li>';
      }).join('') + '</ul></section>';
    }
    if (!f.length) h += vazio('Ainda não chegou nenhuma fatura.', 'Carrega em «Ler caixa agora».');
    return h + datalistFornecedores();
  }

  function datalistFornecedores() {
    var nomes = ((S.regras && S.regras.fornecedores) || []).map(function (f) { return f.nome; });
    return '<datalist id="lista-fornecedores">' + nomes.map(function (n) { return '<option value="' + E(n) + '">'; }).join('') + '</datalist>';
  }

  function cartaoFatura(f) {
    var porId = f.estado === 'por_identificar';
    var opcoesImovel = '<option value="">—</option>' + S.dados.imoveis.map(function (im) {
      return '<option value="' + E(im.ref) + '"' + (im.ref === f.imovel ? ' selected' : '') + '>' + E(im.nome) + '</option>';
    }).join('');
    var opcoesTipo = '<option value="">—</option>' + Object.keys(T.NOME_TIPO).map(function (t) {
      return '<option value="' + t + '"' + (t === f.tipo ? ' selected' : '') + '>' + E(T.NOME_TIPO[t]) + '</option>';
    }).join('');
    var per = f.periodo || {};
    var h = '<article class="cartao ' + (porId ? 'erro' : 'atencao') + '" data-fatura="' + E(f.id) + '">' +
      '<span class="faixa' + (porId ? ' vermelha' : '') + '">' + (porId ? 'Por identificar' : 'Por confirmar') + '</span>' +
      '<div class="linha espalhada"><h3>' + E(f.ficheiro || 'fatura.pdf') + '</h3><span class="mudo pequeno">' + quando(f.recebido_em) + '</span></div>' +
      '<p class="mudo pequeno">De ' + E(f.remetente || '?') + (f.assunto ? ' · «' + E(f.assunto) + '»' : '') + '</p>';
    if ((f.avisos || []).length) h += '<ul class="avisos' + (porId ? ' mau' : '') + '">' + f.avisos.map(function (a) { return '<li>' + E(a) + '</li>'; }).join('') + '</ul>';
    h += '<form data-form="fatura" data-id="' + E(f.id) + '"><div class="campos">' +
      '<label class="campo">Imóvel<select name="imovel" required>' + opcoesImovel + '</select></label>' +
      '<label class="campo">Tipo<select name="tipo" required>' + opcoesTipo + '</select></label>' +
      '<label class="campo">Fornecedor<input name="fornecedor" list="lista-fornecedores" value="' + E(f.fornecedor || '') + '" required></label>' +
      '<label class="campo">Total a pagar (€)<input name="total" inputmode="decimal" value="' + (f.total ? E(U.formatarValor(f.total).replace(' €', '').replace(/ /g, '')) : '') + '" placeholder="0,00" required></label>' +
      '<label class="campo">Período: de<input type="date" name="de" value="' + E(per.de || '') + '"></label>' +
      '<label class="campo">até<input type="date" name="ate" value="' + E(per.ate || '') + '"></label>' +
      '<label class="campo">Pagar até<input type="date" name="data_limite" value="' + E(f.data_limite || '') + '"></label></div>';
    if (per.mes) h += '<p class="pequeno mudo">Período na fatura: ' + E(U.formatarData(per.mes)) + ' (fica assim se não escreveres datas).</p>';
    if ((f.valores || []).length) {
      h += '<div class="campo largo">Valores no PDF — clicar no total certo:<div class="fichas">' + f.valores.slice(0, 40).map(function (v) {
        return '<button type="button" class="ficha' + (v.cent === f.total ? ' escolhida' : '') + '" data-acao="escolher-total" data-cent="' + v.cent + '">' +
          E(U.formatarValor(v.cent)) + (v.contexto ? '<small>' + E(v.contexto) + '</small>' : '') + '</button>';
      }).join('') + '</div></div>';
    }
    if ((f.datas || []).length) {
      h += '<div class="campo largo">Datas no PDF — clicar na data-limite:<div class="fichas">' + f.datas.map(function (d) {
        return '<button type="button" class="ficha' + (d === f.data_limite ? ' escolhida' : '') + '" data-acao="escolher-data" data-iso="' + E(d) + '">' + E(U.formatarData(d)) + '</button>';
      }).join('') + '</div></div>';
    }
    if (f.sem_texto) h += '<p class="pequeno">O PDF não tem texto (digitalizado ou protegido): abrir o PDF e escrever os valores à mão.</p>';
    h += '<p class="pequeno mudo">Pagamento ao fornecedor: ' + E(textoPagamento(f.pagamento)) + '</p>' +
      '<div class="linha"><button class="botao primario" type="submit">Guardar</button>' +
      '<a class="botao" href="' + ligacaoPdf(f.id) + '" target="_blank" rel="noopener">Abrir PDF</a>' +
      '<a class="ligacao" href="' + ligacaoPdf(f.id, true) + '">Descarregar (para trazer ao Claude)</a>' +
      '<button class="ligacao" type="button" data-acao="reler" data-id="' + E(f.id) + '">Voltar a ler</button>' +
      '<button class="ligacao" type="button" data-acao="fatura-comprovativo" data-id="' + E(f.id) + '">É um comprovativo de pagamento</button>' +
      '<button class="ligacao perigo" type="button" data-acao="ignorar" data-id="' + E(f.id) + '">Ignorar (não é despesa)</button></div></form></article>';
    return h;
  }

  // ── Imóvel (administrador) ───────────────────────────────────────────────────────────────
  function vistaImovelAdmin(im) {
    var desp = S.dados.despesas.filter(function (d) { return d.imovel === im.ref; });
    var msg = T.gerar(im, desp, { assinatura: S.dados.assinatura, emailRespostas: S.dados.email_respostas });
    S.mensagens[im.ref] = msg;
    var modo = S.modo[im.ref] || 'email';
    var inq = im.inquilino || {}, prop = im.proprietario || {};
    var partilhas = Object.keys(im.partilha || {}).filter(function (t) { return im.partilha[t] !== 100; })
      .map(function (t) { return T.NOME_TIPO[t] + ' ' + im.partilha[t] + '%'; });
    var h = '<h1>' + E(im.nome) + '</h1><div class="grelha">' +
      '<section class="cartao"><span class="faixa">Proprietário</span><dl class="dados"><dt>Nome</dt><dd>' + E(prop.nome || '—') + '</dd>' +
      '<dt>Email</dt><dd>' + E(prop.email || '—') + '</dd><dt>IBAN</dt><dd>' + E(prop.iban || '—') + '</dd><dt>MB WAY</dt><dd>' + E(prop.mbway ? T.formatarTelefone(prop.mbway) : '—') + '</dd></dl></section>' +
      '<section class="cartao"><span class="faixa">Inquilino</span><dl class="dados"><dt>Nome</dt><dd>' + E(inq.nome || '—') + '</dd>' +
      '<dt>Email</dt><dd>' + E(inq.email || '—') + '</dd><dt>WhatsApp</dt><dd>' + E(inq.whatsapp || '—') + '</dd>' +
      '<dt>Paga</dt><dd>' + E(partilhas.length ? 'tudo a 100%, menos ' + partilhas.join(', ') : '100% de cada fatura') + '</dd></dl></section></div>';

    h += '<section class="cartao"><span class="faixa">Mensagem para ' + E(inq.nome || 'o inquilino') + '</span>';
    if (msg.vazia) h += vazio('Tudo em dia.', 'Não há despesas novas nem em dívida.');
    else {
      if (msg.avisos.length) h += '<ul class="avisos">' + msg.avisos.map(function (a) { return '<li>' + E(a) + '</li>'; }).join('') + '</ul>';
      h += '<div class="linha espalhada"><div class="separadores-mini" role="tablist">' +
        [['email', 'Email (tabela)'], ['texto', 'Texto simples'], ['whatsapp', 'WhatsApp']].map(function (m) {
          return '<button type="button" class="' + (m[0] === modo ? 'ativo' : '') + '" data-acao="modo" data-ref="' + E(im.ref) + '" data-modo="' + m[0] + '">' + m[1] + '</button>';
        }).join('') + '</div><span class="mudo pequeno">Assunto: ' + E(msg.assunto) + '</span></div>';
      h += modo === 'email' ? '<div class="previa">' + msg.html + '</div>' : '<div class="previa-texto">' + E(modo === 'texto' ? msg.texto : msg.whatsapp) + '</div>';
      h += '<div class="linha"><button class="botao" type="button" data-acao="copiar" data-ref="' + E(im.ref) + '">' + (modo === 'email' ? 'Copiar tabela' : 'Copiar texto') + '</button>';
      if (modo !== 'whatsapp' && inq.email) {
        h += '<a class="botao" href="' + E(T.ligacaoEmail(inq.email, msg.assunto, modo === 'texto' ? msg.texto : '', S.dados.email_respostas)) + '">Abrir email</a>';
      }
      if (inq.whatsapp) h += '<a class="botao" href="' + E(T.ligacaoWhatsapp(inq.whatsapp, msg.whatsapp)) + '" target="_blank" rel="noopener">Abrir WhatsApp</a>';
      h += '<button class="botao primario" type="button" data-acao="marcar-enviadas" data-ref="' + E(im.ref) + '">Marcar ' + msg.ids.length + ' como enviada(s)</button></div>' +
        '<p class="mudo pequeno" style="margin-top:10px">A aplicação não envia nada: copia, cola no email (ou abre o WhatsApp), envia tu e depois marca como enviadas.' +
        (modo === 'email' ? ' No email: «Abrir email» traz o assunto; cola a tabela no corpo.' : '') + '</p>';
    }
    h += '</section>';
    h += cartaoConfirmacao(im, desp);
    h += '<section class="cartao"><span class="faixa">Despesas</span>' + tabelaDespesas(desp, true) + '</section>';
    h += cartaoComprovativos(im, true);
    return h;
  }

  // A confirmação do pagamento: as respostas por ver, o registo à mão (WhatsApp, telefone) e o lembrete.
  function cartaoConfirmacao(im, desp) {
    var emDivida = desp.filter(function (d) { return d.estado === 'enviada'; });
    var porVer = respostasPorVer(im.ref), inq = im.inquilino || {};
    if (!emDivida.length && !porVer.length) return '';
    var soma = U.formatarValor(emDivida.reduce(function (s, d) { return s + d.valor; }, 0));
    var h = '<section class="cartao atencao"><span class="faixa">Confirmação do pagamento</span>';
    if (emDivida.length) h += '<p>Em dívida: <b>' + emDivida.length + ' despesa(s), ' + E(soma) + '</b>. Quando ' + E(inq.nome || 'o inquilino') +
      ' confirmar que pagou, regista aqui (fica «paga — o inquilino confirmou»; confirmar se o dinheiro entrou fica para o proprietário).</p>';
    porVer.forEach(function (r) {
      var sug = r.sugestao === 'sim' ? 'parece dizer que pagou' : (r.sugestao === 'nao' ? 'parece dizer que ainda não pagou' : 'não é claro');
      h += '<div class="resposta"><p class="mudo pequeno">' + (r.origem === 'email' ? 'Email de ' + E(r.de) : 'Documento reencaminhado') + ' · ' + quando(r.recebido_em) +
        (r.assunto ? ' · «' + E(r.assunto) + '»' : '') + ' · <b>' + sug + '</b></p>' +
        (r.texto ? '<blockquote>' + E(r.texto) + '</blockquote>' : '') +
        (r.comprovativos.length ? '<p class="pequeno">Comprovativo: ' + listaComprovativos(r.comprovativos) + '</p>' : '') +
        '<div class="linha">' + (emDivida.length ? '<button class="botao primario pequeno" type="button" data-acao="responder" data-valor="sim" data-ref="' + E(im.ref) + '" data-resposta="' + E(r.id) + '">Pagou (' + emDivida.length + ', ' + E(soma) + ')</button>' +
        '<button class="botao pequeno" type="button" data-acao="responder" data-valor="nao" data-ref="' + E(im.ref) + '" data-resposta="' + E(r.id) + '">Ainda não pagou</button>' : '') +
        '<button class="ligacao" type="button" data-acao="resposta-ignorar" data-id="' + E(r.id) + '">Não é sobre o pagamento</button></div></div>';
    });
    if (emDivida.length) {
      var pend = S.carregados[im.ref] || [];
      h += '<div class="resposta"><p class="mudo pequeno">Resposta por WhatsApp ou telefone:</p><div class="linha">' +
        '<button class="botao primario pequeno" type="button" data-acao="responder" data-valor="sim" data-ref="' + E(im.ref) + '">Pagou</button>' +
        '<button class="botao pequeno" type="button" data-acao="responder" data-valor="nao" data-ref="' + E(im.ref) + '">Ainda não pagou</button></div>' +
        '<form class="linha" data-form="comprovativo" data-ref="' + E(im.ref) + '" style="margin-top:10px"><input type="file" name="ficheiro" accept="application/pdf,image/*" required style="max-width:320px">' +
        '<button class="botao pequeno" type="submit">Juntar comprovativo</button>' +
        (pend.length ? '<span class="pequeno">' + pend.length + ' comprovativo(s) a juntar ao «Pagou»</span>' : '') + '</form></div>';
      var l = T.precisaLembrete(desp, hoje(), S.dados.lembrete_dias);
      if (l) {
        var lem = T.lembrete(im, desp, { assinatura: S.dados.assinatura, emailRespostas: S.dados.email_respostas });
        S.lembretes[im.ref] = lem;
        h += '<div class="resposta"><p><b>Sem resposta há ' + l.dias + ' dias.</b> Lembrete pronto (pergunta só «sim» ou «não»):</p>' +
          '<div class="previa-texto">' + E(lem.whatsapp) + '</div><div class="linha">' +
          '<button class="botao pequeno" type="button" data-acao="copiar-lembrete" data-ref="' + E(im.ref) + '">Copiar</button>' +
          (inq.email ? '<a class="botao pequeno" href="' + E(T.ligacaoEmail(inq.email, lem.assunto, lem.texto, S.dados.email_respostas)) + '">Abrir email</a>' : '') +
          (inq.whatsapp ? '<a class="botao pequeno" href="' + E(T.ligacaoWhatsapp(inq.whatsapp, lem.whatsapp)) + '" target="_blank" rel="noopener">Abrir WhatsApp</a>' : '') +
          '<button class="botao primario pequeno" type="button" data-acao="lembrete-enviado" data-ref="' + E(im.ref) + '">Marcar lembrete como enviado</button></div></div>';
      }
    }
    return h + '</section>';
  }

  function cartaoComprovativos(im, adm) {
    var l = comprovativosDe(im.ref).slice().sort(function (a, b) { return (b.recebido_em || '').localeCompare(a.recebido_em || ''); });
    if (!l.length) return adm ? '' : '';
    return '<section class="cartao"><span class="faixa cinza">Comprovativos de pagamento</span><ul class="pequeno">' + l.map(function (c) {
      return '<li>' + quando(c.recebido_em).slice(0, 10) + ' · <a class="ligacao" href="' + ligacaoComprovativo(c.id) + '" target="_blank" rel="noopener">' + E(c.nome || c.ficheiro) + '</a>' +
        ' <span class="mudo">(' + E({ email: 'por email', carregado: 'carregado na página', reencaminhado: 'reencaminhado' }[c.origem] || c.origem) + ')</span></li>';
    }).join('') + '</ul></section>';
  }

  function tabelaDespesas(desp, adm) {
    var limite = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
    var lista = desp.filter(function (d) { return d.estado !== 'anulada' && !(d.estado === 'paga' && (d.paga_em || '') < limite); })
      .sort(function (a, b) { return (b.criada || '').localeCompare(a.criada || ''); });
    if (!lista.length) return vazio('Sem despesas.', adm ? 'Aparecem aqui quando as faturas forem lidas.' : 'Ainda não há despesas para este imóvel.');
    var h = '<div class="tabela-envolta"><table class="lista"><thead><tr><th>Despesa</th><th>Período</th><th>Pagar até</th><th class="num">Valor</th><th>Estado</th>' +
      (adm ? '' : '<th>Pagamento ao fornecedor</th>') + '<th></th></tr></thead><tbody>';
    lista.forEach(function (d) {
      var f = faturaDe(d.fatura);
      var acoes = [];
      if (d.estado === 'nova' || d.estado === 'enviada') acoes.push(botaoDespesa(d.id, 'paga', adm ? 'Paga' : 'Recebi'));
      if (!adm && d.estado === 'paga' && d.paga_origem === 'inquilino') acoes.push('<span class="pequeno mudo">confirme na sua conta se recebeu</span>');
      if (d.estado === 'paga' && (adm || d.paga_por === S.dados.utilizador.email)) acoes.push(botaoDespesa(d.id, 'desfazer', 'Desfazer'));
      if (adm && d.estado === 'enviada') acoes.push(botaoDespesa(d.id, 'desfazer', 'Desfazer envio'));
      if (adm && (d.estado === 'nova' || d.estado === 'enviada')) acoes.push(botaoDespesa(d.id, 'anular', 'Anular', true));
      if (f) acoes.push('<a class="ligacao" href="' + ligacaoPdf(f.id) + '" target="_blank" rel="noopener">PDF</a>');
      var nota = d.estado === 'enviada' ? 'enviada a ' + quando(d.enviada_em).slice(0, 10) + ((d.lembretes || []).length ? ' · ' + d.lembretes.length + ' lembrete(s)' : '') +
          (d.ultima_resposta && d.ultima_resposta.valor === 'nao' ? ' · disse que ainda não pagou' : '')
        : (d.estado === 'paga' ? 'a ' + quando(d.paga_em).slice(0, 10) + (d.paga_origem ? ' · ' + (ORIGEM_PAGA[d.paga_origem] || d.paga_origem) : '') : '');
      if ((d.comprovativos || []).length) acoes.push(listaComprovativos(d.comprovativos));
      h += '<tr><td>' + E(T.nomeDespesa(d)) + '</td><td>' + E(T.formatarPeriodo(d.periodo)) + '</td><td>' + E(U.formatarData(d.data_limite)) + '</td>' +
        '<td class="num">' + E(U.formatarValor(d.valor)) + (d.percentagem !== 100 ? '<br><span class="pequeno mudo">' + E(d.percentagem + '% de ' + U.formatarValor(d.total)) + '</span>' : '') + '</td>' +
        '<td>' + etiqueta(d.estado) + (nota ? '<br><span class="pequeno mudo">' + nota + '</span>' : '') + '</td>' +
        (adm ? '' : '<td class="pequeno">' + E(textoPagamento(f && f.pagamento)) + '</td>') +
        '<td class="acoes">' + acoes.join('') + '</td></tr>';
    });
    return h + '</tbody></table></div>';
  }

  function botaoDespesa(id, op, texto, perigo) {
    return '<button class="' + (op === 'paga' ? 'botao pequeno primario' : 'ligacao' + (perigo ? ' perigo' : '')) + '" type="button" data-acao="despesa" data-op="' + op + '" data-id="' + E(id) + '">' + E(texto) + '</button>';
  }

  // ── Proprietário ─────────────────────────────────────────────────────────────────────────
  function vistaPainelDono() {
    var l = S.dados.imoveis;
    if (!l.length) return '<h1>Os meus imóveis</h1>' + vazio('Sem imóveis.', 'Fale com o administrador.');
    return '<h1>Os meus imóveis</h1>' + l.map(function (im) { return vistaImovelDono(im, false); }).join('');
  }

  function vistaImovelDono(im, sozinho) {
    var desp = S.dados.despesas.filter(function (d) { return d.imovel === im.ref; });
    var divida = desp.filter(function (d) { return d.estado === 'enviada'; });
    return (sozinho ? '<h1>' + E(im.nome) + '</h1>' : '') + '<section class="cartao"><span class="faixa">' + E(im.nome) + '</span>' +
      '<p>' + (divida.length ? 'A aguardar pagamento de ' + E(im.inquilino.nome || 'o inquilino') + ': <b>' + E(U.formatarValor(soma(divida))) + '</b>.' : 'Nada em dívida.') +
      ' Marque «Recebi» quando o inquilino lhe pagar uma despesa.</p>' + tabelaDespesas(desp, false) + '</section>' + cartaoComprovativos(im, false);
  }

  // ── Acessos e verificação ────────────────────────────────────────────────────────────────
  function vistaAcessos() {
    var u = S.dados.utilizadores || [];
    var h = '<h1>Acessos</h1><section class="cartao"><span class="faixa">Quem entra</span>' +
      '<p>Cada pessoa entra com o seu email e a password que lhe deres (10 ou mais caracteres). Os proprietários saem das pastas dos imóveis.</p>' +
      '<div class="tabela-envolta"><table class="lista"><thead><tr><th>Nome</th><th>Email</th><th>Papel</th><th>Password</th><th>Nova password</th></tr></thead><tbody>';
    u.forEach(function (x) {
      h += '<tr><td>' + E(x.nome) + '</td><td>' + E(x.email) + '</td><td>' + (x.papel === 'admin' ? 'administrador' : 'proprietário') + '</td><td>' +
        (x.tem_senha ? '<span class="etiqueta e-paga">definida</span>' : '<span class="etiqueta e-por_identificar">por definir</span>') + '</td>' +
        '<td><form class="linha" data-form="senha" data-email="' + E(x.email) + '"><input name="senha" type="text" minlength="10" autocomplete="off" style="max-width:220px" required>' +
        '<button class="ligacao" type="button" data-acao="gerar-senha">Gerar</button><button class="botao pequeno" type="submit">Definir</button></form></td></tr>';
    });
    h += '</tbody></table></div><p class="mudo pequeno" style="margin-top:10px">Depois de definir, dá a password à pessoa por um canal seguro (pessoalmente ou por telefone).</p></section>';
    var reg = S.dados.registo || [];
    if (reg.length) {
      h += '<section class="cartao"><span class="faixa cinza">Últimas ações</span><ul class="pequeno mudo">' + reg.slice().reverse().map(function (r) {
        return '<li>' + quando(r.quando) + ' · ' + E(r.quem) + ' · ' + E(r.oque) + '</li>';
      }).join('') + '</ul></section>';
    }
    return h;
  }

  function vistaVerificacao() {
    var h = '<h1>Verificação</h1><div class="linha" style="margin-bottom:18px"><button class="botao primario" type="button" data-acao="verificar">Verificar</button>' +
      '<button class="botao" type="button" data-acao="verificar" data-imap="1">Verificar e testar o Gmail</button></div>';
    var v = S.verificacao;
    if (!v) return h + vazio('Ainda não verificado.', 'Verifica o alojamento, os imóveis e corre os testes do PHP.');
    h += '<section class="cartao"><span class="faixa">Alojamento e dados</span><div class="tabela-envolta"><table class="lista"><tbody>' + v.itens.map(function (i) {
      return '<tr><td>' + (i.ok ? '<span class="etiqueta e-paga">ok</span>' : '<span class="etiqueta ' + (i.grave ? 'e-por_identificar">falha' : 'e-enviada">atenção') + '</span>') +
        '</td><td>' + E(i.nome) + '</td><td class="mudo pequeno">' + E(i.detalhe) + '</td></tr>';
    }).join('') + '</tbody></table></div></section>';
    var t = v.testes;
    h += '<section class="cartao' + (t.passaram === t.total ? '' : ' erro') + '"><span class="faixa' + (t.passaram === t.total ? '' : ' vermelha') + '">Testes do PHP: ' + t.passaram + '/' + t.total + '</span><ul class="pequeno">' +
      t.resultados.map(function (r) { return '<li>' + (r.ok ? '✓ ' : '✗ ') + E(r.nome) + (r.ok ? '' : ' — <b>' + E(r.erro) + '</b>') + '</li>'; }).join('') + '</ul></section>';
    return h;
  }

  // ── Ler as faturas novas no browser (o motor JavaScript) ─────────────────────────────────
  function paraServidor(a, p) {
    return {
      fornecedor_id: a.fornecedor ? a.fornecedor.id : null, fornecedor: a.fornecedor ? a.fornecedor.nome : '', tipo: a.tipo, total: a.total,
      periodo: a.periodo, data_limite: a.data_limite, pagamento: a.pagamento, imovel: a.imovel, estado: a.estado,
      avisos: (p.avisos || []).concat(a.avisos || []), valores: a.valores, datas: a.datas, sem_texto: !p.temTexto
    };
  }

  function lerPendentes() {
    if (S.aLer || !S.dados) return;
    var pend = S.dados.faturas.filter(function (f) { return f.estado === 'por_ler'; });
    if (!pend.length) return;
    S.aLer = true;
    var i = 0;
    function proxima() {
      if (i >= pend.length) {
        S.aLer = false;
        avisar(pend.length + ' fatura(s) lida(s).');
        return recarregar();
      }
      var f = pend[i++];
      avisar('A ler a fatura ' + i + ' de ' + pend.length + '…', false, true);
      return fetch(ligacaoPdf(f.id), { credentials: 'same-origin' }).then(function (r) {
        if (!r.ok) throw new Error('não consegui descarregar o PDF (' + r.status + ')');
        return r.arrayBuffer();
      }).then(function (buf) {
        return new Promise(function (ok) { setTimeout(ok, 0); }).then(function () {
          var p = Despesas.pdf.extrair(new Uint8Array(buf));
          var a = Despesas.regras.analisar(p.texto, { regras: S.regras, imoveis: S.dados.imoveis, remetente: f.remetente, assunto: f.assunto });
          return api('resultado', { id: f.id, analise: paraServidor(a, p) });
        });
      }).catch(function (e) {
        return api('resultado', { id: f.id, analise: { estado: 'por_identificar', avisos: ['Não consegui ler o PDF: ' + e.message] } }).catch(function () {});
      }).then(proxima);
    }
    proxima();
  }

  function lerCaixa(botao) {
    if (botao) botao.disabled = true;
    avisar('A ler a caixa de correio…', false, true);
    var novas = 0, voltas = 0, notas = [];
    function volta() {
      return api('ler_caixa', {}).then(function (r) {
        novas += r.novas;
        notas = notas.concat(r.notas || []);
        if (r.ha_mais && ++voltas < 8) return volta();
        avisar(novas ? novas + ' fatura(s) nova(s).' : 'Nada de novo.' + (notas.length ? ' ' + notas[0] : ''));
      });
    }
    volta().then(carregar).catch(falhou).then(function () { if (botao) botao.disabled = false; });
  }

  // ── Copiar ───────────────────────────────────────────────────────────────────────────────
  function copiar(html, texto) {
    if (html && window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
      return navigator.clipboard.write([new window.ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }), 'text/plain': new Blob([texto], { type: 'text/plain' })
      })]);
    }
    if (!html && navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(texto);
    return new Promise(function (ok, falha) {
      var el = document.createElement(html ? 'div' : 'textarea');
      if (html) { el.innerHTML = html; el.setAttribute('contenteditable', 'true'); } else el.value = texto;
      el.style.position = 'fixed';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      if (html) {
        var r = document.createRange(), s = window.getSelection();
        r.selectNodeContents(el);
        s.removeAllRanges();
        s.addRange(r);
      } else el.select();
      var feito = false;
      try { feito = document.execCommand('copy'); } catch (e) { feito = false; }
      document.body.removeChild(el);
      if (feito) ok(); else falha(new Error('O browser não deixou copiar: selecionar e copiar à mão.'));
    });
  }

  function gerarSenha() {
    var a = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789', b = new Uint32Array(15), s = '';
    window.crypto.getRandomValues(b);
    for (var i = 0; i < b.length; i++) s += (i && i % 5 === 0 ? '-' : '') + a[b[i] % a.length];
    return s;
  }

  // ── Eventos ──────────────────────────────────────────────────────────────────────────────
  function aoClicar(ev) {
    var el = ev.target.closest ? ev.target.closest('[data-acao]') : null;
    if (!el) return;
    var acao = el.getAttribute('data-acao'), id = el.getAttribute('data-id'), ref = el.getAttribute('data-ref');
    if (acao === 'ir') { location.hash = el.getAttribute('data-vista'); return; }
    if (acao === 'sair') { api('sair', {}).then(function () { location.hash = ''; location.reload(); }).catch(falhou); return; }
    if (acao === 'ler-caixa') { lerCaixa(el); return; }
    if (acao === 'escolher-total' || acao === 'escolher-data') {
      var form = el.closest('form');
      var campo = form.querySelector(acao === 'escolher-total' ? '[name=total]' : '[name=data_limite]');
      campo.value = acao === 'escolher-total' ? U.formatarValor(+el.getAttribute('data-cent')).replace(' €', '').replace(/ /g, '') : el.getAttribute('data-iso');
      Array.prototype.forEach.call(el.parentNode.querySelectorAll('.ficha'), function (x) { x.classList.toggle('escolhida', x === el); });
      return;
    }
    if (acao === 'reler' || acao === 'ignorar' || acao === 'reabrir') {
      if (acao === 'ignorar' && !confirm('Ignorar esta fatura? Não entra nas despesas e o PDF é apagado do servidor.')) return;
      if (acao === 'reabrir' && !confirm('Reabrir esta fatura? A despesa dela (se ainda não foi enviada) sai e a fatura volta a «por confirmar».')) return;
      api('fatura_' + acao, { id: id }).then(function () { return carregar(); }).catch(falhou);
      return;
    }
    if (acao === 'modo') { S.modo[ref] = el.getAttribute('data-modo'); desenhar(); return; }
    if (acao === 'copiar') {
      var m = S.mensagens[ref], modo = S.modo[ref] || 'email';
      if (!m) return;
      copiar(modo === 'email' ? m.html : '', modo === 'whatsapp' ? m.whatsapp : m.texto)
        .then(function () { avisar(modo === 'email' ? 'Tabela copiada: cola no corpo do email.' : 'Texto copiado.'); }).catch(falhou);
      return;
    }
    if (acao === 'marcar-enviadas') {
      var msg = S.mensagens[ref];
      if (!msg || !msg.ids.length) return;
      if (!confirm('Marcar ' + msg.ids.length + ' despesa(s) como enviada(s) ao inquilino?')) return;
      api('despesas_enviadas', { ids: msg.ids }).then(function () { avisar('Marcadas como enviadas.'); return recarregar(); }).catch(falhou);
      return;
    }
    if (acao === 'despesa') {
      var op = el.getAttribute('data-op');
      var perguntas = { anular: 'Anular esta despesa? Deixa de aparecer ao inquilino.', desfazer: 'Desfazer?' };
      if (perguntas[op] && !confirm(perguntas[op])) return;
      api('despesa_' + op, { id: id }).then(function () { return recarregar(); }).catch(falhou);
      return;
    }
    if (acao === 'responder') {
      var valor = el.getAttribute('data-valor'), ids = despesasDe(ref).filter(function (d) { return d.estado === 'enviada'; }).map(function (d) { return d.id; });
      var pergunta = valor === 'sim' ? 'Registar como pagas ' + ids.length + ' despesa(s) em dívida (o inquilino confirmou)?' : 'Registar que o inquilino disse que ainda não pagou?';
      if (!confirm(pergunta)) return;
      api('resposta_registar', { valor: valor, ids: ids, resposta: el.getAttribute('data-resposta') || '', comprovativos: valor === 'sim' ? (S.carregados[ref] || []) : [] })
        .then(function () { if (valor === 'sim') S.carregados[ref] = []; avisar(valor === 'sim' ? 'Registado: pagas.' : 'Registado: ainda não pagou.'); return recarregar(); }).catch(falhou);
      return;
    }
    if (acao === 'resposta-ignorar') { api('resposta_ignorar', { id: id }).then(recarregar).catch(falhou); return; }
    if (acao === 'copiar-lembrete') {
      var lem = S.lembretes[ref];
      if (lem) copiar('', lem.whatsapp).then(function () { avisar('Lembrete copiado.'); }).catch(falhou);
      return;
    }
    if (acao === 'lembrete-enviado') {
      var le = S.lembretes[ref];
      if (!le || !confirm('Marcar o lembrete como enviado? Volta a contar ' + S.dados.lembrete_dias + ' dias.')) return;
      api('lembrete_enviado', { ids: le.ids }).then(function () { avisar('Lembrete registado.'); return recarregar(); }).catch(falhou);
      return;
    }
    if (acao === 'fatura-comprovativo') {
      var fm = el.closest('form'), refF = fm.querySelector('[name=imovel]').value;
      if (!refF) { avisar('Escolhe primeiro o imóvel.', true); return; }
      if (!confirm('Passar este PDF para os comprovativos de pagamento do imóvel?')) return;
      api('fatura_comprovativo', { id: id, imovel: refF }).then(function () { avisar('Passou a comprovativo: regista o pagamento no imóvel.'); return carregar(); }).catch(falhou);
      return;
    }
    if (acao === 'gerar-senha') { el.closest('form').querySelector('[name=senha]').value = gerarSenha(); return; }
    if (acao === 'verificar') {
      el.disabled = true;
      avisar('A verificar…', false, true);
      api('verificacao', undefined, el.getAttribute('data-imap') ? '&imap=1' : '').then(function (v) {
        S.verificacao = v;
        avisar('Verificação feita.');
        desenhar();
      }).catch(falhou).then(function () { el.disabled = false; });
    }
  }

  function aoSubmeter(ev) {
    var form = ev.target, tipo = form.getAttribute('data-form');
    if (!tipo) return;
    ev.preventDefault();
    var v = function (n) { var c = form.querySelector('[name="' + n + '"]'); return c ? c.value.trim() : ''; };
    if (tipo === 'entrar') {
      api('entrar', { email: v('email'), senha: form.querySelector('[name=senha]').value }).then(function (r) {
        S.csrf = r.csrf;
        location.hash = '';
        return carregar();
      }).catch(function (e) { avisar(e.message, true); });
      return;
    }
    if (tipo === 'instalar') {
      if (v('senha') !== v('senha2')) { avisar('As duas passwords não são iguais.', true); return; }
      api('instalar', { codigo: v('codigo'), senha: form.querySelector('[name=senha]').value }).then(function (r) {
        S.csrf = r.csrf;
        return carregar();
      }).catch(function (e) { avisar(e.message, true); });
      return;
    }
    if (tipo === 'senha') {
      api('senha_definir', { email: form.getAttribute('data-email'), senha: v('senha') }).then(function () {
        avisar('Password definida. Dá-a à pessoa por um canal seguro.');
        return recarregar();
      }).catch(falhou);
      return;
    }
    if (tipo === 'fatura') guardarFatura(form);
    if (tipo === 'comprovativo') {
      var ref = form.getAttribute('data-ref'), dados = new FormData(form);
      dados.append('imovel', ref);
      fetch('index.php?a=comprovativo_enviar', { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF': S.csrf }, body: dados })
        .then(function (r) { return r.json().then(function (j) { if (!r.ok || j.erro) throw new Error(j.erro || ('Erro ' + r.status)); return j; }); })
        .then(function (j) {
          S.carregados[ref] = (S.carregados[ref] || []).concat([j.id]);
          avisar('Comprovativo guardado na pasta do imóvel. Carrega em «Pagou» para o registar.');
          return recarregar();
        }).catch(falhou);
    }
  }

  function guardarFatura(form, mesmoAssim) {
    var id = form.getAttribute('data-id'), f = faturaDe(id) || {};
    var v = function (n) { return form.querySelector('[name="' + n + '"]').value.trim(); };
    var total = U.lerValor(v('total'));
    if (total === null || total <= 0) { avisar('O total tem de ser um valor como 38,47.', true); return; }
    var nome = v('fornecedor'), conhecido = ((S.regras && S.regras.fornecedores) || []).filter(function (x) { return x.nome.toLowerCase() === nome.toLowerCase(); })[0];
    var de = v('de'), ate = v('ate');
    if ((de && !ate) || (!de && ate)) { avisar('Período: preencher as duas datas (ou nenhuma).', true); return; }
    var periodo = (de && ate) ? { de: de, ate: ate } : ((f.periodo && f.periodo.mes) ? { mes: f.periodo.mes } : null);
    var campos = { imovel: v('imovel'), tipo: v('tipo'), fornecedor: conhecido ? conhecido.nome : nome, fornecedor_id: conhecido ? conhecido.id : null,
      total: total, periodo: periodo, data_limite: v('data_limite') || null, pagamento: f.pagamento || { metodo: null } };
    api('fatura_guardar', { id: id, campos: campos, mesmo_assim: !!mesmoAssim }).then(function () {
      avisar('Fatura guardada: a despesa já está no imóvel.');
      return carregar();
    }).catch(function (e) {
      if (e.status === 409 && /mesmo assim/.test(e.message) && confirm(e.message + '\n\nGuardar mesmo assim?')) return guardarFatura(form, true);
      falhou(e);
    });
  }

  // Para os testes no jsc (sem DOM): as vistas e o estado, para conferir o HTML que produzem.
  Despesas._pagina = { S: S, cartaoConfirmacao: cartaoConfirmacao, vistaPainelAdmin: vistaPainelAdmin, vistaFaturas: vistaFaturas, vistaImovelAdmin: vistaImovelAdmin,
    vistaPainelDono: vistaPainelDono, vistaImovelDono: vistaImovelDono, vistaAcessos: vistaAcessos, vistaVerificacao: vistaVerificacao,
    paraServidor: paraServidor };
})();
