<?php
// Despesas — arranque comum à página, à API e à linha de comandos (Cron, testes).
// A pasta app/ fica FORA da pasta pública: o servidor só serve publico/ (ver o README).

error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

define('DESPESAS_RAIZ', dirname(__DIR__));
define('DESPESAS_APP', __DIR__);
$despesasDados = getenv('DESPESAS_DADOS');
define('DESPESAS_DADOS', $despesasDados ? rtrim($despesasDados, '/') : DESPESAS_RAIZ . '/dados');
unset($despesasDados);
$despesasVersao = is_file(DESPESAS_RAIZ . '/VERSION') ? trim((string) file_get_contents(DESPESAS_RAIZ . '/VERSION')) : '';
define('DESPESAS_VERSAO', $despesasVersao !== '' ? $despesasVersao : '0.0.0');
unset($despesasVersao);

if (is_dir(DESPESAS_DADOS) && is_writable(DESPESAS_DADOS)) {
    ini_set('error_log', DESPESAS_DADOS . '/erros.log');
}
date_default_timezone_set('Europe/Lisbon');
umask(0077); // tudo o que a aplicação cria fica só para o dono

require __DIR__ . '/util.php';
require __DIR__ . '/armazem.php';
require __DIR__ . '/imoveis.php';
require __DIR__ . '/despesas.php';
require __DIR__ . '/auth.php';
require __DIR__ . '/mime.php';
require __DIR__ . '/imap.php';
require __DIR__ . '/respostas.php';
require __DIR__ . '/caixa.php';
require __DIR__ . '/api.php';
require __DIR__ . '/verificacao.php';
require __DIR__ . '/pagina.php';
