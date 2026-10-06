<?php
// Despesas — separar um email (RFC 822 / MIME): os anexos (PDF das faturas; PDF e fotos dos comprovativos) e o texto.
// Percorre multipart/* e também emails reencaminhados «como anexo» (message/rfc822). Descodifica base64 e
// quoted-printable, os nomes de ficheiro em RFC 2047 (=?utf-8?Q?…?=) e RFC 2231 (filename*=utf-8''…).

const MIME_PROFUNDIDADE = 8;

// Devolve ['de' => email, 'de_nome' => nome, 'assunto' => texto, 'data' => ISO|null, 'message_id' => texto,
//          'pdfs' => [['nome', 'dados'], …], 'anexos' => [['nome', 'tipo', 'dados'], …], 'texto' => o corpo em texto simples]
function mime_analisar(string $bruto): array
{
    $acc = ['pdfs' => [], 'anexos' => [], 'texto' => null, 'html' => null];
    list($cab, $corpo) = mime_separar($bruto);
    mime_percorrer($cab, $corpo, $acc, 0);
    $de = mime_endereco($cab['from'] ?? '');
    $data = null;
    if (!empty($cab['date'])) {
        $t = strtotime(preg_replace('/\s*\([^)]*\)\s*$/', '', $cab['date']));
        $data = $t ? date('c', $t) : null;
    }
    return [
        'de' => $de['email'],
        'de_nome' => $de['nome'],
        'assunto' => texto_curto(mime_cabecalho_texto($cab['subject'] ?? ''), 300),
        'data' => $data,
        'message_id' => texto_curto($cab['message-id'] ?? '', 300),
        'pdfs' => $acc['pdfs'],
        'anexos' => $acc['anexos'],
        'texto' => $acc['texto'] !== null ? $acc['texto'] : ($acc['html'] !== null ? mime_html_para_texto($acc['html']) : ''),
    ];
}

function mime_html_para_texto(string $html): string
{
    $s = preg_replace('#<(script|style)\b[^>]*>.*?</\1>#is', '', $html) ?? '';
    $s = preg_replace('#<(br|/p|/div|/li|/tr|/h\d)\b[^>]*>#i', "\n", $s) ?? '';
    $s = html_entity_decode(strip_tags($s), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    return trim(preg_replace("/[ \t]+/", ' ', $s) ?? '');
}

// O tipo verdadeiro de um anexo, pelos primeiros bytes (não se confia no que o email diz).
function mime_tipo_real(string $dados): string
{
    if (strpos(substr($dados, 0, 1024), '%PDF') !== false) {
        return 'application/pdf';
    }
    if (substr($dados, 0, 3) === "\xFF\xD8\xFF") {
        return 'image/jpeg';
    }
    if (substr($dados, 0, 8) === "\x89PNG\r\n\x1A\n") {
        return 'image/png';
    }
    if (substr($dados, 0, 4) === 'RIFF' && substr($dados, 8, 4) === 'WEBP') {
        return 'image/webp';
    }
    if (substr($dados, 4, 4) === 'ftyp' && in_array(substr($dados, 8, 4), ['heic', 'heix', 'mif1', 'msf1', 'heis'], true)) {
        return 'image/heic';
    }
    return 'application/octet-stream';
}

// Cabeçalhos e corpo. Os cabeçalhos ficam num array nome-em-minúsculas → valor (o primeiro de cada nome).
function mime_separar(string $bruto): array
{
    $p1 = strpos($bruto, "\r\n\r\n");
    $p2 = strpos($bruto, "\n\n");
    if ($p1 !== false && ($p2 === false || $p1 <= $p2)) {
        $cabTexto = substr($bruto, 0, $p1);
        $corpo = (string) substr($bruto, $p1 + 4);
    } elseif ($p2 !== false) {
        $cabTexto = substr($bruto, 0, $p2);
        $corpo = (string) substr($bruto, $p2 + 2);
    } else {
        $cabTexto = $bruto;
        $corpo = '';
    }
    // Uma parte sem cabeçalhos começa logo com a linha em branco.
    if ($cabTexto !== '' && !preg_match('/^[\x21-\x39\x3B-\x7E]+:/', $cabTexto)) {
        return [[], $bruto];
    }
    $cabTexto = preg_replace("/\r?\n[ \t]+/", ' ', $cabTexto);
    $cab = [];
    foreach (preg_split("/\r?\n/", (string) $cabTexto) as $linha) {
        $dp = strpos($linha, ':');
        if ($dp === false) {
            continue;
        }
        $nome = strtolower(trim(substr($linha, 0, $dp)));
        if (!isset($cab[$nome])) {
            $cab[$nome] = trim(substr($linha, $dp + 1));
        }
    }
    return [$cab, $corpo];
}

// «tipo/subtipo; nome=valor; nome*=utf-8''valor%20…» → ['valor' => 'tipo/subtipo', 'params' => [...]]
function mime_parametros(string $valor): array
{
    $partes = [];
    $atual = '';
    $aspas = false;
    $n = strlen($valor);
    for ($i = 0; $i < $n; $i++) {
        $c = $valor[$i];
        if ($c === '"' && ($i === 0 || $valor[$i - 1] !== '\\')) {
            $aspas = !$aspas;
        }
        if ($c === ';' && !$aspas) {
            $partes[] = $atual;
            $atual = '';
            continue;
        }
        $atual .= $c;
    }
    $partes[] = $atual;
    $principal = strtolower(trim(array_shift($partes)));
    $simples = [];
    $continuacoes = [];
    foreach ($partes as $p) {
        $ig = strpos($p, '=');
        if ($ig === false) {
            continue;
        }
        $k = strtolower(trim(substr($p, 0, $ig)));
        $v = trim(substr($p, $ig + 1));
        if (strlen($v) >= 2 && $v[0] === '"' && substr($v, -1) === '"') {
            $v = stripcslashes(substr($v, 1, -1));
        }
        if (preg_match('/^([^*]+)\*(\d+)(\*?)$/', $k, $m)) {          // RFC 2231 em pedaços: nome*0*=…, nome*1*=…
            $continuacoes[$m[1]][(int) $m[2]] = [$v, $m[3] === '*'];
        } elseif (substr($k, -1) === '*') {                         // RFC 2231 numa só peça: nome*=utf-8''…
            $simples[substr($k, 0, -1)] = mime_rfc2231($v, true);
        } else {
            $simples[$k] = $v;
        }
    }
    foreach ($continuacoes as $k => $pedacos) {
        ksort($pedacos);
        $juntos = '';
        $charset = '';
        foreach ($pedacos as $i => $pd) {
            list($v, $codificado) = $pd;
            if ($i === 0 && $codificado && preg_match("/^([^']*)'[^']*'(.*)$/s", $v, $m)) {
                $charset = $m[1];
                $v = $m[2];
            }
            $juntos .= $codificado ? rawurldecode($v) : $v;
        }
        $simples[$k] = para_utf8($juntos, $charset);
    }
    return ['valor' => $principal, 'params' => $simples];
}

function mime_rfc2231(string $v, bool $codificado): string
{
    if ($codificado && preg_match("/^([^']*)'[^']*'(.*)$/s", $v, $m)) {
        return para_utf8(rawurldecode($m[2]), $m[1]);
    }
    return $codificado ? rawurldecode($v) : $v;
}

// Palavras codificadas RFC 2047 (=?charset?B|Q?…?=); as que estão seguidas juntam-se sem o espaço entre elas.
function mime_cabecalho_texto(string $s): string
{
    $s = preg_replace('/(=\?[^?]+\?[bBqQ]\?[^?]*\?=)\s+(?==\?[^?]+\?[bBqQ]\?)/', '$1', $s);
    $r = preg_replace_callback('/=\?([^?]+)\?([bBqQ])\?([^?]*)\?=/', function ($m) {
        $charset = preg_replace('/\*.*$/', '', $m[1]);  // =?utf-8*pt?…  (língua RFC 2231)
        if (strtoupper($m[2]) === 'B') {
            $bytes = (string) base64_decode($m[3]);
        } else {
            $bytes = quoted_printable_decode(str_replace('_', ' ', $m[3]));
        }
        return para_utf8($bytes, $charset);
    }, $s);
    return para_utf8((string) $r);
}

// «Nome <email@x>» ou «email@x» → ['email' => minúsculas, 'nome' => texto]
function mime_endereco(string $valor): array
{
    $valor = mime_cabecalho_texto($valor);
    if (preg_match('/^(.*)<\s*([^<>\s]+@[^<>\s]+)\s*>/', $valor, $m)) {
        return ['email' => strtolower(trim($m[2])), 'nome' => trim(trim($m[1]), "\" \t")];
    }
    if (preg_match('/([^\s<>"]+@[^\s<>"]+)/', $valor, $m)) {
        return ['email' => strtolower(trim($m[1], '.,;')), 'nome' => ''];
    }
    return ['email' => '', 'nome' => ''];
}

function mime_descodificar_corpo(string $corpo, string $codificacao): string
{
    $cod = strtolower(trim($codificacao));
    if ($cod === 'base64') {
        return (string) base64_decode(preg_replace('/[^A-Za-z0-9+\/=]/', '', $corpo));
    }
    if ($cod === 'quoted-printable') {
        return quoted_printable_decode($corpo);
    }
    return $corpo;
}

// Partes de um multipart: tudo o que está entre as linhas «--fronteira», até «--fronteira--».
function mime_partes_multipart(string $corpo, string $fronteira): array
{
    $d = '--' . $fronteira;
    $partes = [];
    $pos = strpos($corpo, $d);
    if ($pos === false) {
        return $partes;
    }
    while (true) {
        $pos += strlen($d);
        if (substr($corpo, $pos, 2) === '--') {
            break; // fronteira final
        }
        $eol = strpos($corpo, "\n", $pos);
        if ($eol === false) {
            break;
        }
        $inicio = $eol + 1;
        $prox = strpos($corpo, "\n" . $d, $inicio - 1);
        if ($prox === false) {
            $partes[] = (string) substr($corpo, $inicio);
            break;
        }
        $fim = $prox;
        if ($fim > $inicio && $corpo[$fim - 1] === "\r") {
            $fim--;
        }
        $partes[] = $fim > $inicio ? substr($corpo, $inicio, $fim - $inicio) : '';
        $pos = $prox + 1;
    }
    return $partes;
}

function mime_percorrer(array $cab, string $corpo, array &$acc, int $prof): void
{
    if ($prof > MIME_PROFUNDIDADE) {
        return;
    }
    $ct = mime_parametros($cab['content-type'] ?? 'text/plain');
    $tipo = $ct['valor'];
    if (strpos($tipo, 'multipart/') === 0) {
        $fronteira = $ct['params']['boundary'] ?? '';
        if ($fronteira === '') {
            return;
        }
        foreach (mime_partes_multipart($corpo, $fronteira) as $parte) {
            list($c2, $b2) = mime_separar($parte);
            mime_percorrer($c2, $b2, $acc, $prof + 1);
        }
        return;
    }
    $cod = $cab['content-transfer-encoding'] ?? '';
    if ($tipo === 'message/rfc822') {
        list($c2, $b2) = mime_separar(mime_descodificar_corpo($corpo, $cod));
        mime_percorrer($c2, $b2, $acc, $prof + 1);
        return;
    }
    $disp = mime_parametros($cab['content-disposition'] ?? '');
    $nome = $disp['params']['filename'] ?? ($ct['params']['name'] ?? '');
    $nome = mime_cabecalho_texto((string) $nome);
    // O corpo do email (o primeiro texto que não é anexo): serve para ler a resposta do inquilino.
    if (($tipo === 'text/plain' || $tipo === 'text/html') && $disp['valor'] !== 'attachment' && $nome === '') {
        $chave = $tipo === 'text/plain' ? 'texto' : 'html';
        if ($acc[$chave] === null) {
            $acc[$chave] = para_utf8(mime_descodificar_corpo($corpo, $cod), (string) ($ct['params']['charset'] ?? ''));
        }
        return;
    }
    if (strpos($tipo, 'text/') === 0 || strpos($tipo, 'multipart/') === 0) {
        return;
    }
    $dados = mime_descodificar_corpo($corpo, $cod);
    if ($dados === '') {
        return;
    }
    $real = mime_tipo_real($dados);
    $nome = preg_replace('/[\/\\\\\x00-\x1F]/', '_', $nome);
    if ($nome === '' || $nome === null) {
        $nome = $real === 'application/pdf' ? 'documento.pdf' : 'anexo';
    }
    $nome = texto_curto($nome, 150);
    $acc['anexos'][] = ['nome' => $nome, 'tipo' => $real, 'dados' => $dados];
    if ($real === 'application/pdf') {
        $acc['pdfs'][] = ['nome' => $nome, 'dados' => $dados]; // diz que é PDF e é mesmo (pelos bytes)
    }
}
