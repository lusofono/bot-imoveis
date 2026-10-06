<?php
// Despesas — ler a caixa a partir do Cron do cPanel (só na linha de comandos), por exemplo de 6 em 6 horas:
//   php /home/<conta>/despesas/app/ler.php
// Guarda os PDFs novos como faturas «por ler»; a página lê-as quando o administrador a abrir.
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
require __DIR__ . '/arranque.php';
try {
    $r = caixa_ler(30);
    echo date('c') . ' ' . $r['mensagens'] . ' email(s), ' . $r['novas'] . ' fatura(s) nova(s)' . ($r['ha_mais'] ? ' (há mais)' : '') . "\n";
    foreach ($r['notas'] as $n) {
        echo '  ' . $n . "\n";
    }
} catch (Throwable $e) {
    fwrite(STDERR, date('c') . ' ERRO: ' . $e->getMessage() . "\n");
    exit(1);
}
