<?php
// Despesas — utilitários comuns (configuração, ficheiros, respostas, texto).
// Compatível com PHP 7.4+; não depende de mbstring nem de iconv (usa-os só se existirem).

class ErroPedido extends Exception {}

function ler_config(): array
{
    static $cfg = null;
    if ($cfg !== null) {
        return $cfg;
    }
    $caminho = DESPESAS_DADOS . '/config.php';
    if (!is_file($caminho)) {
        throw new ErroPedido('Falta o ficheiro de configuração (dados/config.php). Ver o README.', 503);
    }
    $lido = require $caminho;
    if (!is_array($lido)) {
        throw new ErroPedido('O ficheiro dados/config.php não devolve uma lista de opções.', 503);
    }
    $cfg = $lido;
    return $cfg;
}

function config_existe(): bool
{
    return is_file(DESPESAS_DADOS . '/config.php');
}

function id_novo(): string
{
    return bin2hex(random_bytes(6));
}

function agora(): string
{
    return date('c');
}

function garantir_pasta(string $pasta): void
{
    if (!is_dir($pasta) && !@mkdir($pasta, 0700, true) && !is_dir($pasta)) {
        throw new RuntimeException('Não consegui criar a pasta ' . basename($pasta) . '.');
    }
}

// Escreve por cima de forma atómica (ficheiro temporário + rename) e com permissões só para o dono.
function escrever_atomico(string $caminho, string $conteudo, int $modo = 0600): void
{
    garantir_pasta(dirname($caminho));
    $tmp = $caminho . '.tmp-' . bin2hex(random_bytes(4));
    if (@file_put_contents($tmp, $conteudo) === false) {
        throw new RuntimeException('Não consegui escrever ' . basename($caminho) . '.');
    }
    @chmod($tmp, $modo);
    if (!@rename($tmp, $caminho)) {
        @unlink($tmp);
        throw new RuntimeException('Não consegui gravar ' . basename($caminho) . '.');
    }
}

function json_codificar($dados, bool $bonito = false): string
{
    $flags = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | ($bonito ? JSON_PRETTY_PRINT : 0);
    $s = json_encode($dados, $flags);
    if ($s === false) {
        throw new RuntimeException('JSON inválido: ' . json_last_error_msg());
    }
    return $s;
}

function json_resposta($dados, int $codigo = 200): void
{
    http_response_code($codigo);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_codificar($dados);
}

// O pedido em JSON (corpo do POST).
function entrada_json(): array
{
    $bruto = file_get_contents('php://input');
    if ($bruto === false || $bruto === '') {
        return [];
    }
    $dados = json_decode($bruto, true);
    if (!is_array($dados)) {
        throw new ErroPedido('Pedido inválido (JSON).', 400);
    }
    return $dados;
}

function texto_curto($valor, int $max = 200): string
{
    if (!is_string($valor) && !is_numeric($valor)) {
        return '';
    }
    $s = (string) $valor;
    if (preg_match('//u', $s) !== 1) {
        $s = cp1252_para_utf8($s);
    }
    $s = trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $s) ?? '');
    if (strlen($s) > $max) {
        $s = substr($s, 0, $max);
        // não cortar um carácter UTF-8 a meio
        while ($s !== '' && preg_match('//u', $s) !== 1) {
            $s = substr($s, 0, -1);
        }
    }
    return $s;
}

function email_normalizado($valor): string
{
    $e = strtolower(trim((string) $valor));
    return filter_var($e, FILTER_VALIDATE_EMAIL) ? $e : '';
}

// true se $caminho está dentro de $pasta (ou é ela).
function dentro_de(string $caminho, string $pasta): bool
{
    $c = rtrim(str_replace('\\', '/', $caminho), '/') . '/';
    $p = rtrim(str_replace('\\', '/', $pasta), '/') . '/';
    return strpos($c, $p) === 0;
}

function eh_https(): bool
{
    if (!empty($_SERVER['HTTPS']) && strtolower((string) $_SERVER['HTTPS']) !== 'off') {
        return true;
    }
    if (strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https') {
        return true;
    }
    return (string) ($_SERVER['SERVER_PORT'] ?? '') === '443';
}

function cabecalhos_seguranca(bool $comCsp = true): void
{
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: no-referrer');
    header('Strict-Transport-Security: max-age=31536000');
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
    if (!$comCsp) {
        return; // o PDF aberto no browser: a CSP (object-src 'none') bloquearia o visualizador de PDF
    }
    // style-src com 'unsafe-inline' só por causa da pré-visualização da tabela (estilos em linha para o Gmail).
    header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        . "img-src 'self' data: blob:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; "
        . "form-action 'self'; frame-ancestors 'none'");
}

// Texto num charset qualquer → UTF-8, mesmo sem mbstring nem iconv.
function para_utf8(string $bytes, string $charset = ''): string
{
    $cs = strtolower(preg_replace('/[^a-z0-9]/i', '', $charset));
    if ($cs === 'utf8' || $cs === 'usascii' || $cs === 'ascii' || $cs === '') {
        if (preg_match('//u', $bytes) === 1) {
            return $bytes;
        }
        $cs = 'windows1252';
    }
    if (function_exists('mb_convert_encoding')) {
        $mapa = ['iso88591' => 'ISO-8859-1', 'latin1' => 'ISO-8859-1', 'iso885915' => 'ISO-8859-15', 'windows1252' => 'Windows-1252',
            'cp1252' => 'Windows-1252', 'utf16' => 'UTF-16', 'utf16be' => 'UTF-16BE', 'utf16le' => 'UTF-16LE'];
        if (isset($mapa[$cs])) {
            $r = @mb_convert_encoding($bytes, 'UTF-8', $mapa[$cs]);
            if (is_string($r)) {
                return $r;
            }
        }
    }
    if (function_exists('iconv') && $charset !== '') {
        $r = @iconv($charset, 'UTF-8//IGNORE', $bytes);
        if (is_string($r) && $r !== '') {
            return $r;
        }
    }
    return cp1252_para_utf8($bytes);
}

function cp1252_para_utf8(string $bytes): string
{
    static $alto = [0x20AC, 0xFFFD, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021, 0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0xFFFD,
        0x017D, 0xFFFD, 0xFFFD, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, 0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0xFFFD,
        0x017E, 0x0178];
    $saida = '';
    $n = strlen($bytes);
    for ($i = 0; $i < $n; $i++) {
        $c = ord($bytes[$i]);
        if ($c < 0x80) {
            $saida .= $bytes[$i];
            continue;
        }
        $cp = ($c < 0xA0) ? $alto[$c - 0x80] : $c;
        $saida .= codepoint_utf8($cp);
    }
    return $saida;
}

function codepoint_utf8(int $cp): string
{
    if ($cp < 0x80) {
        return chr($cp);
    }
    if ($cp < 0x800) {
        return chr(0xC0 | ($cp >> 6)) . chr(0x80 | ($cp & 0x3F));
    }
    if ($cp < 0x10000) {
        return chr(0xE0 | ($cp >> 12)) . chr(0x80 | (($cp >> 6) & 0x3F)) . chr(0x80 | ($cp & 0x3F));
    }
    return chr(0xF0 | ($cp >> 18)) . chr(0x80 | (($cp >> 12) & 0x3F)) . chr(0x80 | (($cp >> 6) & 0x3F)) . chr(0x80 | ($cp & 0x3F));
}

function data_iso_valida($s): bool
{
    if (!is_string($s) || !preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $s, $m)) {
        return false;
    }
    return checkdate((int) $m[2], (int) $m[3], (int) $m[1]);
}
