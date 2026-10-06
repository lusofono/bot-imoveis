/* Despesas — tirar o texto de um PDF, sem serviços externos e sem bibliotecas.
   Lê os objetos (também os que vêm dentro de «object streams»), descomprime os fluxos (Flate, ASCIIHex, ASCII85),
   percorre as páginas, interpreta os operadores de texto (Tf, Td, Tm, Tj, TJ…, e os XObjects de formulário) e traduz
   os códigos para Unicode pela tabela ToUnicode da fonte ou, nas fontes simples, pela codificação (WinAnsi +
   /Differences). No fim junta os pedaços por linhas, pela posição na página.
   Não lê PDFs cifrados nem imagens (faturas digitalizadas): nesses casos devolve um aviso, não inventa texto. */
var Despesas = (typeof Despesas !== 'undefined') ? Despesas : {};

Despesas.pdf = (function () {
  'use strict';
  var U = Despesas.util;

  var FIM = { t: 'fim' }, ABRE_DICT = { t: '<<' }, FECHA_DICT = { t: '>>' }, ABRE_ARR = { t: '[' }, FECHA_ARR = { t: ']' };

  function eBranco(c) { return c === 32 || c === 10 || c === 13 || c === 9 || c === 12 || c === 0; }
  function eDelim(c) { return c === 40 || c === 41 || c === 60 || c === 62 || c === 91 || c === 93 || c === 123 || c === 125 || c === 47 || c === 37; }
  function nomeDe(v) { return (v && v.t === 'n') ? v.v : null; }
  function numero(v, padrao) { return (typeof v === 'number' && isFinite(v)) ? v : padrao; }

  // ── Leitor de tokens (serve para os objetos do ficheiro, os fluxos de conteúdo e os CMaps) ──────
  function Lexer(s, pos) { this.s = s; this.pos = pos || 0; }

  Lexer.prototype.saltarBranco = function () {
    var s = this.s, n = s.length;
    while (this.pos < n) {
      var c = s.charCodeAt(this.pos);
      if (eBranco(c)) { this.pos++; continue; }
      if (c === 37) { // % comentário até ao fim da linha
        while (this.pos < n) { c = s.charCodeAt(this.pos); if (c === 10 || c === 13) break; this.pos++; }
        continue;
      }
      break;
    }
  };

  Lexer.prototype.token = function () {
    for (;;) {
      this.saltarBranco();
      var s = this.s, n = s.length;
      if (this.pos >= n) return FIM;
      var c = s.charCodeAt(this.pos);
      if (c === 47) { // /Nome
        var i = this.pos + 1;
        while (i < n) { var cc = s.charCodeAt(i); if (eBranco(cc) || eDelim(cc)) break; i++; }
        var nome = s.substring(this.pos + 1, i).replace(/#([0-9A-Fa-f]{2})/g, function (_, h) { return String.fromCharCode(parseInt(h, 16)); });
        this.pos = i;
        return { t: 'n', v: nome };
      }
      if (c === 40) return { t: 's', v: this.literal() };
      if (c === 60) {
        if (s.charCodeAt(this.pos + 1) === 60) { this.pos += 2; return ABRE_DICT; }
        return { t: 's', v: this.hex() };
      }
      if (c === 62) {
        if (s.charCodeAt(this.pos + 1) === 62) { this.pos += 2; return FECHA_DICT; }
        this.pos++; continue; // «>» solto: ignora
      }
      if (c === 91) { this.pos++; return ABRE_ARR; }
      if (c === 93) { this.pos++; return FECHA_ARR; }
      if (c === 123 || c === 125 || c === 41) { this.pos++; continue; } // { } ) soltos
      var j = this.pos;
      while (j < n) { var d = s.charCodeAt(j); if (eBranco(d) || eDelim(d)) break; j++; }
      var palavra = s.substring(this.pos, j);
      this.pos = j;
      if (/^[+-]?(\d+\.?\d*|\.\d+)$/.test(palavra)) return parseFloat(palavra);
      if (palavra === 'true') return true;
      if (palavra === 'false') return false;
      if (palavra === 'null') return null;
      return { t: 'o', v: palavra };
    }
  };

  Lexer.prototype.literal = function () {
    var s = this.s, n = s.length, i = this.pos + 1, prof = 1, out = [];
    while (i < n) {
      var c = s[i];
      if (c === '\\') {
        var d = s[i + 1];
        i += 2;
        if (d === 'n') out.push('\n');
        else if (d === 'r') out.push('\r');
        else if (d === 't') out.push('\t');
        else if (d === 'b') out.push('\b');
        else if (d === 'f') out.push('\f');
        else if (d === '\r') { if (s[i] === '\n') i++; } // continuação de linha
        else if (d === '\n') { /* continuação de linha */ }
        else if (d >= '0' && d <= '7') {
          var oct = d;
          while (oct.length < 3 && s[i] >= '0' && s[i] <= '7') { oct += s[i]; i++; }
          out.push(String.fromCharCode(parseInt(oct, 8) & 0xff));
        } else if (d !== undefined) out.push(d); // \( \) \\ e outros
        continue;
      }
      if (c === '(') prof++;
      else if (c === ')') { prof--; if (prof === 0) { i++; break; } }
      out.push(c);
      i++;
    }
    this.pos = i;
    return out.join('');
  };

  Lexer.prototype.hex = function () {
    var s = this.s, fim = s.indexOf('>', this.pos + 1);
    if (fim < 0) fim = s.length;
    var h = s.substring(this.pos + 1, fim).replace(/[^0-9A-Fa-f]/g, '');
    if (h.length % 2) h += '0';
    var out = [];
    for (var i = 0; i < h.length; i += 2) out.push(String.fromCharCode(parseInt(h.substr(i, 2), 16)));
    this.pos = fim + 1;
    return out.join('');
  };

  // Um valor completo: dicionário, array, referência «n g R» ou um token simples.
  Lexer.prototype.valor = function (tok) {
    if (tok === undefined) tok = this.token();
    if (tok === ABRE_DICT) {
      var d = {};
      for (;;) {
        var k = this.token();
        if (k === FECHA_DICT || k === FIM) break;
        if (!k || k.t !== 'n') continue;
        var v = this.valor();
        if (v === FECHA_DICT || v === FIM) break;
        d[k.v] = v;
      }
      return { t: 'd', v: d };
    }
    if (tok === ABRE_ARR) {
      var a = [];
      for (;;) {
        var x = this.token();
        if (x === FECHA_ARR || x === FIM) break;
        a.push(this.valor(x));
      }
      return a;
    }
    if (typeof tok === 'number' && tok >= 0 && Math.floor(tok) === tok) {
      var guarda = this.pos, t2 = this.token();
      if (typeof t2 === 'number' && Math.floor(t2) === t2) {
        var t3 = this.token();
        if (t3 && t3.t === 'o' && t3.v === 'R') return { t: 'r', n: tok, g: t2 };
      }
      this.pos = guarda;
    }
    return tok;
  };

  // ── Filtros ──────────────────────────────────────────────────────────────────────────────────
  function deHex(s) {
    var fim = s.indexOf('>');
    if (fim >= 0) s = s.substring(0, fim);
    var h = s.replace(/[^0-9A-Fa-f]/g, '');
    if (h.length % 2) h += '0';
    var out = [];
    for (var i = 0; i < h.length; i += 2) out.push(String.fromCharCode(parseInt(h.substr(i, 2), 16)));
    return out.join('');
  }

  function deA85(s) {
    var fim = s.indexOf('~>');
    if (fim >= 0) s = s.substring(0, fim);
    if (s.substring(0, 2) === '<~') s = s.substring(2);
    s = s.replace(/\s+/g, '');
    var out = [], grupo = [];
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c === 122 && grupo.length === 0) { out.push('\0\0\0\0'); continue; } // z
      if (c < 33 || c > 117) continue;
      grupo.push(c - 33);
      if (grupo.length === 5) { out.push(bloco85(grupo, 4)); grupo = []; }
    }
    if (grupo.length > 1) {
      var falta = 5 - grupo.length;
      while (grupo.length < 5) grupo.push(84);
      out.push(bloco85(grupo, 4 - falta));
    }
    return out.join('');
  }
  function bloco85(g, nBytes) {
    var v = (((g[0] * 85 + g[1]) * 85 + g[2]) * 85 + g[3]) * 85 + g[4];
    var b = [(v / 16777216) & 0xff, (v / 65536) & 0xff, (v / 256) & 0xff, v & 0xff];
    // v pode passar de 2^31: usar divisões em vez de deslocamentos
    b[0] = Math.floor(v / 16777216) & 0xff; b[1] = Math.floor(v / 65536) & 0xff; b[2] = Math.floor(v / 256) & 0xff; b[3] = v % 256;
    return String.fromCharCode.apply(null, b.slice(0, nBytes));
  }

  // ── O documento: tabela de objetos ───────────────────────────────────────────────────────────
  function Documento(bytes) {
    this.bin = U.bytesParaBinario(bytes);
    this.objs = {};
    this.fontes = {};
    this.indexar();
  }

  Documento.prototype.guardar = function (num, ent) {
    var antigo = this.objs[num];
    if (!antigo || antigo.pos <= ent.pos) this.objs[num] = ent; // a definição mais à frente no ficheiro ganha
  };

  Documento.prototype.indexar = function () {
    var s = this.bin, re = /(\d+)\s+(\d+)\s+obj\b/g, m;
    while ((m = re.exec(s))) {
      var num = parseInt(m[1], 10), pos = m.index;
      if (pos > 0) {
        var antes = s.charCodeAt(pos - 1);
        if (!(eBranco(antes) || eDelim(antes))) continue;
      }
      var lx = new Lexer(s, re.lastIndex), valor;
      try { valor = lx.valor(); } catch (e) { continue; }
      var ent = { pos: pos, valor: valor, dados: null };
      lx.saltarBranco();
      if (s.substr(lx.pos, 6) === 'stream') {
        var ini = lx.pos + 6;
        if (s[ini] === '\r') ini++;
        if (s[ini] === '\n') ini++;
        var comp = (valor && valor.t === 'd') ? valor.v.Length : null, fim = -1;
        if (typeof comp === 'number' && comp >= 0 && ini + comp <= s.length && /^\s*endstream/.test(s.substr(ini + comp, 30))) fim = ini + comp;
        if (fim < 0) {
          fim = s.indexOf('endstream', ini);
          if (fim < 0) fim = s.length;
          if (s[fim - 1] === '\n') fim--;
          if (s[fim - 1] === '\r') fim--;
        }
        ent.dados = s.substring(ini, fim);
        re.lastIndex = fim; // não procurar «obj» dentro do fluxo
      }
      this.guardar(num, ent);
    }
    var nums = Object.keys(this.objs);
    for (var i = 0; i < nums.length; i++) {
      var o = this.objs[nums[i]];
      if (o.dados !== null && o.valor && o.valor.t === 'd' && nomeDe(o.valor.v.Type) === 'ObjStm') this.lerObjStm(o);
    }
  };

  Documento.prototype.lerObjStm = function (o) {
    var dados = this.descodificar(o);
    if (dados === null) return;
    var d = o.valor.v, n = numero(this.resolver(d.N), 0), primeiro = numero(this.resolver(d.First), -1);
    if (n <= 0 || primeiro < 0) return;
    var lx = new Lexer(dados, 0), pares = [];
    for (var i = 0; i < n; i++) {
      var a = lx.token(), b = lx.token();
      if (typeof a !== 'number' || typeof b !== 'number') break;
      pares.push([a, b]);
    }
    for (var j = 0; j < pares.length; j++) {
      var v;
      try { v = new Lexer(dados, primeiro + pares[j][1]).valor(); } catch (e) { continue; }
      this.guardar(pares[j][0], { pos: o.pos + (j + 1) / 1e6, valor: v, dados: null });
    }
  };

  Documento.prototype.resolver = function (v) {
    for (var prof = 0; prof < 20 && v && v.t === 'r'; prof++) {
      var o = this.objs[v.n];
      v = o ? o.valor : null;
    }
    return (v && v.t === 'r') ? null : v;
  };

  Documento.prototype.entrada = function (ref) {
    return (ref && ref.t === 'r') ? (this.objs[ref.n] || null) : null;
  };

  Documento.prototype.descodificar = function (ent) {
    if (!ent || ent.dados === null) return null;
    if (ent.descodificado !== undefined) return ent.descodificado;
    var d = (ent.valor && ent.valor.t === 'd') ? ent.valor.v : {};
    var filtros = this.resolver(d.Filter);
    if (!filtros) filtros = [];
    else if (!Array.isArray(filtros)) filtros = [filtros];
    var dados = ent.dados;
    for (var i = 0; i < filtros.length && dados !== null; i++) {
      var f = nomeDe(this.resolver(filtros[i]));
      try {
        if (f === 'FlateDecode' || f === 'Fl') dados = U.bytesParaBinario(U.inflate(U.binarioParaBytes(dados)));
        else if (f === 'ASCIIHexDecode' || f === 'AHx') dados = deHex(dados);
        else if (f === 'ASCII85Decode' || f === 'A85') dados = deA85(dados);
        else dados = null; // imagens (DCT, JPX, CCITT, JBIG2) e LZW: não trazem texto que nos sirva
      } catch (e) { dados = null; }
    }
    ent.descodificado = dados;
    return dados;
  };

  Documento.prototype.paginas = function () {
    var self = this, lista = [], vistos = {}, s = this.bin, re = /\/Root\s+(\d+)\s+(\d+)\s+R/g, m, ultimo = null;
    while ((m = re.exec(s))) ultimo = m;
    function percorrer(no, recursos, prof) {
      if (!no || no.t !== 'd' || prof > 40) return;
      var d = no.v, rec = (d.Resources !== undefined) ? self.resolver(d.Resources) : recursos, tipo = nomeDe(self.resolver(d.Type));
      if (tipo === 'Pages' || (tipo !== 'Page' && d.Kids)) {
        var kids = self.resolver(d.Kids) || [];
        for (var i = 0; i < kids.length; i++) {
          var k = kids[i];
          if (k && k.t === 'r') { if (vistos[k.n]) continue; vistos[k.n] = 1; }
          percorrer(self.resolver(k), rec, prof + 1);
        }
      } else {
        lista.push({ dict: d, recursos: rec });
      }
    }
    if (ultimo) {
      var raiz = this.resolver({ t: 'r', n: parseInt(ultimo[1], 10), g: 0 });
      if (raiz && raiz.t === 'd') percorrer(this.resolver(raiz.v.Pages), null, 0);
    }
    if (!lista.length) {
      // Sem catálogo legível: as páginas pela ordem em que aparecem no ficheiro.
      Object.keys(this.objs).map(function (k) { return self.objs[k]; })
        .filter(function (o) { return o.valor && o.valor.t === 'd' && nomeDe(o.valor.v.Type) === 'Page'; })
        .sort(function (a, b) { return a.pos - b.pos; })
        .forEach(function (o) { lista.push({ dict: o.valor.v, recursos: self.resolver(o.valor.v.Resources) }); });
    }
    return lista;
  };

  Documento.prototype.conteudo = function (pagina) {
    var c = pagina.dict.Contents, partes = [], self = this;
    var lista = Array.isArray(c) ? c : (Array.isArray(this.resolver(c)) ? this.resolver(c) : [c]);
    lista.forEach(function (ref) {
      var dados = self.descodificar(self.entrada(ref));
      if (dados) partes.push(dados);
    });
    return partes.join('\n');
  };

  Documento.prototype.fonte = function (ref) {
    var chave = (ref && ref.t === 'r') ? ref.n : null;
    if (chave !== null && this.fontes[chave]) return this.fontes[chave];
    var d = this.resolver(ref);
    var f = (d && d.t === 'd') ? new Fonte(this, d) : null;
    if (chave !== null) this.fontes[chave] = f;
    return f;
  };

  // ── Fontes ───────────────────────────────────────────────────────────────────────────────────
  function Fonte(doc, dict) {
    var d = dict.v, i;
    this.subtipo = nomeDe(doc.resolver(d.Subtype));
    this.composta = this.subtipo === 'Type0';
    this.mapa = null;
    this.espacos = null;
    this.larguras = {};
    this.escala = 1;
    this.cod = null;
    var tu = doc.descodificar(doc.entrada(d.ToUnicode));
    if (tu) this.lerCMap(tu);
    if (this.composta) {
      var desc = doc.resolver(d.DescendantFonts);
      desc = Array.isArray(desc) ? doc.resolver(desc[0]) : desc;
      var dd = (desc && desc.t === 'd') ? desc.v : {};
      this.larguraPadrao = numero(doc.resolver(dd.DW), 1000);
      var w = doc.resolver(dd.W);
      if (Array.isArray(w)) {
        for (i = 0; i < w.length;) {
          var c0 = doc.resolver(w[i]), nx = doc.resolver(w[i + 1]);
          if (typeof c0 !== 'number') break;
          if (Array.isArray(nx)) {
            for (var k = 0; k < nx.length; k++) this.larguras[c0 + k] = numero(doc.resolver(nx[k]), this.larguraPadrao);
            i += 2;
          } else {
            var c1 = numero(nx, c0), lw = numero(doc.resolver(w[i + 2]), this.larguraPadrao);
            for (var c = c0; c <= c1 && c - c0 < 65536; c++) this.larguras[c] = lw;
            i += 3;
          }
        }
      }
      if (!this.espacos) this.espacos = [{ len: 2, lo: '\x00\x00', hi: '\xff\xff' }];
    } else {
      var primeiro = numero(doc.resolver(d.FirstChar), 0), ws = doc.resolver(d.Widths);
      this.temLarguras = Array.isArray(ws);
      if (this.temLarguras) for (i = 0; i < ws.length; i++) this.larguras[primeiro + i] = numero(doc.resolver(ws[i]), 0);
      var fd = doc.resolver(d.FontDescriptor);
      this.larguraPadrao = (fd && fd.t === 'd') ? numero(doc.resolver(fd.v.MissingWidth), 0) : 0;
      if (this.subtipo === 'Type3') {
        var fm = doc.resolver(d.FontMatrix);
        if (Array.isArray(fm)) this.escala = numero(doc.resolver(fm[0]), 0.001) * 1000;
      }
      this.cod = codificacaoSimples(doc, doc.resolver(d.Encoding));
    }
  }

  // Larguras aproximadas (Helvetica) para as fontes padrão sem /Widths.
  function larguraEstimada(c) {
    if (c === 32) return 278;
    if (c >= 48 && c <= 57) return 556;
    if (c >= 65 && c <= 90) return 667;
    if (c === 44 || c === 46) return 278;
    return 500;
  }

  Fonte.prototype.comprimentoCodigo = function (bin, i) {
    var resto = bin.length - i;
    if (!this.espacos) return 1;
    for (var r = 0; r < this.espacos.length; r++) {
      var e = this.espacos[r];
      if (e.len > resto) continue;
      var ok = true;
      for (var k = 0; k < e.len; k++) {
        var b = bin.charCodeAt(i + k);
        if (b < e.lo.charCodeAt(k) || b > e.hi.charCodeAt(k)) { ok = false; break; }
      }
      if (ok) return e.len;
    }
    return Math.min(this.espacos[0].len, resto);
  };

  Fonte.prototype.descodificar = function (bin) {
    var out = [], i = 0;
    while (i < bin.length) {
      var len = this.comprimentoCodigo(bin, i), codigo = bin.substr(i, len), num = 0, k;
      i += len;
      for (k = 0; k < codigo.length; k++) num = num * 256 + codigo.charCodeAt(k);
      var t = this.mapa ? this.mapa[codigo] : undefined;
      if (t === undefined && !this.composta) t = this.cod[num & 0xff];
      if (t === undefined) t = null;
      var w = this.larguras[num];
      if (w === undefined || (w === 0 && !this.composta && !this.temLarguras)) w = this.larguraPadrao || (this.composta ? 1000 : larguraEstimada(num));
      out.push({ t: t, w: w * this.escala, espaco: len === 1 && num === 32 });
    }
    return out;
  };

  Fonte.prototype.lerCMap = function (s) {
    var mapa = {}, espacos = [], lx = new Lexer(s, 0), pilha = [], i, total = 0;
    for (;;) {
      var tok = lx.token();
      if (tok === FIM) break;
      if (tok === ABRE_ARR) {
        var arr = [];
        for (;;) { var x = lx.token(); if (x === FECHA_ARR || x === FIM) break; arr.push(x); }
        pilha.push(arr);
        continue;
      }
      if (tok && tok.t === 'o') {
        var op = tok.v;
        if (op === 'endcodespacerange') {
          for (i = 0; i + 1 < pilha.length; i += 2) {
            if (pilha[i] && pilha[i].t === 's' && pilha[i + 1] && pilha[i + 1].t === 's' && pilha[i].v.length)
              espacos.push({ len: pilha[i].v.length, lo: pilha[i].v, hi: pilha[i + 1].v });
          }
        } else if (op === 'endbfchar') {
          for (i = 0; i + 1 < pilha.length; i += 2) {
            if (pilha[i] && pilha[i].t === 's' && pilha[i + 1] && pilha[i + 1].t === 's') { mapa[pilha[i].v] = destino(pilha[i + 1].v, 0); total++; }
          }
        } else if (op === 'endbfrange') {
          for (i = 0; i + 2 < pilha.length; i += 3) {
            var lo = pilha[i], hi = pilha[i + 1], dst = pilha[i + 2];
            if (!lo || lo.t !== 's' || !hi || hi.t !== 's' || !lo.v.length) continue;
            var nlo = numBin(lo.v), nhi = numBin(hi.v), len = lo.v.length;
            if (nhi < nlo || nhi - nlo > 65535) continue;
            for (var c = nlo; c <= nhi; c++) {
              var cod = binNum(c, len);
              if (Array.isArray(dst)) { var e = dst[c - nlo]; if (e && e.t === 's') mapa[cod] = destino(e.v, 0); }
              else if (dst && dst.t === 's') mapa[cod] = destino(dst.v, c - nlo);
              total++;
            }
          }
        }
        pilha = [];
        continue;
      }
      pilha.push(tok);
    }
    espacos.sort(function (a, b) { return a.len - b.len; });
    if (total) this.mapa = mapa;
    if (espacos.length) this.espacos = espacos;
  };

  function numBin(s) { var n = 0; for (var i = 0; i < s.length; i++) n = n * 256 + s.charCodeAt(i); return n; }
  function binNum(n, len) { var s = ''; for (var i = 0; i < len; i++) { s = String.fromCharCode(n & 0xff) + s; n = Math.floor(n / 256); } return s; }
  function destino(bin, incremento) {
    if (bin.length === 1) return String.fromCharCode(bin.charCodeAt(0) + incremento);
    var u = U.utf16beParaTexto(bin);
    if (!u.length || !incremento) return u;
    return u.slice(0, -1) + String.fromCharCode(u.charCodeAt(u.length - 1) + incremento);
  }

  // Codificação das fontes simples: WinAnsi (Windows-1252) por omissão, ou MacRoman quando a fonte o diz
  // (muito usada pelos programas de faturação que geram PDFs com fontes TrueType).
  var MAC_ROMAN_ALTO = '\u00c4\u00c5\u00c7\u00c9\u00d1\u00d6\u00dc\u00e1\u00e0\u00e2\u00e4\u00e3\u00e5\u00e7\u00e9\u00e8\u00ea\u00eb\u00ed\u00ec\u00ee\u00ef\u00f1\u00f3\u00f2\u00f4\u00f6\u00f5\u00fa\u00f9\u00fb\u00fc\u2020\u00b0\u00a2\u00a3\u00a7\u2022\u00b6\u00df\u00ae\u00a9\u2122\u00b4\u00a8\u2260\u00c6\u00d8\u221e\u00b1\u2264\u2265\u00a5\u00b5\u2202\u2211\u220f\u03c0\u222b\u00aa\u00ba\u03a9\u00e6\u00f8\u00bf\u00a1\u00ac\u221a\u0192\u2248\u2206\u00ab\u00bb\u2026\u00a0\u00c0\u00c3\u00d5\u0152\u0153\u2013\u2014\u201c\u201d\u2018\u2019\u00f7\u25ca\u00ff\u0178\u2044\u20ac\u2039\u203a\ufb01\ufb02\u2021\u00b7\u201a\u201e\u2030\u00c2\u00ca\u00c1\u00cb\u00c8\u00cd\u00ce\u00cf\u00cc\u00d3\u00d4\ufffd\u00d2\u00da\u00db\u00d9\u0131\u02c6\u02dc\u00af\u02d8\u02d9\u02da\u00b8\u02dd\u02db\u02c7';
  function codificacaoSimples(doc, enc) {
    var tabela = new Array(256), i, dif = null, base = nomeDe(enc);
    if (enc && enc.t === 'd') { dif = doc.resolver(enc.v.Differences); base = nomeDe(doc.resolver(enc.v.BaseEncoding)); }
    var mac = base === 'MacRomanEncoding';
    for (i = 0; i < 256; i++) {
      if (i < 32) tabela[i] = (i === 9 || i === 10 || i === 13) ? ' ' : undefined;
      else if (mac && i >= 128) tabela[i] = MAC_ROMAN_ALTO.charAt(i - 128);
      else tabela[i] = U.cp1252Carater(i);
    }
    if (Array.isArray(dif)) {
      var cod = 0;
      for (i = 0; i < dif.length; i++) {
        var x = doc.resolver(dif[i]);
        if (typeof x === 'number') cod = x;
        else if (x && x.t === 'n') { if (cod >= 0 && cod < 256) { var g = glifo(x.v); if (g !== null) tabela[cod] = g; } cod++; }
      }
    }
    return tabela;
  }

  // Nomes de glifos (subconjunto da Adobe Glyph List que aparece em faturas portuguesas).
  var GLIFOS = {
    space: ' ', nbspace: ' ', period: '.', comma: ',', colon: ':', semicolon: ';', hyphen: '-', minus: '-', endash: '–',
    emdash: '—', slash: '/', backslash: '\\', parenleft: '(', parenright: ')', bracketleft: '[', bracketright: ']',
    braceleft: '{', braceright: '}', percent: '%', ampersand: '&', at: '@', numbersign: '#', dollar: '$', Euro: '€', euro: '€',
    quotesingle: '\'', quotedbl: '"', quoteright: '’', quoteleft: '‘', quotedblleft: '“', quotedblright: '”',
    quotesinglbase: '‚', quotedblbase: '„', guillemotleft: '«', guillemotright: '»', bullet: '•', degree: '°',
    ordmasculine: 'º', ordfeminine: 'ª', plus: '+', equal: '=', less: '<', greater: '>', underscore: '_', asterisk: '*',
    exclam: '!', question: '?', exclamdown: '¡', questiondown: '¿', bar: '|', asciitilde: '~', asciicircum: '^', grave: '`',
    section: '§', paragraph: '¶', copyright: '©', registered: '®', trademark: '™', ellipsis: '…', periodcentered: '·',
    multiply: '×', divide: '÷', plusminus: '±', onehalf: '½', onequarter: '¼', threequarters: '¾', mu: 'µ', twosuperior: '²',
    threesuperior: '³', onesuperior: '¹', fi: 'fi', fl: 'fl', zero: '0', one: '1', two: '2', three: '3', four: '4', five: '5',
    six: '6', seven: '7', eight: '8', nine: '9', florin: 'ƒ', cent: '¢', sterling: '£', yen: '¥', currency: '¤', brokenbar: '¦',
    dieresis: '¨', macron: '¯', acute: '´', cedilla: '¸', circumflex: 'ˆ', tilde: '˜', dagger: '†', daggerdbl: '‡', perthousand: '‰'
  };
  (function () {
    var acentos = { grave: 'àèìòù', acute: 'áéíóúý', circumflex: 'âêîôû', tilde: 'ãñõ', dieresis: 'äëïöüÿ', ring: 'å', cedilla: 'ç' };
    Object.keys(acentos).forEach(function (sufixo) {
      var letras = acentos[sufixo];
      for (var i = 0; i < letras.length; i++) {
        var l = letras[i], base = l.normalize('NFD')[0];
        GLIFOS[base + sufixo] = l;
        if (l !== 'ÿ') GLIFOS[base.toUpperCase() + sufixo] = l.toUpperCase();
      }
    });
    GLIFOS.germandbls = 'ß'; GLIFOS.ae = 'æ'; GLIFOS.AE = 'Æ'; GLIFOS.oe = 'œ'; GLIFOS.OE = 'Œ'; GLIFOS.oslash = 'ø'; GLIFOS.Oslash = 'Ø';
  })();
  function glifo(nome) {
    if (/^[A-Za-z]$/.test(nome)) return nome;
    if (GLIFOS.hasOwnProperty(nome)) return GLIFOS[nome];
    var m = /^uni([0-9A-Fa-f]{4})+$/.exec(nome);
    if (m) {
      var s = '';
      for (var i = 3; i + 4 <= nome.length; i += 4) s += String.fromCharCode(parseInt(nome.substr(i, 4), 16));
      return s;
    }
    m = /^u([0-9A-Fa-f]{4,6})$/.exec(nome);
    if (m) return String.fromCodePoint(parseInt(m[1], 16));
    var base = nome.split('.')[0].split('_')[0];
    if (base !== nome && base) return glifo(base);
    return null;
  }

  // ── Interpretar o conteúdo das páginas ───────────────────────────────────────────────────────
  function mult(a, b) {
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
      a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]];
  }
  function aplicar(m, x, y) { return { x: x * m[0] + y * m[2] + m[4], y: x * m[1] + y * m[3] + m[5] }; }
  function seis(ops, doc) {
    if (ops.length < 6) return null;
    var r = ops.slice(ops.length - 6).map(function (v) { return numero(doc ? doc.resolver(v) : v, NaN); });
    return r.every(function (v) { return !isNaN(v); }) ? r : null;
  }
  function copiaGs(gs) {
    return { ctm: gs.ctm.slice(), fonte: gs.fonte, tam: gs.tam, Tc: gs.Tc, Tw: gs.Tw, Tz: gs.Tz, TL: gs.TL, Ts: gs.Ts };
  }

  var FONTE_NULA = {
    descodificar: function (bin) {
      var out = [];
      for (var i = 0; i < bin.length; i++) {
        var c = bin.charCodeAt(i) & 0xff;
        out.push({ t: c < 32 ? null : U.cp1252Carater(c), w: larguraEstimada(c), espaco: c === 32 });
      }
      return out;
    }
  };

  function Contexto(doc) {
    this.doc = doc;
    this.gs = { ctm: [1, 0, 0, 1, 0, 0], fonte: null, tam: 10, Tc: 0, Tw: 0, Tz: 100, TL: 0, Ts: 0 };
    this.pilha = [];
    this.tm = [1, 0, 0, 1, 0, 0];
    this.tlm = [1, 0, 0, 1, 0, 0];
    this.pedacos = [];
  }

  Contexto.prototype.mover = function (tx, ty) {
    this.tlm = mult([1, 0, 0, 1, tx, ty], this.tlm);
    this.tm = this.tlm.slice();
  };

  Contexto.prototype.avancar = function (tx) {
    this.tm = mult([1, 0, 0, 1, tx, 0], this.tm);
  };

  Contexto.prototype.mostrar = function (s) {
    if (!s || s.t !== 's' || !s.v.length) return;
    var gs = this.gs, f = gs.fonte || FONTE_NULA, glifos = f.descodificar(s.v);
    var trm = mult(this.tm, gs.ctm), inicio = aplicar(trm, 0, gs.Ts);
    var escalaV = Math.sqrt(trm[2] * trm[2] + trm[3] * trm[3]) || 1;
    var tam = Math.abs(gs.tam) * escalaV || 1;
    var texto = '', ilegiveis = 0;
    for (var i = 0; i < glifos.length; i++) {
      var g = glifos[i];
      if (g.t === null) { texto += '�'; ilegiveis++; } else texto += g.t;
      var tx = ((g.w / 1000) * gs.tam + gs.Tc + (g.espaco ? gs.Tw : 0)) * gs.Tz / 100;
      this.avancar(tx);
    }
    var fim = aplicar(mult(this.tm, gs.ctm), 0, gs.Ts);
    var norma = Math.sqrt(trm[0] * trm[0] + trm[1] * trm[1]) || 1;
    this.pedacos.push({
      x: inicio.x, y: inicio.y, xf: fim.x, yf: fim.y, tam: tam, t: texto, ilegiveis: ilegiveis,
      c: trm[0] / norma, s: trm[1] / norma,
      rodado: Math.abs(trm[1]) > Math.abs(trm[0]) + 1e-6 || trm[0] < 0
    });
  };

  Contexto.prototype.fonteDe = function (recursos, nome) {
    if (!nome || nome.t !== 'n' || !recursos || recursos.t !== 'd') return null;
    var fontes = this.doc.resolver(recursos.v.Font);
    if (!fontes || fontes.t !== 'd') return null;
    var ref = fontes.v[nome.v];
    return ref ? this.doc.fonte(ref) : null;
  };

  Contexto.prototype.interpretar = function (conteudo, recursos, prof) {
    var lx = new Lexer(conteudo, 0), ops = [];
    for (;;) {
      var tok = lx.token();
      if (tok === FIM) break;
      if (tok === ABRE_ARR || tok === ABRE_DICT) { ops.push(lx.valor(tok)); continue; }
      if (tok === FECHA_ARR || tok === FECHA_DICT) continue;
      if (tok !== null && typeof tok === 'object' && tok.t === 'o') {
        this.executar(tok.v, ops, recursos, lx, prof);
        ops = [];
        continue;
      }
      ops.push(tok);
    }
  };

  Contexto.prototype.executar = function (op, ops, recursos, lx, prof) {
    var gs = this.gs, m, i;
    switch (op) {
      case 'q': this.pilha.push(copiaGs(gs)); break;
      case 'Q': if (this.pilha.length) this.gs = this.pilha.pop(); break;
      case 'cm': m = seis(ops); if (m) gs.ctm = mult(m, gs.ctm); break;
      case 'BT': this.tm = [1, 0, 0, 1, 0, 0]; this.tlm = [1, 0, 0, 1, 0, 0]; break;
      case 'Tf': gs.fonte = this.fonteDe(recursos, ops[0]); gs.tam = numero(ops[1], gs.tam); break;
      case 'Tc': gs.Tc = numero(ops[0], 0); break;
      case 'Tw': gs.Tw = numero(ops[0], 0); break;
      case 'Tz': gs.Tz = numero(ops[0], 100); break;
      case 'TL': gs.TL = numero(ops[0], 0); break;
      case 'Ts': gs.Ts = numero(ops[0], 0); break;
      case 'Td': this.mover(numero(ops[0], 0), numero(ops[1], 0)); break;
      case 'TD': gs.TL = -numero(ops[1], 0); this.mover(numero(ops[0], 0), numero(ops[1], 0)); break;
      case 'Tm': m = seis(ops); if (m) { this.tlm = m; this.tm = m.slice(); } break;
      case 'T*': this.mover(0, -gs.TL); break;
      case 'Tj': this.mostrar(ops[0]); break;
      case '\'': this.mover(0, -gs.TL); this.mostrar(ops[0]); break;
      case '"': gs.Tw = numero(ops[0], 0); gs.Tc = numero(ops[1], 0); this.mover(0, -gs.TL); this.mostrar(ops[2]); break;
      case 'TJ':
        if (Array.isArray(ops[0])) {
          for (i = 0; i < ops[0].length; i++) {
            var e = ops[0][i];
            if (typeof e === 'number') this.avancar(-e / 1000 * gs.tam * gs.Tz / 100);
            else this.mostrar(e);
          }
        }
        break;
      case 'Do': this.xobjeto(ops[0], recursos, prof); break;
      case 'ID': this.saltarImagem(lx); break;
    }
  };

  Contexto.prototype.saltarImagem = function (lx) {
    var s = lx.s, k = lx.pos;
    while ((k = s.indexOf('EI', k)) >= 0) {
      var antes = s.charCodeAt(k - 1), depois = s.charCodeAt(k + 2);
      if (eBranco(antes) && (isNaN(depois) || eBranco(depois))) break;
      k += 2;
    }
    lx.pos = (k < 0) ? s.length : k + 2;
  };

  Contexto.prototype.xobjeto = function (nome, recursos, prof) {
    if (prof > 8 || !nome || nome.t !== 'n' || !recursos || recursos.t !== 'd') return;
    var doc = this.doc, xo = doc.resolver(recursos.v.XObject);
    if (!xo || xo.t !== 'd') return;
    var ent = doc.entrada(xo.v[nome.v]);
    if (!ent || !ent.valor || ent.valor.t !== 'd') return;
    var d = ent.valor.v;
    if (nomeDe(doc.resolver(d.Subtype)) !== 'Form') return;
    var dados = doc.descodificar(ent);
    if (!dados) return;
    var salvo = copiaGs(this.gs), tm = this.tm, tlm = this.tlm, mat = doc.resolver(d.Matrix);
    if (Array.isArray(mat)) { var m = seis(mat, doc); if (m) this.gs.ctm = mult(m, this.gs.ctm); }
    var rec = d.Resources ? doc.resolver(d.Resources) : recursos;
    this.interpretar(dados, rec, prof + 1);
    this.gs = salvo; this.tm = tm; this.tlm = tlm;
  };

  // ── Juntar os pedaços em linhas, de cima para baixo e da esquerda para a direita ─────────────
  // O texto rodado (por exemplo os dados da empresa ao longo da margem) junta-se por linhas na sua própria direção:
  // roda-se cada grupo de volta à horizontal e usa-se o mesmo método. Fica no fim da página.
  function montarLinhas(pedacos) {
    var normais = [], grupos = {};
    pedacos.forEach(function (p) {
      if (!p.t.length) return;
      if (!p.rodado) { normais.push(p); return; }
      var k = Math.round(Math.atan2(p.s, p.c) * 20);
      (grupos[k] = grupos[k] || []).push({
        x: p.x * p.c + p.y * p.s, y: -p.x * p.s + p.y * p.c, xf: p.xf * p.c + p.yf * p.s, tam: p.tam, t: p.t
      });
    });
    var saida = juntar(normais);
    Object.keys(grupos).sort().forEach(function (k) { saida = saida.concat(juntar(grupos[k])); });
    return saida.map(function (t) { return t.replace(/\u00a0/g, ' ').replace(/[ \t]{4,}/g, '   ').replace(/\s+$/, ''); })
      .filter(function (t) { return t.replace(/\s/g, '').length > 0; });
  }

  function juntar(normais) {
    normais.sort(function (a, b) { return (b.y - a.y) || (a.x - b.x); });
    var linhas = [], atual = null;
    normais.forEach(function (p) {
      if (atual && Math.abs(atual.y - p.y) <= Math.max(1, 0.4 * Math.min(atual.tam, p.tam))) atual.pedacos.push(p);
      else { atual = { y: p.y, tam: p.tam, pedacos: [p] }; linhas.push(atual); }
    });
    var saida = linhas.map(function (l) {
      l.pedacos.sort(function (a, b) { return a.x - b.x; });
      var texto = '', fimAnt = null, xAnt = null, tAnt = null;
      l.pedacos.forEach(function (p) {
        if (fimAnt !== null) {
          if (p.t === tAnt && Math.abs(p.x - xAnt) < p.tam * 0.1) return; // texto repetido (negrito falso)
          var folga = p.x - fimAnt;
          if (folga > p.tam * 2) texto = texto.replace(/\s+$/, '') + '   ';
          else if (folga > p.tam * 0.15 && !/\s$/.test(texto) && !/^\s/.test(p.t)) texto += ' ';
        }
        texto += p.t;
        fimAnt = (fimAnt === null) ? p.xf : Math.max(fimAnt, p.xf);
        xAnt = p.x; tAnt = p.t;
      });
      return texto;
    });
    return saida;
  }

  // ── Entrada pública ──────────────────────────────────────────────────────────────────────────
  function extrair(bytes) {
    var r = { paginas: [], texto: '', temTexto: false, protegido: false, avisos: [] };
    try {
      var cabeca = U.bytesParaBinario(bytes, 0, Math.min(bytes.length, 1024));
      if (cabeca.indexOf('%PDF') < 0) { r.avisos.push('O ficheiro não parece um PDF.'); return r; }
      var doc = new Documento(bytes);
      if (/\/Encrypt\s*(?:\d+\s+\d+\s+R|<<)/.test(doc.bin)) {
        r.protegido = true;
        r.avisos.push('PDF protegido (cifrado): ainda não sei lê-lo. Preencher à mão ou trazer ao Claude.');
        return r;
      }
      doc.paginas().forEach(function (pag) {
        var ctx = new Contexto(doc);
        ctx.interpretar(doc.conteudo(pag), pag.recursos, 0);
        r.paginas.push(montarLinhas(ctx.pedacos).join('\n'));
      });
    } catch (e) {
      r.avisos.push('Não consegui ler o PDF (' + (e && e.message ? e.message : e) + ').');
    }
    r.texto = r.paginas.join('\n\n');
    var letras = r.texto.replace(/[\s�]/g, '').length, ilegiveis = (r.texto.match(/�/g) || []).length;
    r.temTexto = letras >= 20;
    if (!r.temTexto && !r.avisos.length) r.avisos.push('O PDF não tem texto (fatura digitalizada?): identificar à mão.');
    else if (r.temTexto && ilegiveis > letras * 0.3) r.avisos.push('Parte do texto do PDF não se consegue ler (fonte sem tabela Unicode).');
    return r;
  }

  return { extrair: extrair, _Lexer: Lexer, _glifo: glifo, _deA85: deA85 };
})();
