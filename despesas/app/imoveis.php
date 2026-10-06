<?php
// Despesas — os imóveis: uma pasta por imóvel em dados/imoveis/<REF>/imovel.json (ver exemplos/imoveis).
// Feitas aqui, com o Claude, quando entra um imóvel novo; o servidor só as lê.

const TIPOS_DESPESA = ['agua', 'eletricidade', 'gas', 'internet', 'aquecimento'];

function imoveis_todos(?string $pasta = null): array
{
    static $cache = [];
    $pasta = $pasta ?? (DESPESAS_DADOS . '/imoveis');
    if (isset($cache[$pasta])) {
        return $cache[$pasta];
    }
    $lista = [];
    foreach (glob($pasta . '/*/imovel.json') ?: [] as $ficheiro) {
        $dados = json_decode((string) file_get_contents($ficheiro), true);
        if (!is_array($dados)) {
            error_log('Despesas: imovel.json inválido em ' . basename(dirname($ficheiro)));
            continue;
        }
        $im = imovel_normalizar($dados, basename(dirname($ficheiro)));
        $lista[$im['ref']] = $im;
    }
    ksort($lista);
    $cache[$pasta] = $lista;
    return $lista;
}

function imovel_normalizar(array $d, string $pastaRef): array
{
    $ref = preg_match('/^[A-Za-z0-9_-]{1,60}$/', (string) ($d['ref'] ?? '')) ? (string) $d['ref'] : $pastaRef;
    $prop = is_array($d['proprietario'] ?? null) ? $d['proprietario'] : [];
    $prop['email'] = email_normalizado($prop['email'] ?? '');
    $inq = is_array($d['inquilino'] ?? null) ? $d['inquilino'] : [];
    $remetentes = [];
    foreach (array_merge([$prop['email']], is_array($d['remetentes'] ?? null) ? $d['remetentes'] : []) as $r) {
        $e = email_normalizado($r);
        if ($e !== '' && !in_array($e, $remetentes, true)) {
            $remetentes[] = $e;
        }
    }
    $partilha = [];
    foreach (TIPOS_DESPESA as $t) {
        $p = $d['partilha'][$t] ?? 100;
        $partilha[$t] = (is_numeric($p) && $p >= 0 && $p <= 100) ? $p + 0 : 100; // «50» → 50, «33.5» → 33.5
    }
    return [
        'ref' => $ref,
        'nome' => texto_curto($d['nome'] ?? $ref, 120),
        'morada' => texto_curto($d['morada'] ?? '', 200),
        'apelidos' => array_values(array_filter(array_map(function ($a) { return texto_curto($a, 60); }, is_array($d['apelidos'] ?? null) ? $d['apelidos'] : []))),
        'proprietario' => [
            'nome' => texto_curto($prop['nome'] ?? '', 120),
            'email' => $prop['email'],
            'iban' => texto_curto($prop['iban'] ?? '', 42),
            'titular' => texto_curto($prop['titular'] ?? ($prop['nome'] ?? ''), 120),
            'mbway' => texto_curto($prop['mbway'] ?? '', 30),
        ],
        'inquilino' => [
            'nome' => texto_curto($inq['nome'] ?? '', 120),
            'email' => email_normalizado($inq['email'] ?? ''),
            'whatsapp' => texto_curto($inq['whatsapp'] ?? '', 30),
        ],
        'remetentes' => $remetentes,
        'identificadores' => array_values(array_filter(is_array($d['identificadores'] ?? null) ? $d['identificadores'] : [], function ($i) {
            return is_string($i) || (is_array($i) && isset($i['valor']));
        })),
        'partilha' => $partilha,
        'mensagem' => is_array($d['mensagem'] ?? null) ? ['assinatura' => texto_curto($d['mensagem']['assinatura'] ?? '', 200)] : ['assinatura' => ''],
    ];
}

// Endereços cujos emails contam: os proprietários, os remetentes extra de cada imóvel e os do administrador.
function remetentes_permitidos(array $imoveis, array $cfg): array
{
    $lista = [];
    foreach ($imoveis as $im) {
        foreach ($im['remetentes'] as $r) {
            $lista[$r] = true;
        }
    }
    foreach ((array) ($cfg['remetentes_administrador'] ?? []) as $r) {
        $e = email_normalizado($r);
        if ($e !== '') {
            $lista[$e] = true;
        }
    }
    return array_keys($lista);
}

// Os imóveis que um utilizador pode ver: o administrador vê todos; o proprietário, os seus.
function imoveis_de(array $utilizador, array $imoveis): array
{
    if ($utilizador['papel'] === 'admin') {
        return $imoveis;
    }
    return array_filter($imoveis, function ($im) use ($utilizador) {
        return $im['proprietario']['email'] !== '' && $im['proprietario']['email'] === $utilizador['email'];
    });
}

// O que vai para o browser: o proprietário não precisa dos identificadores nem dos contactos da inquilina.
function imovel_para_pagina(array $im, string $papel): array
{
    if ($papel === 'admin') {
        return $im;
    }
    return ['ref' => $im['ref'], 'nome' => $im['nome'], 'partilha' => $im['partilha'],
        'proprietario' => ['nome' => $im['proprietario']['nome']], 'inquilino' => ['nome' => $im['inquilino']['nome']]];
}
