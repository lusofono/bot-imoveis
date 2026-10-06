<?php
// Despesas — faturas e despesas: validar o que vem da página, criar a despesa de cada fatura e mudar estados.
//
// Fatura: por_ler (PDF guardado, ainda não lido) → lida | por_confirmar | por_identificar → lida (ou ignorada).
// Despesa (a parte do inquilino de uma fatura lida): nova → enviada (ao inquilino) → paga (o senhorio recebeu).
// Todas as funções aqui são puras (recebem e devolvem arrays), para se poderem testar sem servidor.

const ESTADOS_FATURA = ['por_ler', 'lida', 'por_confirmar', 'por_identificar', 'ignorada'];
const METODOS_PAGAMENTO = ['debito_direto', 'multibanco', 'transferencia'];

function iban_valido(string $iban): bool
{
    $s = strtoupper(preg_replace('/\s+/', '', $iban));
    if (!preg_match('/^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/', $s)) {
        return false;
    }
    $r = substr($s, 4) . substr($s, 0, 4);
    $resto = 0;
    $n = strlen($r);
    for ($i = 0; $i < $n; $i++) {
        $c = $r[$i];
        $v = ctype_alpha($c) ? (string) (ord($c) - 55) : $c;
        $k = strlen($v);
        for ($j = 0; $j < $k; $j++) {
            $resto = ($resto * 10 + (int) $v[$j]) % 97;
        }
    }
    return $resto === 1;
}

function periodo_validar($p): ?array
{
    if (!is_array($p)) {
        return null;
    }
    if (isset($p['mes']) && is_string($p['mes']) && preg_match('/^\d{4}-(0[1-9]|1[0-2])$/', $p['mes'])) {
        return ['mes' => $p['mes']];
    }
    if (data_iso_valida($p['de'] ?? null) && data_iso_valida($p['ate'] ?? null) && $p['de'] <= $p['ate']) {
        return ['de' => $p['de'], 'ate' => $p['ate']];
    }
    return null;
}

function pagamento_validar($p): array
{
    $saida = ['metodo' => null];
    if (!is_array($p)) {
        return $saida;
    }
    if (in_array($p['metodo'] ?? null, METODOS_PAGAMENTO, true)) {
        $saida['metodo'] = $p['metodo'];
    }
    if (isset($p['entidade']) && preg_match('/^\d{5}$/', (string) $p['entidade'])) {
        $saida['entidade'] = (string) $p['entidade'];
    }
    if (isset($p['referencia'])) {
        $ref = preg_replace('/\s+/', '', (string) $p['referencia']);
        if (preg_match('/^\d{9}$/', $ref)) {
            $saida['referencia'] = substr($ref, 0, 3) . ' ' . substr($ref, 3, 3) . ' ' . substr($ref, 6, 3);
        }
    }
    if (isset($p['montante']) && is_int($p['montante'])) {
        $saida['montante'] = $p['montante'];
    }
    if (isset($p['iban']) && is_string($p['iban']) && iban_valido($p['iban']) && $saida['metodo'] !== 'debito_direto') {
        $saida['iban'] = trim(chunk_split(strtoupper(preg_replace('/\s+/', '', $p['iban'])), 4, ' '));
    }
    return $saida;
}

// Campos de uma fatura vindos da página (do motor ou escritos à mão). $completa: exige tudo o que a despesa precisa.
function fatura_campos_validar(array $c, array $imoveis, bool $completa): array
{
    $erros = [];
    $f = [];
    $f['fornecedor_id'] = preg_match('/^[a-z0-9-]{1,40}$/', (string) ($c['fornecedor_id'] ?? '')) ? (string) $c['fornecedor_id'] : null;
    $f['fornecedor'] = texto_curto($c['fornecedor'] ?? '', 80);
    $f['tipo'] = in_array($c['tipo'] ?? null, TIPOS_DESPESA, true) ? $c['tipo'] : null;
    $total = $c['total'] ?? null;
    $f['total'] = (is_int($total) && $total > 0 && $total < 10000000) ? $total : null;
    $f['periodo'] = periodo_validar($c['periodo'] ?? null);
    $f['data_limite'] = data_iso_valida($c['data_limite'] ?? null) ? $c['data_limite'] : null;
    $f['pagamento'] = pagamento_validar($c['pagamento'] ?? null);
    $f['imovel'] = (is_string($c['imovel'] ?? null) && isset($imoveis[$c['imovel']])) ? $c['imovel'] : null;
    if ($completa) {
        if ($f['fornecedor'] === '') {
            $erros[] = 'falta o fornecedor';
        }
        if ($f['tipo'] === null) {
            $erros[] = 'o tipo tem de ser água, eletricidade, gás, internet ou aquecimento';
        }
        if ($f['total'] === null) {
            $erros[] = 'falta o total (maior do que zero)';
        }
        if ($f['imovel'] === null) {
            $erros[] = 'falta o imóvel';
        }
        if ($erros) {
            throw new ErroPedido('Não dá para guardar: ' . implode('; ', $erros) . '.', 422);
        }
    }
    return $f;
}

// A parte do inquilino: a percentagem do imóvel para esse tipo (100 % se nada for dito).
function despesa_de_fatura(array $fatura, array $imovel, string $id, string $quando): array
{
    $pct = $imovel['partilha'][$fatura['tipo']] ?? 100;
    return [
        'id' => $id,
        'fatura' => $fatura['id'],
        'imovel' => $fatura['imovel'],
        'tipo' => $fatura['tipo'],
        'fornecedor' => $fatura['fornecedor'],
        'periodo' => $fatura['periodo'],
        'data_limite' => $fatura['data_limite'],
        'total' => $fatura['total'],
        'percentagem' => $pct,
        'valor' => (int) round($fatura['total'] * $pct / 100),
        'estado' => 'nova',
        'criada' => $quando,
        'enviada_em' => null,
        'paga_em' => null,
        'paga_por' => null,
    ];
}

// Mudar o estado de uma despesa. Devolve a despesa alterada ou lança ErroPedido.
//   enviar   (admin):        nova|enviada → enviada (reenviar só atualiza a data)
//   paga     (admin, dono):  nova|enviada → paga
//   desfazer (admin):        paga → enviada (ou nova, se nunca foi enviada); enviada → nova
//            (dono):         paga → enviada|nova, só se foi ele a marcar
//   anular   (admin):        nova|enviada → anulada (fatura errada, por exemplo)
//   lembrete (admin):        enviada → enviada, com mais um lembrete enviado nesta data
//   nao_pagou (admin):       enviada → enviada, com a resposta «ainda não paguei» (o prazo do lembrete recomeça)
// $extra no «paga»: 'origem' (inquilino = o inquilino confirmou; proprietario = recebeu; admin) e 'comprovativos'.
function despesa_mudar(array $d, string $acao, array $utilizador, string $quando, array $extra = []): array
{
    $admin = $utilizador['papel'] === 'admin';
    $e = $d['estado'];
    if ($acao === 'enviar' && $admin && ($e === 'nova' || $e === 'enviada')) {
        $d['estado'] = 'enviada';
        $d['enviada_em'] = $quando;
        return $d;
    }
    if ($acao === 'paga' && ($e === 'nova' || $e === 'enviada')) {
        $origem = $extra['origem'] ?? ($admin ? 'admin' : 'proprietario');
        if (!$admin) {
            $origem = 'proprietario';
        }
        $d['estado'] = 'paga';
        $d['paga_em'] = $quando;
        $d['paga_por'] = $utilizador['email'];
        $d['paga_origem'] = in_array($origem, ['inquilino', 'proprietario', 'admin'], true) ? $origem : 'admin';
        $d['comprovativos'] = array_values(array_unique(array_merge($d['comprovativos'] ?? [], array_map('strval', (array) ($extra['comprovativos'] ?? [])))));
        return $d;
    }
    if ($acao === 'lembrete' && $admin && $e === 'enviada') {
        $d['lembretes'] = array_merge($d['lembretes'] ?? [], [$quando]);
        return $d;
    }
    if ($acao === 'nao_pagou' && $admin && $e === 'enviada') {
        $d['ultima_resposta'] = ['quando' => $quando, 'valor' => 'nao'];
        return $d;
    }
    if ($acao === 'desfazer' && $e === 'paga' && ($admin || $d['paga_por'] === $utilizador['email'])) {
        $d['estado'] = $d['enviada_em'] ? 'enviada' : 'nova';
        $d['paga_em'] = null;
        $d['paga_por'] = null;
        $d['paga_origem'] = null;
        return $d;
    }
    if ($acao === 'desfazer' && $e === 'enviada' && $admin) {
        $d['estado'] = 'nova';
        $d['enviada_em'] = null;
        return $d;
    }
    if ($acao === 'anular' && $admin && ($e === 'nova' || $e === 'enviada')) {
        $d['estado'] = 'anulada';
        return $d;
    }
    throw new ErroPedido('Não é possível «' . $acao . '» uma despesa ' . $e . '.', 409);
}

// O que um utilizador pode ver de uma fatura. O proprietário só vê as lidas dos seus imóveis, sem os auxiliares.
function fatura_para_pagina(array $f, string $papel): array
{
    if ($papel === 'admin') {
        return $f;
    }
    $campos = ['id', 'imovel', 'fornecedor', 'tipo', 'total', 'periodo', 'data_limite', 'pagamento', 'recebido_em', 'ficheiro'];
    return array_intersect_key($f, array_flip($campos));
}
