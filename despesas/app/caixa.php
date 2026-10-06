<?php
// Despesas — ler a caixa de correio das faturas e guardar os anexos PDF em dados/faturas/ (fora da pasta pública).
// Só emails de remetentes da lista (proprietários, remetentes extra dos imóveis, administrador). Só leitura.
// Cada PDF novo vira uma fatura «por_ler»; a página lê-a (motor JavaScript) e devolve os campos.

function caixa_pasta_faturas(): string
{
    return DESPESAS_DADOS . '/faturas';
}

// Guarda os PDFs de uma mensagem. Puro o suficiente para testar: recebe o estado, as pastas e os remetentes.
// Os emails dos inquilinos ($inquilinos: email → imóvel) não são faturas: são respostas («já paguei», comprovativo).
// Devolve ['novas' => n, 'respostas' => n, 'nota' => texto|null].
function caixa_guardar_mensagem(array &$estado, string $bruto, int $uid, array $remetentes, string $pastaFaturas, string $quando,
    array $inquilinos = [], ?string $pastaComprovativos = null): array
{
    $m = mime_analisar($bruto);
    if ($m['de'] !== '' && isset($inquilinos[$m['de']])) {
        resposta_de_email($estado, $m, $inquilinos[$m['de']], $quando, $pastaComprovativos);
        return ['novas' => 0, 'respostas' => 1, 'nota' => null];
    }
    if ($m['de'] === '' || !in_array($m['de'], $remetentes, true)) {
        return ['novas' => 0, 'respostas' => 0, 'nota' => null]; // a pesquisa FROM do IMAP é por pedaço de texto: confirmar o endereço exato
    }
    if (!$m['pdfs']) {
        return ['novas' => 0, 'respostas' => 0, 'nota' => 'Email de ' . $m['de'] . ' («' . $m['assunto'] . '») sem PDF anexado.'];
    }
    $existentes = [];
    foreach ($estado['faturas'] as $f) {
        $existentes[$f['sha256']] = true;
    }
    $novas = 0;
    foreach ($m['pdfs'] as $pdf) {
        $sha = hash('sha256', $pdf['dados']);
        if (isset($existentes[$sha])) {
            continue; // o mesmo PDF já veio noutro email
        }
        $id = id_novo();
        escrever_atomico($pastaFaturas . '/' . $id . '.pdf', $pdf['dados']);
        $estado['faturas'][$id] = [
            'id' => $id,
            'estado' => 'por_ler',
            'remetente' => $m['de'],
            'assunto' => $m['assunto'],
            'recebido_em' => $m['data'] ?: $quando,
            'ficheiro' => $pdf['nome'],
            'sha256' => $sha,
            'tamanho' => strlen($pdf['dados']),
            'uid' => $uid,
            'criada' => $quando,
            'avisos' => [],
        ];
        $existentes[$sha] = true;
        $novas++;
    }
    return ['novas' => $novas, 'respostas' => 0, 'nota' => null];
}

// Lê a caixa. $maximo mensagens por vez (o alojamento corta pedidos longos); devolve se ainda há mais.
function caixa_ler(int $maximo = 15): array
{
    $cfg = ler_config();
    $imap = (array) ($cfg['imap'] ?? []);
    if (empty($imap['utilizador']) || empty($imap['app_password'])) {
        throw new ErroPedido('Falta configurar a caixa de correio (imap → utilizador e app_password em dados/config.php).', 503);
    }
    $remetentes = remetentes_permitidos(imoveis_todos(), $cfg);
    $inquilinos = inquilinos_emails(imoveis_todos());
    if (!$remetentes) {
        throw new ErroPedido('Não há remetentes: falta pelo menos um imóvel com o email do proprietário.', 503);
    }
    @set_time_limit(120);
    $desde = strtotime((string) ($cfg['ler_desde'] ?? '')) ?: strtotime('-120 days');
    $antes = estado_ler();
    $leitor = new LeitorImap();
    $mensagens = [];
    $haMais = false;
    $validade = 0;
    try {
        $leitor->ligar((string) ($imap['servidor'] ?? 'imap.gmail.com'), (int) ($imap['porta'] ?? 993));
        $leitor->entrar((string) $imap['utilizador'], (string) $imap['app_password']);
        $validade = $leitor->examinar((string) ($imap['pasta'] ?? 'INBOX'));
        $uids = [];
        foreach (array_unique(array_merge($remetentes, array_keys($inquilinos))) as $r) {
            foreach ($leitor->procurar('SINCE ' . date('d-M-Y', $desde) . ' FROM ' . LeitorImap::aspas($r)) as $u) {
                $uids[$u] = true;
            }
        }
        $uids = array_keys($uids);
        sort($uids);
        $vistos = ($antes['caixa']['uidvalidity'] ?? null) === $validade ? array_flip($antes['caixa']['vistos'] ?? []) : [];
        $novos = array_values(array_filter($uids, function ($u) use ($vistos) { return !isset($vistos[$u]); }));
        $haMais = count($novos) > $maximo;
        foreach (array_slice($novos, 0, $maximo) as $uid) {
            $mensagens[$uid] = $leitor->buscar($uid);
        }
        $leitor->sair();
    } catch (Throwable $e) {
        $leitor->sair();
        $msg = $e->getMessage();
        estado_alterar(function (array &$estado) use ($msg) {
            $estado['caixa']['ultimo_erro'] = ['quando' => agora(), 'erro' => $msg];
        });
        throw new ErroPedido($msg, 502);
    }
    $quando = agora();
    $pasta = caixa_pasta_faturas();
    return estado_alterar(function (array &$estado) use ($mensagens, $remetentes, $inquilinos, $pasta, $quando, $validade, $haMais) {
        if (($estado['caixa']['uidvalidity'] ?? null) !== $validade) {
            $estado['caixa']['vistos'] = [];
            $estado['caixa']['uidvalidity'] = $validade;
        }
        $novas = 0;
        $respostas = 0;
        $notas = [];
        foreach ($mensagens as $uid => $bruto) {
            try {
                $r = caixa_guardar_mensagem($estado, $bruto, $uid, $remetentes, $pasta, $quando, $inquilinos);
                $novas += $r['novas'];
                $respostas += $r['respostas'];
                if ($r['nota']) {
                    $notas[] = $r['nota'];
                }
            } catch (Throwable $e) {
                $notas[] = 'Não consegui ler a mensagem ' . $uid . ': ' . $e->getMessage();
            }
            $estado['caixa']['vistos'][] = $uid;
        }
        $estado['caixa']['ultima_leitura'] = $quando;
        $estado['caixa']['ultimo_erro'] = null;
        $estado['caixa']['sem_pdf'] = array_slice(array_merge($estado['caixa']['sem_pdf'] ?? [], array_map(function ($n) use ($quando) {
            return ['quando' => $quando, 'nota' => $n];
        }, $notas)), -20);
        if ($mensagens) {
            registar($estado, 'caixa', count($mensagens) . ' email(s) lido(s), ' . $novas . ' fatura(s) nova(s), ' . $respostas . ' resposta(s) de inquilinos');
        }
        return ['mensagens' => count($mensagens), 'novas' => $novas, 'respostas' => $respostas, 'ha_mais' => $haMais, 'notas' => $notas];
    });
}
