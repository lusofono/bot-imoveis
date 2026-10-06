#!/bin/sh
# Ler uma fatura real com o motor da página (no Mac, sem instalar nada). Para afinar as regras com o Claude.
# Uso:  sh despesas/ferramentas/ler_pdf.sh despesas/amostras/fatura.pdf [remetente] [assunto]
[ -n "$1" ] || { echo "Uso: sh ferramentas/ler_pdf.sh <fatura.pdf> [remetente] [assunto]"; exit 1; }
PDF=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.." || exit 1
JSC=/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc
[ -x "$JSC" ] || JSC=$(command -v jsc)
# os imóveis locais (dados/imoveis/*/imovel.json), se existirem, para ver também a que imóvel a fatura vai
if [ -d dados/imoveis ]; then ls "$PWD"/dados/imoveis/*/imovel.json > dados/.lista-imoveis 2>/dev/null; fi
"$JSC" ferramentas/ler_pdf.js -- "$PWD" "$PDF" "$2" "$3"
rm -f dados/.lista-imoveis
