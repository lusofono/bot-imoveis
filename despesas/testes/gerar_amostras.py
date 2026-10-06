#!/usr/bin/env python3
"""Gera as faturas fictícias (PDF) e os emails fictícios (.eml) dos testes. Só usa a biblioteca padrão.

Cada PDF usa uma técnica diferente de os PDFs reais guardarem texto, para o motor ser posto à prova:
fontes simples WinAnsi com /Widths, fontes compostas (Type0, Identity-H) com ToUnicode, «object streams» com
tabela xref em fluxo (PDF 1.5), TJ com kerning, cm com escala, XObjects de formulário, /Differences, ASCII85+Flate,
uma fatura digitalizada (só imagem) e um PDF marcado como cifrado.

Os documentos dizem em letras grandes que são FICTÍCIOS. Os nomes dos fornecedores aparecem como texto simples
(sem logótipos nem grafismo) só para pôr à prova as regras de identificação; clientes, moradas, NIF, IBAN e
referências são inventados (o IBAN usa o banco 0000, que não existe).

Correr a partir de despesas/:  python3 testes/gerar_amostras.py
"""
import base64
import json
import os
import zlib
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.join(AQUI, 'pdfs')
EMAILS = os.path.join(AQUI, 'emails')

AVISO = 'DOCUMENTO FICTÍCIO PARA TESTES — NÃO É UMA FATURA'

# Larguras da Helvetica (milésimos de em) para os caracteres usados; o resto fica a 556.
LARG = {' ': 278, '!': 278, '"': 355, '#': 556, '%': 889, '&': 667, "'": 191, '(': 333, ')': 333, '*': 389, '+': 584,
        ',': 278, '-': 333, '.': 278, '/': 278, ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015,
        'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278, 'J': 500, 'K': 667,
        'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667,
        'W': 944, 'X': 667, 'Y': 667, 'Z': 611, 'c': 500, 'f': 278, 'i': 222, 'j': 222, 'k': 500, 'l': 222, 'm': 833,
        'r': 333, 's': 500, 't': 278, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500, 'º': 365, 'ª': 370, '°': 400,
        '—': 1000, '–': 556, '«': 556, '»': 556, 'ç': 500, 'í': 278, 'Í': 278, 'Ç': 722, 'É': 667, 'Á': 667, 'Ó': 778,
        'Ú': 722, '€': 556}


def largura(texto, tam):
    return sum(LARG.get(c, 556) for c in texto) * tam / 1000.0


def iban_ficticio(corpo19):
    """IBAN português (PT50 + 21 dígitos) com os dois últimos dígitos calculados para passar o módulo 97."""
    for cc in range(100):
        bban = corpo19 + '%02d' % cc
        numero = int(bban + '2529' + '50')  # P=25, T=29
        if numero % 97 == 1:
            return 'PT50' + bban
    raise ValueError('sem IBAN')


def agrupar(iban):
    return ' '.join(iban[i:i + 4] for i in range(0, len(iban), 4))


IBAN_FORN = agrupar(iban_ficticio('0000' + '0000' + '12345678901'))


# ── Construtor de PDFs ────────────────────────────────────────────────────────────────────────────
class PDF:
    def __init__(self, versao='1.4'):
        self.versao = versao
        self.objs = {}     # num → bytes (corpo, sem «n 0 obj»)
        self.n = 0

    def reservar(self):
        self.n += 1
        return self.n

    def por(self, num, corpo):
        self.objs[num] = corpo.encode('latin-1') if isinstance(corpo, str) else corpo

    def novo(self, corpo):
        num = self.reservar()
        self.por(num, corpo)
        return num

    def fluxo(self, dic, dados, filtro=None, num=None):
        if filtro == 'flate':
            dados = zlib.compress(dados)
            dic += ' /Filter /FlateDecode'
        elif filtro == 'a85flate':
            dados = base64.a85encode(zlib.compress(dados), adobe=True)[2:]  # sem o «<~» inicial (o PDF só usa o «~>» final)
            dic += ' /Filter [/ASCII85Decode /FlateDecode]'
        corpo = ('<< %s /Length %d >>\nstream\n' % (dic, len(dados))).encode('latin-1') + dados + b'\nendstream'
        if num is None:
            return self.novo(corpo)
        self.por(num, corpo)
        return num

    def escrever(self, caminho, raiz, extra_trailer='', comprimir=()):
        """comprimir: números de objetos (sem fluxo) a pôr num ObjStm, com xref em fluxo."""
        saida = bytearray(('%%PDF-%s\n' % self.versao).encode('latin-1') + b'%\xe2\xe3\xcf\xd3\n')
        posicoes = {}
        comprimidos = [k for k in comprimir if k in self.objs]
        objstm = None
        if comprimidos:
            cab, corpo = [], bytearray()
            for k in comprimidos:
                cab.append('%d %d' % (k, len(corpo)))
                corpo += self.objs[k] + b'\n'
            cabecalho = (' '.join(cab) + '\n').encode('latin-1')
            dados = zlib.compress(cabecalho + bytes(corpo))
            objstm = self.reservar()
            self.objs[objstm] = ('<< /Type /ObjStm /N %d /First %d /Filter /FlateDecode /Length %d >>\nstream\n'
                                 % (len(comprimidos), len(cabecalho), len(dados))).encode('latin-1') + dados + b'\nendstream'
        for k in sorted(self.objs):
            if k in comprimidos:
                continue
            posicoes[k] = len(saida)
            saida += ('%d 0 obj\n' % k).encode('latin-1') + self.objs[k] + b'\nendobj\n'
        if objstm is None:
            xref = len(saida)
            total = self.n + 1
            saida += ('xref\n0 %d\n0000000000 65535 f \n' % total).encode('latin-1')
            for k in range(1, total):
                saida += ('%010d 00000 n \n' % posicoes.get(k, 0)).encode('latin-1')
            saida += ('trailer\n<< /Size %d /Root %d 0 R %s>>\nstartxref\n%d\n%%%%EOF\n' % (total, raiz, extra_trailer, xref)).encode('latin-1')
        else:
            num_xref = self.reservar()
            total = self.n + 1
            linhas = bytearray()
            for k in range(total):
                if k == 0:
                    linhas += bytes([0]) + (0).to_bytes(4, 'big') + (65535).to_bytes(2, 'big')
                elif k in comprimidos:
                    linhas += bytes([2]) + objstm.to_bytes(4, 'big') + comprimidos.index(k).to_bytes(2, 'big')
                elif k == num_xref:
                    linhas += bytes([1]) + len(saida).to_bytes(4, 'big') + (0).to_bytes(2, 'big')
                else:
                    linhas += bytes([1]) + posicoes.get(k, 0).to_bytes(4, 'big') + (0).to_bytes(2, 'big')
            dados = zlib.compress(bytes(linhas))
            xref = len(saida)
            saida += ('%d 0 obj\n<< /Type /XRef /Size %d /W [1 4 2] /Root %d 0 R %s/Filter /FlateDecode /Length %d >>\nstream\n'
                      % (num_xref, total, raiz, extra_trailer, len(dados))).encode('latin-1') + dados + b'\nendstream\nendobj\n'
            saida += ('startxref\n%d\n%%%%EOF\n' % xref).encode('latin-1')
        with open(caminho, 'wb') as f:
            f.write(bytes(saida))


def literal(texto, codificacao='cp1252'):
    b = texto.encode(codificacao)
    out = []
    for byte in b:
        c = chr(byte)
        if c in '\\()':
            out.append('\\' + c)
        elif byte < 32 or byte > 126:
            out.append('\\%03o' % byte)
        else:
            out.append(c)
    return '(' + ''.join(out) + ')'


def fonte_helvetica(pdf, nome='Helvetica', diferencas=None):
    larguras = ' '.join(str(LARG.get(bytes([c]).decode('cp1252', 'replace'), 556)) for c in range(32, 256))
    enc = '/WinAnsiEncoding'
    if diferencas:
        enc = '<< /Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [%s] >>' % diferencas
    return pdf.novo('<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding %s /FirstChar 32 /LastChar 255 /Widths [%s] >>'
                    % (nome, enc, larguras))


def paginas(pdf, conteudos, recursos, comprimir_conteudo=None, extra_pagina=''):
    raiz, arvore = pdf.reservar(), pdf.reservar()
    kids = []
    for conteudo in conteudos:
        c = pdf.fluxo('', conteudo.encode('latin-1'), comprimir_conteudo)
        kids.append(pdf.novo('<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Contents %d 0 R %s>>' % (arvore, c, extra_pagina)))
    pdf.por(arvore, '<< /Type /Pages /Kids [%s] /Count %d /Resources %s >>' % (' '.join('%d 0 R' % k for k in kids), len(kids), recursos))
    pdf.por(raiz, '<< /Type /Catalog /Pages %d 0 R >>' % arvore)
    return raiz


def linha_valor(x_dir, y, texto, tam, fonte='/F1'):
    """Texto alinhado à direita em x_dir (como os valores nas faturas)."""
    return 'BT %s %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (fonte, tam, x_dir - largura(texto, tam), y, literal(texto))


def txt(x, y, texto, tam, fonte='/F1'):
    return 'BT %s %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (fonte, tam, x, y, literal(texto))


# ── 1. Água (EPAL): Helvetica WinAnsi, conteúdo sem compressão, Td relativos ──────────────────────
def epal_agua(caminho, com_total=True):
    pdf = PDF()
    f1 = fonte_helvetica(pdf)
    f2 = fonte_helvetica(pdf, 'Helvetica-Bold')
    c = []
    c.append(txt(40, 800, AVISO, 9, '/F2'))
    c.append('BT /F2 16 Tf 40 760 Td (EPAL) Tj 0 -16 Td /F1 9 Tf %s Tj ET\n' % literal('Empresa Portuguesa das Águas Livres (exemplo)'))
    c.append('BT /F1 10 Tf 40 700 Td %s Tj 0 -14 Td %s Tj 0 -14 Td %s Tj ET\n'
             % (literal('Cliente: Cliente Exemplo Um'), literal('Local de consumo: Rua do Exemplo, 1 — 1000-000 Lisboa'),
                literal('Nº de cliente: 9900112233')))
    c.append(txt(40, 640, 'Fatura FT 2026/123456', 11, '/F2'))
    c.append(txt(40, 620, 'Período de faturação: 01/08/2026 a 31/08/2026', 10))
    c.append(txt(40, 590, 'Água — consumo de 7 m³', 10))
    c.append(linha_valor(550, 590, '21,30 €', 10))
    c.append(txt(40, 575, 'Saneamento e resíduos', 10))
    c.append(linha_valor(550, 575, '14,99 €', 10))
    c.append(txt(40, 560, 'IVA 6,00 %', 10))
    c.append(linha_valor(550, 560, '2,18 €', 10))
    if com_total:
        c.append(txt(40, 530, 'Total a pagar', 12, '/F2'))
        c.append(linha_valor(550, 530, '38,47 €', 12, '/F2'))
    c.append(txt(40, 500, 'Data limite de pagamento: 25/09/2026', 10))
    c.append(txt(40, 470, 'Pagamento por Multibanco', 10, '/F2'))
    c.append(txt(40, 455, 'Entidade: 12345   Referência: 123 456 789   Montante: 38,47 €', 10))
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R /F2 %d 0 R >> >>' % (f1, f2))
    pdf.escrever(caminho, raiz)


# ── 2. Eletricidade (EDP): Type0 Identity-H + ToUnicode, ObjStm + xref em fluxo, 2 páginas ─────────
class FonteComposta:
    def __init__(self):
        self.cids = {}

    def cid(self, ch):
        if ch not in self.cids:
            self.cids[ch] = 3 + len(self.cids)
        return self.cids[ch]

    def hexa(self, texto):
        return '<' + ''.join('%04X' % self.cid(ch) for ch in texto) + '>'

    def tounicode(self):
        itens = sorted((cid, ch) for ch, cid in self.cids.items())
        # metade em bfrange (sequências), o resto em bfchar
        ranges, chars = [], []
        i = 0
        while i < len(itens):
            j = i
            while j + 1 < len(itens) and itens[j + 1][0] == itens[j][0] + 1 and ord(itens[j + 1][1]) == ord(itens[j][1]) + 1:
                j += 1
            if j > i:
                ranges.append('<%04X> <%04X> <%04X>' % (itens[i][0], itens[j][0], ord(itens[i][1])))
            else:
                chars.append('<%04X> <%s>' % (itens[i][0], itens[i][1].encode('utf-16-be').hex().upper()))
            i = j + 1
        partes = ['/CIDInit /ProcSet findresource begin', '12 dict begin', 'begincmap',
                  '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def',
                  '/CMapName /Adobe-Identity-UCS def', '/CMapType 2 def',
                  '1 begincodespacerange', '<0000> <FFFF>', 'endcodespacerange']
        if chars:
            partes += ['%d beginbfchar' % len(chars)] + chars + ['endbfchar']
        if ranges:
            partes += ['%d beginbfrange' % len(ranges)] + ranges + ['endbfrange']
        partes += ['endcmap', 'CMapName currentdict /CMap defineresource pop', 'end', 'end']
        return '\n'.join(partes)

    def larguras(self):
        itens = sorted((cid, ch) for ch, cid in self.cids.items())
        return '[%d [%s]]' % (itens[0][0], ' '.join(str(LARG.get(ch, 556)) for _, ch in itens)) if itens else '[]'


def edp_eletricidade(caminho):
    pdf = PDF('1.5')
    fc = FonteComposta()
    # Página 1
    p1 = []
    def t(x, y, texto, tam):
        p1.append('BT /C1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, x, y, fc.hexa(texto)))
    def v(xd, y, texto, tam):
        p1.append('BT /C1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, xd - largura(texto, tam), y, fc.hexa(texto)))
    t(40, 800, AVISO, 9)
    t(40, 760, 'EDP Comercial — Comercialização de Energia, S.A. (exemplo)', 11)
    t(40, 720, 'Fatura de eletricidade', 14)
    t(40, 700, 'Cliente Exemplo Dois', 10)
    t(40, 686, 'CPE: PT 0002 0000 1234 5678 XY', 10)
    t(40, 672, 'Período de faturação 05/08/2026 a 04/09/2026', 10)
    t(40, 640, 'Energia ativa 180 kWh', 10)
    v(550, 640, '41,20 €', 10)
    t(40, 625, 'Potência contratada 6,90 kVA', 10)
    v(550, 625, '11,31 €', 10)
    t(40, 610, 'Taxas e IVA 23 %', 10)
    v(550, 610, '11,61 €', 10)
    t(40, 580, 'Valor a pagar', 12)
    v(550, 580, '64,12 €', 12)
    t(40, 550, 'Data limite de pagamento', 10)       # rótulo por cima do valor
    t(40, 536, '28/09/2026', 10)
    # Página 2
    p2 = []
    def t2(x, y, texto, tam):
        p2.append('BT /C1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, x, y, fc.hexa(texto)))
    t2(40, 800, AVISO, 9)
    t2(40, 760, 'Formas de pagamento', 12)
    t2(40, 740, 'Multibanco — Entidade 54321 Referência 987 654 321', 10)
    t2(40, 726, 'Montante 64,12 €', 10)
    raiz_n, arvore = pdf.reservar(), pdf.reservar()
    cmap = pdf.fluxo('', fc.tounicode().encode('latin-1'), 'flate')
    desc_fd = pdf.novo('<< /Type /FontDescriptor /FontName /ExemploSans /Flags 32 /FontBBox [-166 -225 1000 931] /ItalicAngle 0 '
                       '/Ascent 718 /Descent -207 /CapHeight 718 /StemV 88 >>')
    cid = pdf.novo('<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ExemploSans /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) '
                   '/Supplement 0 >> /FontDescriptor %d 0 R /DW 556 /W %s /CIDToGIDMap /Identity >>' % (desc_fd, fc.larguras()))
    f0 = pdf.novo('<< /Type /Font /Subtype /Type0 /BaseFont /ExemploSans /Encoding /Identity-H /DescendantFonts [%d 0 R] /ToUnicode %d 0 R >>'
                  % (cid, cmap))
    recursos = pdf.novo('<< /Font << /C1 %d 0 R >> >>' % f0)
    kids = []
    for conteudo in (''.join(p1), ''.join(p2)):
        cc = pdf.fluxo('', conteudo.encode('latin-1'), 'flate')
        kids.append(pdf.novo('<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Contents %d 0 R /Resources %d 0 R >>' % (arvore, cc, recursos)))
    pdf.por(arvore, '<< /Type /Pages /Kids [%s] /Count 2 >>' % ' '.join('%d 0 R' % k for k in kids))
    pdf.por(raiz_n, '<< /Type /Catalog /Pages %d 0 R >>' % arvore)
    pdf.escrever(caminho, raiz_n, comprimir=[raiz_n, arvore, desc_fd, cid, f0, recursos] + kids)


# ── 3. Internet (MEO): TJ com kerning, cm com escala, cabeçalho num XObject, débito direto ────────
def tj_kerning(texto, tam):
    """Parte o texto em sílabas com kerning pequeno; os espaços viram kerning grande (sem carácter de espaço)."""
    partes = []
    for i, palavra in enumerate(texto.split(' ')):
        if i:
            partes.append('-300')
        for k in range(0, len(palavra), 3):
            if k:
                partes.append('12')
            partes.append(literal(palavra[k:k + 3]))
    return '[%s] TJ' % ' '.join(partes)


def meo_internet(caminho):
    pdf = PDF()
    f1 = fonte_helvetica(pdf)
    cab = 'BT /F1 9 Tf 40 800 Td %s Tj ET\nBT /F1 14 Tf 40 770 Td %s Tj ET\nBT /F1 9 Tf 40 756 Td %s Tj ET\n' % (
        literal(AVISO), literal('MEO'), literal('MEO - Serviços de Comunicações e Multimédia, S.A. (exemplo)'))
    xo = pdf.fluxo('/Type /XObject /Subtype /Form /BBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >>' % f1,
                   cab.encode('latin-1'), 'flate')
    c = ['q /Cab Do Q\n', 'q 0.5 0 0 0.5 0 0 cm\n']  # tudo o resto desenhado a metade da escala, com letras do dobro
    def t(x, y, texto, tam):
        c.append('BT /F1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s ET\n' % (tam * 2, x * 2, y * 2, tj_kerning(texto, tam * 2)))
    def v(xd, y, texto, tam):
        c.append('BT /F1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam * 2, (xd - largura(texto, tam)) * 2, y * 2, literal(texto)))
    t(40, 720, 'Fatura de serviços de telecomunicações', 12)
    t(40, 700, 'Cliente Exemplo Três', 10)
    t(40, 686, 'Conta de cliente 5566778899', 10)
    t(40, 672, 'Período de faturação 01/09/2026 a 30/09/2026', 10)
    t(40, 640, 'Pacote Fibra (exemplo)', 10)
    v(550, 640, '41,99 €', 10)
    t(40, 610, 'Total a pagar', 12)
    v(550, 610, '41,99 €', 12)
    t(40, 580, 'Data limite de pagamento 20/09/2026', 10)
    t(40, 560, 'Pagamento por Débito Direto na conta indicada pelo cliente', 10)
    c.append('Q\n')
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R >> /XObject << /Cab %d 0 R >> >>' % (f1, xo), 'flate')
    pdf.escrever(caminho, raiz)


# ── 4. Aquecimento (Climaespaço): /Differences com códigos próprios, ASCII85+Flate, transferência ──
DIF = {'ç': 1, 'ã': 2, 'í': 3, 'é': 4, 'õ': 5, '€': 6, 'á': 7, 'ó': 8, 'ê': 9, 'ú': 10}
NOMES_DIF = {'ç': 'ccedilla', 'ã': 'atilde', 'í': 'iacute', 'é': 'eacute', 'õ': 'otilde', '€': 'Euro', 'á': 'aacute',
             'ó': 'oacute', 'ê': 'ecircumflex', 'ú': 'uacute'}


def literal_dif(texto):
    out = []
    for ch in texto:
        if ch in DIF:
            out.append('\\%03o' % DIF[ch])
        elif ch in '\\()':
            out.append('\\' + ch)
        else:
            b = ch.encode('cp1252')[0]
            out.append(ch if 32 <= b <= 126 else '\\%03o' % b)
    return '(' + ''.join(out) + ')'


def climaespaco_aquecimento(caminho):
    pdf = PDF()
    dif = ' '.join('%d /%s' % (DIF[ch], NOMES_DIF[ch]) for ch in sorted(DIF, key=DIF.get))
    f1 = fonte_helvetica(pdf, 'Helvetica', dif)
    c = []
    def t(x, y, texto, tam):
        c.append('BT /F1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, x, y, literal_dif(texto)))
    def v(xd, y, texto, tam):
        c.append('BT /F1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, xd - largura(texto, tam), y, literal_dif(texto)))
    t(40, 800, AVISO, 9)
    t(40, 770, 'Climaespaço — Sistema de distribuição de calor e frio (exemplo)', 11)
    t(40, 740, 'Fatura de energia térmica (aquecimento)', 13)
    t(40, 720, 'Cliente Exemplo Um — Nº de contrato CT-000777', 10)
    t(40, 700, 'Período de 01/08/2026 a 31/08/2026', 10)
    t(40, 670, 'Energia térmica — calor', 10)
    v(550, 670, '25,78 €', 10)
    t(40, 655, 'IVA 6 %', 10)
    v(550, 655, '1,55 €', 10)
    t(40, 625, 'Total a pagar', 12)
    v(550, 625, '27,33 €', 12)
    t(40, 600, 'Data limite: 15/10/2026', 10)
    t(40, 575, 'Pagamento por transferência bancária para o IBAN %s' % IBAN_FORN, 10)
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R >> >>' % f1, 'a85flate')
    pdf.escrever(caminho, raiz)


# ── 5. Internet (NOS): TL + T* + ' e Tw, rótulo «Pagar até», período por extenso ─────────────────
def nos_internet(caminho):
    pdf = PDF()
    f1 = fonte_helvetica(pdf)
    c = ['BT /F1 9 Tf 14 TL 40 800 Td %s Tj ET\n' % literal(AVISO)]
    c.append('BT /F1 10 Tf 14 TL 2 Tw 40 760 Td %s Tj T* %s Tj %s \' %s \' ET\n' % (
        literal('NOS Comunicações, S.A. (exemplo)'), literal('Fatura mensal de setembro de 2026'),
        literal('Cliente Exemplo Dois — Nº de cliente 1122334455'), literal('Período de 15/08/2026 a 14/09/2026')))
    c.append(txt(40, 680, 'Serviço de internet (exemplo)', 10))
    c.append(linha_valor(550, 680, '35,99 €', 10))
    c.append(txt(40, 650, 'Valor a pagar', 12))
    c.append(linha_valor(550, 650, '35,99 €', 12))
    c.append(txt(40, 620, 'Pagar até 30/09/2026', 10))
    c.append(txt(40, 600, 'Referência Multibanco: Entidade 11111 Ref. 222 333 444', 10))
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R >> >>' % f1, 'flate')
    pdf.escrever(caminho, raiz)


# ── 5b. Luz com fonte MacRoman, texto rodado na margem, convite ao débito direto e Multibanco em colunas ──
def literal_mac(texto):
    out = []
    for byte in texto.encode('mac_roman'):
        c = chr(byte)
        if c in '\\()':
            out.append('\\' + c)
        elif byte < 32 or byte > 126:
            out.append('\\%03o' % byte)
        else:
            out.append(c)
    return '(' + ''.join(out) + ')'


def su_luz_macroman(caminho):
    pdf = PDF()
    larguras = ' '.join(str(LARG.get(bytes([c]).decode('mac_roman'), 556)) for c in range(32, 256))
    f1 = pdf.novo('<< /Type /Font /Subtype /TrueType /BaseFont /ArialMT /Encoding /MacRomanEncoding /FirstChar 32 /LastChar 255 /Widths [%s] >>' % larguras)
    c = []
    def t(x, y, texto, tam=10):
        c.append('BT /F1 %.1f Tf 1 0 0 1 %.2f %.2f Tm %s Tj ET\n' % (tam, x, y, literal_mac(texto)))
    t(40, 800, AVISO, 9)
    t(40, 780, 'Página 1 de 2')
    t(40, 765, 'sueletricidade.pt (exemplo)')
    t(40, 740, 'Documento nº: 000000000001')
    t(40, 725, 'Período de faturação: 13 jun 2026 até 12 jul 2026')
    t(40, 700, 'Valor da fatura')
    t(40, 686, '20,00 €   +   5,00 €   +   1,00 €   26,00 €')
    t(40, 672, 'Eletricidade   Taxas, Impostos e   Juros   pague até')
    t(300, 658, '1 agosto 2026')
    t(40, 630, 'Potência contratada: 6,9 kVA   Consumo 95 kWh')
    t(40, 600, 'Adira ao débito direto')
    for i, (rot, val) in enumerate([('ENTIDADE', '11111'), ('REFERÊNCIA', '222 333 444'), ('MONTANTE', '26,00 €')]):
        t(300, 600 - i * 28, rot)
        t(300, 586 - i * 28, val)
    # texto da margem, rodado 90°, uma letra de cada vez (como nas faturas verdadeiras)
    margem = 'PROCESSADO POR COMPUTADOR - SU ELETRICIDADE (exemplo) - Sede: Rua Fictícia, 1'
    y = 120.0
    for ch in margem:
        c.append('BT /F1 7 Tf 0 1 -1 0 20 %.2f Tm %s Tj ET\n' % (y, literal_mac(ch)))
        y += largura(ch, 7)
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R >> >>' % f1, 'flate')
    pdf.escrever(caminho, raiz)


# ── 6. Fatura de outro tipo (ginásio): fornecedor desconhecido ────────────────────────────────────
def ginasio_outro(caminho):
    pdf = PDF()
    f1 = fonte_helvetica(pdf)
    c = [txt(40, 800, AVISO, 9), txt(40, 760, 'Ginásio Exemplo, Lda.', 14), txt(40, 730, 'Mensalidade de setembro de 2026', 10),
         txt(40, 700, 'Total a pagar', 12), linha_valor(550, 700, '30,00 €', 12), txt(40, 670, 'Data limite: 10/09/2026', 10)]
    raiz = paginas(pdf, [''.join(c)], '<< /Font << /F1 %d 0 R >> >>' % f1, 'flate')
    pdf.escrever(caminho, raiz)


# ── 7. Digitalizada: só uma imagem, sem texto ────────────────────────────────────────────────────
def digitalizada(caminho):
    pdf = PDF()
    larg, alt = 60, 80
    pixels = bytes((200 if (x // 6 + y // 6) % 2 else 240) for y in range(alt) for x in range(larg))
    img = pdf.fluxo('/Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray /BitsPerComponent 8' % (larg, alt),
                    pixels, 'flate')
    raiz = paginas(pdf, ['q 500 0 0 700 40 60 cm /Im1 Do Q\n'], '<< /XObject << /Im1 %d 0 R >> >>' % img, 'flate')
    pdf.escrever(caminho, raiz)


# ── 8. Marcado como cifrado (não é cifra a sério: só para o aviso) ───────────────────────────────
def protegido(caminho):
    pdf = PDF()
    f1 = fonte_helvetica(pdf)
    enc = pdf.novo('<< /Filter /Standard /V 2 /R 3 /Length 128 /O (xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx) /U (xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx) /P -4 >>')
    raiz = paginas(pdf, [txt(40, 800, AVISO, 9)], '<< /Font << /F1 %d 0 R >> >>' % f1)
    pdf.escrever(caminho, raiz, extra_trailer='/Encrypt %d 0 R /ID [<00112233445566778899AABBCCDDEEFF> <00112233445566778899AABBCCDDEEFF>] ' % enc)


# ── Emails fictícios (para os testes do PHP no servidor) ─────────────────────────────────────────
def emails():
    data = format_datetime(datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc))
    with open(os.path.join(PDFS, 'epal_agua.pdf'), 'rb') as f:
        pdf_epal = f.read()
    with open(os.path.join(PDFS, 'meo_internet.pdf'), 'rb') as f:
        pdf_meo = f.read()

    m = EmailMessage()
    m['From'] = 'Proprietário Exemplo <proprietario1@example.com>'
    m['To'] = 'contas@example.com'
    m['Subject'] = 'Fwd: Fatura da água de agosto'
    m['Date'] = data
    m['Message-ID'] = '<exemplo-1@example.com>'
    m.set_content('Segue a fatura da água.\n\n---------- Forwarded message ---------\nDe: faturas@example.com\n')
    m.add_attachment(pdf_epal, maintype='application', subtype='pdf', filename='fatura água agosto.pdf')
    m.set_boundary('====exemplo-1====')
    with open(os.path.join(EMAILS, 'reencaminhado_com_pdf.eml'), 'wb') as f:
        f.write(bytes(m))

    interior = EmailMessage()
    interior['From'] = 'Fornecedor Exemplo <faturas@example.com>'
    interior['To'] = 'proprietario2@example.com'
    interior['Subject'] = 'A sua fatura'
    interior['Date'] = data
    interior.set_content('Em anexo a sua fatura.')
    interior.add_attachment(pdf_meo, maintype='application', subtype='octet-stream', filename='Fatura_Setembro.PDF')
    exterior = EmailMessage()
    exterior['From'] = '"Outra Proprietária" <Proprietario2@Example.com>'
    exterior['To'] = 'contas@example.com'
    exterior['Subject'] = '=?utf-8?q?Fatura_da_internet_=E2=80=94_setembro?='
    exterior['Date'] = data
    exterior.set_content('Reencaminho como anexo.')
    interior.set_boundary('====exemplo-interior====')
    exterior.add_attachment(interior)
    exterior.set_boundary('====exemplo-2====')
    with open(os.path.join(EMAILS, 'anexo_rfc822.eml'), 'wb') as f:
        f.write(bytes(exterior))

    resp = EmailMessage()
    resp['From'] = 'Inquilina Exemplo <inquilina@example.com>'
    resp['To'] = 'contas@example.com'
    resp['Subject'] = 'Re: Despesas — T2 Exemplo — Edifício Fictício (outubro 2026)'
    resp['Date'] = data
    resp.set_content('Sim, já paguei hoje. Segue o comprovativo.\n\nEm seg., 6/10/2026, Gestão de Contas escreveu:\n> Olá Inquilina,\n> Seguem as despesas do apartamento.\n')
    jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + b'COMPROVATIVO FICTICIO' * 20 + b'\xff\xd9'
    resp.add_attachment(jpeg, maintype='image', subtype='jpeg', filename='Comprovativo transferência.jpg')
    resp.set_boundary('====exemplo-resposta====')
    with open(os.path.join(EMAILS, 'resposta_inquilina.eml'), 'wb') as f:
        f.write(bytes(resp))

    sem = EmailMessage()
    sem['From'] = 'proprietario1@example.com'
    sem['To'] = 'contas@example.com'
    sem['Subject'] = 'Sem anexo'
    sem['Date'] = data
    sem.set_content('Esqueci-me do anexo.')
    with open(os.path.join(EMAILS, 'sem_anexo.eml'), 'wb') as f:
        f.write(bytes(sem))


def dados_inflate():
    """Dados comprimidos pelo zlib do Python, para testar o inflate do motor (guardado, Huffman fixo e dinâmico)."""
    original = ('Total a pagar 38,47 € — período de faturação. ' * 60).encode('utf-8') + bytes(range(256))
    cru = zlib.compressobj(9, zlib.DEFLATED, -15)
    b64 = lambda b: base64.b64encode(b).decode('ascii')
    dados = {'original': b64(original), 'zlib0': b64(zlib.compress(original, 0)), 'zlib1': b64(zlib.compress(original, 1)),
             'zlib9': b64(zlib.compress(original, 9)), 'cru': b64(cru.compress(original) + cru.flush()),
             'curto_original': b64(b'abcabcabc'), 'curto': b64(zlib.compress(b'abcabcabc', 9)),
             'a85_original': b64(b'Despesas \x00\x00\x00\x00 fim'), 'a85': base64.a85encode(b'Despesas \x00\x00\x00\x00 fim', adobe=True)[2:].decode('ascii')}
    with open(os.path.join(AQUI, 'js', 'inflate.json'), 'w') as f:
        json.dump(dados, f, indent=1)


def main():
    os.makedirs(PDFS, exist_ok=True)
    os.makedirs(EMAILS, exist_ok=True)
    epal_agua(os.path.join(PDFS, 'epal_agua.pdf'))
    epal_agua(os.path.join(PDFS, 'epal_sem_total.pdf'), com_total=False)
    edp_eletricidade(os.path.join(PDFS, 'edp_eletricidade.pdf'))
    meo_internet(os.path.join(PDFS, 'meo_internet.pdf'))
    climaespaco_aquecimento(os.path.join(PDFS, 'climaespaco_aquecimento.pdf'))
    nos_internet(os.path.join(PDFS, 'nos_internet.pdf'))
    su_luz_macroman(os.path.join(PDFS, 'su_luz_macroman.pdf'))
    ginasio_outro(os.path.join(PDFS, 'ginasio_outro.pdf'))
    digitalizada(os.path.join(PDFS, 'digitalizada.pdf'))
    protegido(os.path.join(PDFS, 'protegido.pdf'))
    emails()
    dados_inflate()
    print('IBAN fictício do fornecedor:', IBAN_FORN)
    print('Gerado em', PDFS, 'e', EMAILS)


if __name__ == '__main__':
    main()
