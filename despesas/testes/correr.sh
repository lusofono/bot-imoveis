#!/bin/sh
# Testes do motor (JavaScript), com o jsc que vem com o macOS — não é preciso instalar nada.
# Uso, a partir de qualquer pasta:  sh despesas/testes/correr.sh
# Os testes do PHP correm no servidor (php app/testes.php, ou a página Verificação); ver o README.
cd "$(dirname "$0")/.." || exit 1
JSC=/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc
[ -x "$JSC" ] || JSC=$(command -v jsc)
if [ -z "$JSC" ]; then echo "Não encontrei o jsc (JavaScriptCore)."; exit 1; fi
"$JSC" testes/js/correr.js -- "$PWD"
