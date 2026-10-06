/* Despesas — utilitários do motor (bytes, texto, base64, SHA-256, inflate, dinheiro e datas).
   O motor corre igual no browser e no jsc do macOS (os testes): nada de módulos, nada de APIs do browser.
   Tudo fica em Despesas.util. */
var Despesas = (typeof Despesas !== 'undefined') ? Despesas : {};

Despesas.util = (function () {
  'use strict';

  // ── Bytes e cadeias «binárias» (um carácter por byte, 0–255) ────────────────────────────────
  function bytesParaBinario(bytes, inicio, fim) {
    inicio = inicio || 0;
    fim = (fim === undefined) ? bytes.length : fim;
    var partes = [], PASSO = 8192;
    for (var i = inicio; i < fim; i += PASSO) {
      partes.push(String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + PASSO, fim))));
    }
    return partes.join('');
  }

  function binarioParaBytes(s) {
    var b = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) b[i] = s.charCodeAt(i) & 0xff;
    return b;
  }

  // ── Base64 (sem atob: o jsc antigo não o tem e queremos o mesmo código nos dois lados) ─────────
  var B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var B64_INV = (function () {
    var t = new Int16Array(256);
    for (var i = 0; i < 256; i++) t[i] = -1;
    for (var j = 0; j < 64; j++) t[B64.charCodeAt(j)] = j;
    t['-'.charCodeAt(0)] = 62; t['_'.charCodeAt(0)] = 63; // base64url
    return t;
  })();

  function base64ParaBytes(s) {
    var saida = new Uint8Array(Math.floor(s.length * 3 / 4) + 3), n = 0, acc = 0, bits = 0;
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c === 61) break; // '='
      var v = c < 256 ? B64_INV[c] : -1;
      if (v < 0) continue; // espaços, quebras de linha, lixo
      acc = (acc << 6) | v; bits += 6;
      if (bits >= 8) { bits -= 8; saida[n++] = (acc >> bits) & 0xff; }
    }
    return saida.subarray(0, n);
  }

  function bytesParaBase64(b) {
    var s = '', i;
    for (i = 0; i + 2 < b.length; i += 3) {
      var v = (b[i] << 16) | (b[i + 1] << 8) | b[i + 2];
      s += B64[v >> 18] + B64[(v >> 12) & 63] + B64[(v >> 6) & 63] + B64[v & 63];
    }
    if (i < b.length) {
      var r = b.length - i, w = (b[i] << 16) | (r > 1 ? b[i + 1] << 8 : 0);
      s += B64[w >> 18] + B64[(w >> 12) & 63] + (r > 1 ? B64[(w >> 6) & 63] : '=') + '=';
    }
    return s;
  }

  // ── Descodificar texto ───────────────────────────────────────────────────────────────────────
  function utf8ParaTexto(bytes) {
    var s = '', i = 0, n = bytes.length;
    while (i < n) {
      var c = bytes[i++];
      if (c < 0x80) { s += String.fromCharCode(c); continue; }
      var extra = 0, cp = 0;
      if (c >= 0xc2 && c < 0xe0) { extra = 1; cp = c & 0x1f; }
      else if (c >= 0xe0 && c < 0xf0) { extra = 2; cp = c & 0x0f; }
      else if (c >= 0xf0 && c < 0xf5) { extra = 3; cp = c & 0x07; }
      else { s += '�'; continue; }
      if (i + extra > n) { s += '�'; break; }
      var ok = true;
      for (var k = 0; k < extra; k++) {
        var cc = bytes[i + k];
        if ((cc & 0xc0) !== 0x80) { ok = false; break; }
        cp = (cp << 6) | (cc & 0x3f);
      }
      if (!ok) { s += '�'; continue; }
      i += extra;
      s += String.fromCodePoint(cp);
    }
    return s;
  }

  function textoParaUtf8(texto) {
    var saida = [];
    for (var i = 0; i < texto.length; i++) {
      var cp = texto.codePointAt(i);
      if (cp > 0xffff) i++;
      if (cp < 0x80) saida.push(cp);
      else if (cp < 0x800) saida.push(0xc0 | (cp >> 6), 0x80 | (cp & 63));
      else if (cp < 0x10000) saida.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
      else saida.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
    }
    return new Uint8Array(saida);
  }

  // UTF-16BE (cadeias do PDF com BOM FE FF e destinos dos CMaps), a partir de uma cadeia binária.
  function utf16beParaTexto(bin) {
    var s = '';
    for (var i = 0; i + 1 < bin.length; i += 2) s += String.fromCharCode((bin.charCodeAt(i) << 8) | bin.charCodeAt(i + 1));
    return s;
  }

  // Windows-1252: 0x80–0x9F têm o €, as aspas curvas, os travessões…; o resto é Latin-1.
  var CP1252_ALTO = [0x20ac, 0xfffd, 0x201a, 0x0192, 0x201e, 0x2026, 0x2020, 0x2021, 0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0xfffd, 0x017d, 0xfffd,
    0xfffd, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014, 0x02dc, 0x2122, 0x0161, 0x203a, 0x0153, 0xfffd, 0x017e, 0x0178];
  function cp1252Carater(byte) {
    if (byte >= 0x80 && byte < 0xa0) return String.fromCharCode(CP1252_ALTO[byte - 0x80]);
    return String.fromCharCode(byte);
  }
  function cp1252ParaTexto(bin) {
    var s = '';
    for (var i = 0; i < bin.length; i++) s += cp1252Carater(bin.charCodeAt(i) & 0xff);
    return s;
  }

  // Charset de um email (utf-8, iso-8859-1, windows-1252, us-ascii…) a partir de uma cadeia binária.
  function descodificarCharset(bin, charset) {
    charset = (charset || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (charset === 'utf8' || charset === '') {
      var t = utf8ParaTexto(binarioParaBytes(bin));
      if (charset === '' && t.indexOf('�') >= 0) return cp1252ParaTexto(bin); // sem charset e não é UTF-8
      return t;
    }
    if (charset === 'utf16be' || charset === 'utf16') return utf16beParaTexto(bin);
    return cp1252ParaTexto(bin); // iso-8859-1/15, windows-1252, us-ascii
  }

  // ── SHA-256 (para reconhecer o mesmo PDF recebido duas vezes) ────────────────────────────────
  var K256 = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70,
    0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];

  function sha256(bytes) {
    var n = bytes.length, totalBlocos = ((n + 9 + 63) >> 6);
    var m = new Uint8Array(totalBlocos * 64);
    m.set(bytes);
    m[n] = 0x80;
    var bitsAlto = Math.floor(n / 0x20000000), bitsBaixo = (n << 3) >>> 0;
    var fim = m.length;
    m[fim - 8] = (bitsAlto >>> 24) & 0xff; m[fim - 7] = (bitsAlto >>> 16) & 0xff; m[fim - 6] = (bitsAlto >>> 8) & 0xff; m[fim - 5] = bitsAlto & 0xff;
    m[fim - 4] = (bitsBaixo >>> 24) & 0xff; m[fim - 3] = (bitsBaixo >>> 16) & 0xff; m[fim - 2] = (bitsBaixo >>> 8) & 0xff; m[fim - 1] = bitsBaixo & 0xff;
    var h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var w = new Array(64);
    for (var bloco = 0; bloco < totalBlocos; bloco++) {
      var o = bloco * 64, t;
      for (t = 0; t < 16; t++) w[t] = ((m[o + 4 * t] << 24) | (m[o + 4 * t + 1] << 16) | (m[o + 4 * t + 2] << 8) | m[o + 4 * t + 3]) | 0;
      for (t = 16; t < 64; t++) {
        var x = w[t - 15], y = w[t - 2];
        var s0 = ((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3);
        var s1 = ((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10);
        w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
      }
      var a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
      for (t = 0; t < 64; t++) {
        var S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
        var ch = (e & f) ^ (~e & g);
        var t1 = (hh + S1 + ch + K256[t] + w[t]) | 0;
        var S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + maj) | 0;
        hh = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0;
      h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
    }
    var hex = '';
    for (var i = 0; i < 8; i++) hex += ('00000000' + (h[i] >>> 0).toString(16)).slice(-8);
    return hex;
  }

  // ── Inflate (FlateDecode dos PDFs): o algoritmo do «puff» de Mark Adler, simples e completo ────
  var L_BASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258];
  var L_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0];
  var D_BASE = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193,
    12289, 16385, 24577];
  var D_EXTRA = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13];
  var ORDEM_CL = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];

  function huffman(comprimentos, n) {
    var count = new Uint16Array(16), symbol = new Uint16Array(n), offs = new Uint16Array(16), s, len;
    for (s = 0; s < n; s++) count[comprimentos[s]]++;
    offs[1] = 0;
    for (len = 1; len < 15; len++) offs[len + 1] = offs[len] + count[len];
    for (s = 0; s < n; s++) if (comprimentos[s] !== 0) symbol[offs[comprimentos[s]]++] = s;
    return { count: count, symbol: symbol };
  }

  var FIXO = null;
  function tabelasFixas() {
    if (FIXO) return FIXO;
    var l = new Uint8Array(288), s;
    for (s = 0; s < 144; s++) l[s] = 8;
    for (; s < 256; s++) l[s] = 9;
    for (; s < 280; s++) l[s] = 7;
    for (; s < 288; s++) l[s] = 8;
    var d = new Uint8Array(30);
    for (s = 0; s < 30; s++) d[s] = 5;
    FIXO = { comp: huffman(l, 288), dist: huffman(d, 30) };
    return FIXO;
  }

  function inflateBruto(dados, inicio) {
    var pos = inicio, bitbuf = 0, bitcnt = 0;
    var saida = new Uint8Array(Math.max(1024, dados.length * 4)), n = 0;

    function garantir(extra) {
      if (n + extra <= saida.length) return;
      var nova = new Uint8Array(Math.max(saida.length * 2, n + extra + 1024));
      nova.set(saida.subarray(0, n));
      saida = nova;
    }
    function bits(k) {
      while (bitcnt < k) {
        if (pos >= dados.length) throw new Error('fim dos dados');
        bitbuf |= dados[pos++] << bitcnt;
        bitcnt += 8;
      }
      var v = bitbuf & ((1 << k) - 1);
      bitbuf >>>= k;
      bitcnt -= k;
      return v;
    }
    function decodificar(h) {
      var code = 0, first = 0, index = 0;
      for (var len = 1; len <= 15; len++) {
        code |= bits(1);
        var count = h.count[len];
        if (code - count < first) return h.symbol[index + (code - first)];
        index += count;
        first += count;
        first <<= 1;
        code <<= 1;
      }
      throw new Error('código Huffman inválido');
    }
    function codigos(lc, dc) {
      for (;;) {
        var sym = decodificar(lc);
        if (sym < 256) { garantir(1); saida[n++] = sym; continue; }
        if (sym === 256) return;
        sym -= 257;
        if (sym >= 29) throw new Error('comprimento inválido');
        var len = L_BASE[sym] + bits(L_EXTRA[sym]);
        var ds = decodificar(dc);
        if (ds >= 30) throw new Error('distância inválida');
        var dist = D_BASE[ds] + bits(D_EXTRA[ds]);
        if (dist > n) throw new Error('distância antes do início');
        garantir(len);
        for (var k = 0; k < len; k++) { saida[n] = saida[n - dist]; n++; }
      }
    }

    var ultimo = 0;
    try {
      do {
        ultimo = bits(1);
        var tipo = bits(2);
        if (tipo === 0) {
          bitbuf = 0; bitcnt = 0;
          if (pos + 4 > dados.length) throw new Error('bloco guardado truncado');
          var len = dados[pos] | (dados[pos + 1] << 8);
          pos += 4;
          var fimBloco = Math.min(pos + len, dados.length);
          garantir(fimBloco - pos);
          saida.set(dados.subarray(pos, fimBloco), n);
          n += fimBloco - pos;
          pos = fimBloco;
        } else if (tipo === 1) {
          var f = tabelasFixas();
          codigos(f.comp, f.dist);
        } else if (tipo === 2) {
          var nlen = bits(5) + 257, ndist = bits(5) + 1, ncode = bits(4) + 4, comp = new Uint8Array(320), k2;
          var cl = new Uint8Array(19);
          for (k2 = 0; k2 < ncode; k2++) cl[ORDEM_CL[k2]] = bits(3);
          var hcl = huffman(cl, 19), idx = 0;
          while (idx < nlen + ndist) {
            var sym = decodificar(hcl);
            if (sym < 16) { comp[idx++] = sym; continue; }
            var rep = 0, val = 0;
            if (sym === 16) { if (idx === 0) throw new Error('repetição sem anterior'); val = comp[idx - 1]; rep = 3 + bits(2); }
            else if (sym === 17) rep = 3 + bits(3);
            else rep = 11 + bits(7);
            if (idx + rep > nlen + ndist) throw new Error('demasiados comprimentos');
            while (rep--) comp[idx++] = val;
          }
          codigos(huffman(comp.subarray(0, nlen), nlen), huffman(comp.subarray(nlen, nlen + ndist), ndist));
        } else {
          throw new Error('tipo de bloco inválido');
        }
      } while (!ultimo);
    } catch (e) {
      // Fluxos truncados são comuns em PDFs: devolve-se o que se conseguiu descomprimir.
      if (n === 0) throw e;
    }
    return saida.subarray(0, n);
  }

  // zlib (cabeçalho de 2 bytes) ou deflate cru.
  function inflate(dados) {
    var inicio = 0;
    if (dados.length >= 2 && (dados[0] & 0x0f) === 8 && (((dados[0] << 8) | dados[1]) % 31) === 0) inicio = 2;
    return inflateBruto(dados, inicio);
  }

  // ── Texto para comparar: minúsculas sem acentos, com o MESMO comprimento (as posições batem certo) ─
  var SEM_ACENTO = {};
  (function () {
    var de = 'áàâãäåçéèêëíìîïñóòôõöúùûüýÿÁÀÂÃÄÅÇÉÈÊËÍÌÎÏÑÓÒÔÕÖÚÙÛÜÝºª ’‘“”–—';
    var para = 'aaaaaaceeeeiiiinooooouuuuyyaaaaaaceeeeiiiinooooouuuuyoa \'\'""--';
    for (var i = 0; i < de.length; i++) SEM_ACENTO[de[i]] = para[i];
  })();
  function dobrar(texto) {
    var s = '';
    for (var i = 0; i < texto.length; i++) {
      var c = texto[i];
      var r = SEM_ACENTO[c];
      s += (r !== undefined) ? r : c.toLowerCase().charAt(0) || c;
    }
    return s;
  }

  // ── Dinheiro (cêntimos inteiros) e datas (AAAA-MM-DD) ───────────────────────────────────────
  function lerValor(texto) {
    // «1.234,56», «1 234,56», «45,67», «-12,30», «45.67»; devolve cêntimos ou null.
    if (texto === null || texto === undefined) return null;
    var t = String(texto).replace(/[€\s ]|EUR/g, '');
    var negativo = /^-|-$/.test(t);
    t = t.replace(/-/g, '');
    var m = /^(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})$/.exec(t) || /^(\d+)\.(\d{2})$/.exec(t);
    if (!m) return null;
    var cent = parseInt(m[1].replace(/\./g, ''), 10) * 100 + parseInt(m[2], 10);
    return negativo ? -cent : cent;
  }

  function formatarValor(cent) {
    if (cent === null || cent === undefined || isNaN(cent)) return '—';
    var neg = cent < 0;
    cent = Math.abs(Math.round(cent));
    var inteiro = String(Math.floor(cent / 100)), dec = ('0' + (cent % 100)).slice(-2);
    inteiro = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (neg ? '-' : '') + inteiro + ',' + dec + ' €';
  }

  function dataValida(a, m, d) {
    if (m < 1 || m > 12 || d < 1 || a < 2000 || a > 2100) return false;
    var dias = [31, (a % 4 === 0 && (a % 100 !== 0 || a % 400 === 0)) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return d <= dias[m - 1];
  }
  function iso(a, m, d) { return a + '-' + ('0' + m).slice(-2) + '-' + ('0' + d).slice(-2); }

  function formatarData(isoData) {
    if (!isoData) return '—';
    var m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(isoData);
    if (!m) return isoData;
    if (!m[3]) return MESES_NOME[parseInt(m[2], 10) - 1] + ' ' + m[1];
    return m[3] + '/' + m[2] + '/' + m[1];
  }
  var MESES_NOME = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

  function escaparHtml(s) {
    return String(s === null || s === undefined ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  return {
    bytesParaBinario: bytesParaBinario, binarioParaBytes: binarioParaBytes,
    base64ParaBytes: base64ParaBytes, bytesParaBase64: bytesParaBase64,
    utf8ParaTexto: utf8ParaTexto, textoParaUtf8: textoParaUtf8, utf16beParaTexto: utf16beParaTexto,
    cp1252Carater: cp1252Carater, cp1252ParaTexto: cp1252ParaTexto, descodificarCharset: descodificarCharset,
    sha256: sha256, inflate: inflate, dobrar: dobrar,
    lerValor: lerValor, formatarValor: formatarValor, dataValida: dataValida, iso: iso, formatarData: formatarData,
    MESES_NOME: MESES_NOME, escaparHtml: escaparHtml
  };
})();
