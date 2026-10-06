<?php
// Despesas — testes do PHP. Correm no servidor (não há PHP no Mac onde a aplicação é feita):
//   php /home/<conta>/despesas/app/testes.php        (Terminal do cPanel)
// ou na página Verificação. Usam só pastas temporárias e os ficheiros fictícios de testes/ e exemplos/.

function testes_php_correr(): array
{
    $res = [];
    $tmp = rtrim(sys_get_temp_dir(), '/') . '/despesas-testes-' . bin2hex(random_bytes(4));
    $t = function (string $nome, callable $fn) use (&$res) {
        try {
            $fn();
            $res[] = ['nome' => $nome, 'ok' => true];
        } catch (Throwable $e) {
            $res[] = ['nome' => $nome, 'ok' => false, 'erro' => $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')'];
        }
    };
    $igual = function ($veio, $esperado, string $msg = '') {
        if ($veio !== $esperado) {
            throw new Exception(($msg !== '' ? $msg . ': ' : '') . 'esperava ' . var_export($esperado, true) . ', veio ' . var_export($veio, true));
        }
    };
    $verdade = function ($c, string $msg = 'condição falsa') {
        if (!$c) {
            throw new Exception($msg);
        }
    };
    $falha = function (callable $fn, string $msg) {
        try {
            $fn();
        } catch (Throwable $e) {
            return $e;
        }
        throw new Exception('devia ter falhado: ' . $msg);
    };
    $testes = DESPESAS_RAIZ . '/testes';
    $eml = function (string $nome) use ($testes) { return (string) file_get_contents($testes . '/emails/' . $nome); };
    $pdf = function (string $nome) use ($testes) { return (string) file_get_contents($testes . '/pdfs/' . $nome); };
    $admin = ['email' => 'admin@example.com', 'nome' => 'Admin', 'papel' => 'admin'];
    $dono = ['email' => 'proprietario1@example.com', 'nome' => 'Dono', 'papel' => 'proprietario'];
    $outro = ['email' => 'outro@example.com', 'nome' => 'Outro', 'papel' => 'proprietario'];

    // ── email (MIME) ─────────────────────────────────────────────────────────────────────────
    $t('email reencaminhado com PDF anexado', function () use ($igual, $verdade, $eml, $pdf) {
        $m = mime_analisar($eml('reencaminhado_com_pdf.eml'));
        $igual($m['de'], 'proprietario1@example.com', 'remetente');
        $igual($m['assunto'], 'Fwd: Fatura da água de agosto', 'assunto');
        $igual(count($m['pdfs']), 1, 'PDFs');
        $igual($m['pdfs'][0]['nome'], 'fatura água agosto.pdf', 'nome (RFC 2231)');
        $igual(hash('sha256', $m['pdfs'][0]['dados']), hash('sha256', $pdf('epal_agua.pdf')), 'conteúdo do PDF');
        $verdade(strpos((string) $m['data'], '2026-09-10') === 0, 'data ' . $m['data']);
    });
    $t('email reencaminhado como anexo (message/rfc822) e octet-stream .PDF', function () use ($igual, $eml, $pdf) {
        $m = mime_analisar($eml('anexo_rfc822.eml'));
        $igual($m['de'], 'proprietario2@example.com', 'remetente em minúsculas');
        $igual($m['assunto'], 'Fatura da internet — setembro', 'assunto RFC 2047');
        $igual(count($m['pdfs']), 1, 'PDFs');
        $igual($m['pdfs'][0]['nome'], 'Fatura_Setembro.PDF');
        $igual(hash('sha256', $m['pdfs'][0]['dados']), hash('sha256', $pdf('meo_internet.pdf')), 'conteúdo do PDF');
    });
    $t('email sem anexo', function () use ($igual, $eml) {
        $igual(count(mime_analisar($eml('sem_anexo.eml'))['pdfs']), 0);
    });
    $t('cabeçalhos codificados e parâmetros em pedaços (RFC 2047 e 2231)', function () use ($igual) {
        $igual(mime_cabecalho_texto('=?ISO-8859-1?Q?Fatura_da_=E1gua?= =?UTF-8?B?w6dv?='), 'Fatura da águaço');
        $p = mime_parametros("attachment; filename*0*=utf-8''fatura%20; filename*1*=%C3%A1gua.pdf");
        $igual($p['valor'], 'attachment');
        $igual($p['params']['filename'], 'fatura água.pdf');
        $igual(mime_parametros('multipart/mixed; boundary="==a;b=="')['params']['boundary'], '==a;b==');
        $igual(mime_endereco('"Ana" <Ana@Example.COM>'), ['email' => 'ana@example.com', 'nome' => 'Ana']);
    });
    $t('multipart com CRLF e parte vazia', function () use ($igual) {
        $bruto = "From: a@example.com\r\nSubject: x\r\nContent-Type: multipart/mixed; boundary=\"F\"\r\n\r\n"
            . "--F\r\nContent-Type: text/plain\r\n\r\nolá\r\n--F\r\n\r\n--F\r\nContent-Type: application/pdf\r\n"
            . "Content-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename=\"a.pdf\"\r\n\r\n"
            . chunk_split(base64_encode("%PDF-1.4\nconteudo\n%%EOF\n"), 8, "\r\n") . "--F--\r\n";
        $m = mime_analisar($bruto);
        $igual(count($m['pdfs']), 1);
        $igual($m['pdfs'][0]['dados'], "%PDF-1.4\nconteudo\n%%EOF\n");
    });

    // ── IMAP só de leitura ───────────────────────────────────────────────────────────────────
    $t('IMAP: EXAMINE, SEARCH e FETCH com BODY.PEEK, sem a password no registo', function () use ($igual, $verdade) {
        $respostas = "D0001 OK autenticado\r\n"
            . "* FLAGS (\\Seen)\r\n* OK [UIDVALIDITY 777] UIDs valid.\r\n* 3 EXISTS\r\nD0002 OK [READ-ONLY] INBOX selected.\r\n"
            . "* SEARCH 9 5\r\nD0003 OK SEARCH completed\r\n"
            . "* 1 FETCH (UID 5 BODY[] {12}\r\nHello\r\nWorld)\r\nD0004 OK Success\r\n"
            . "* BYE\r\nD0005 OK\r\n";
        $in = fopen('php://memory', 'w+');
        fwrite($in, $respostas);
        rewind($in);
        $out = fopen('php://memory', 'w+');
        $l = new LeitorImap();
        $l->usarFluxos($in, $out);
        $l->entrar('contas@example.com', 'segredo123');
        $igual($l->examinar('INBOX'), 777, 'UIDVALIDITY');
        $igual($l->procurar('SINCE 01-Sep-2026 FROM "a@example.com"'), [5, 9], 'UIDs');
        $igual($l->buscar(5), "Hello\r\nWorld", 'mensagem');
        $enviados = implode("\n", $l->enviados);
        $l->sair();
        rewind($out);
        $escrito = stream_get_contents($out);
        $verdade(strpos($escrito, 'D0002 EXAMINE "INBOX"') !== false, 'EXAMINE');
        $verdade(strpos($escrito, 'D0004 UID FETCH 5 (BODY.PEEK[])') !== false, 'BODY.PEEK');
        $verdade(!preg_match('/SELECT|STORE|EXPUNGE|COPY|MOVE/', $escrito), 'comandos que mudam a caixa');
        $verdade(strpos($enviados, 'segredo123') === false && strpos($enviados, '"***"') !== false, 'password fora do registo');
    });
    $t('IMAP: comandos que mudam a caixa são recusados', function () use ($falha) {
        $l = new LeitorImap();
        $falha(function () use ($l) {
            (function () { return $this->comando('UID STORE 5 +FLAGS (\\Seen)'); })->call($l);
        }, 'STORE');
    });
    $t('IMAP: resposta NO dá erro', function () use ($falha) {
        $in = fopen('php://memory', 'w+');
        fwrite($in, "D0001 NO [AUTHENTICATIONFAILED] Invalid credentials\r\n");
        rewind($in);
        $l = new LeitorImap();
        $l->usarFluxos($in, fopen('php://memory', 'w+'));
        $falha(function () use ($l) { $l->entrar('a', 'b'); }, 'login recusado');
    });

    // ── faturas, despesas e estados ──────────────────────────────────────────────────────────
    $imoveis = imoveis_todos(DESPESAS_RAIZ . '/exemplos/imoveis');
    $t('pasta de imóvel de exemplo: normalização', function () use ($igual, $verdade, $imoveis) {
        $verdade(isset($imoveis['EXEMPLO-1']), 'EXEMPLO-1 lido');
        $im = $imoveis['EXEMPLO-1'];
        $igual($im['remetentes'][0], 'proprietario1@example.com', 'o email do proprietário conta como remetente');
        $igual($im['partilha']['aquecimento'], 50, 'partilha do aquecimento');
        $igual($im['partilha']['agua'], 100, 'partilha por omissão');
        $verdade(iban_valido($im['proprietario']['iban']), 'IBAN do exemplo válido');
        $igual($im['proprietario']['mbway'], '+351 900 000 000', 'MB WAY do proprietário');
    });
    $t('despesa a partir da fatura, com a percentagem do imóvel', function () use ($igual, $imoveis) {
        $f = ['id' => 'f1', 'imovel' => 'EXEMPLO-1', 'tipo' => 'aquecimento', 'fornecedor' => 'Climaespaço', 'periodo' => null,
            'data_limite' => '2026-10-15', 'total' => 2734];
        $d = despesa_de_fatura($f, $imoveis['EXEMPLO-1'], 'd1', '2026-10-06T10:00:00+01:00');
        $igual($d['valor'], 1367);
        $igual($d['estado'], 'nova');
    });
    $t('estados: nova → enviada → paga, e desfazer', function () use ($igual, $falha, $admin, $dono, $outro) {
        $q = '2026-10-06T10:00:00+01:00';
        $d = ['id' => 'd1', 'imovel' => 'EXEMPLO-1', 'estado' => 'nova', 'enviada_em' => null, 'paga_em' => null, 'paga_por' => null];
        $falha(function () use ($d, $dono, $q) { despesa_mudar($d, 'enviar', $dono, $q); }, 'o proprietário não envia');
        $d = despesa_mudar($d, 'enviar', $admin, $q);
        $igual($d['estado'], 'enviada');
        $d = despesa_mudar($d, 'paga', $dono, $q);
        $igual([$d['estado'], $d['paga_por']], ['paga', 'proprietario1@example.com']);
        $falha(function () use ($d, $outro, $q) { despesa_mudar($d, 'desfazer', $outro, $q); }, 'outro proprietário não desfaz');
        $falha(function () use ($d, $admin, $q) { despesa_mudar($d, 'anular', $admin, $q); }, 'não se anula uma paga');
        $d = despesa_mudar($d, 'desfazer', $dono, $q);
        $igual($d['estado'], 'enviada', 'volta a enviada');
        $d = despesa_mudar($d, 'desfazer', $admin, $q);
        $igual([$d['estado'], $d['enviada_em']], ['nova', null]);
        $igual(despesa_mudar($d, 'anular', $admin, $q)['estado'], 'anulada');
    });
    $t('campos de uma fatura: validação', function () use ($igual, $falha, $imoveis) {
        $ok = fatura_campos_validar(['fornecedor' => 'EPAL', 'fornecedor_id' => 'epal', 'tipo' => 'agua', 'total' => 3847, 'imovel' => 'EXEMPLO-1',
            'periodo' => ['de' => '2026-08-01', 'ate' => '2026-08-31'], 'data_limite' => '2026-09-25',
            'pagamento' => ['metodo' => 'multibanco', 'entidade' => '12345', 'referencia' => '123456789', 'iban' => 'PT50 0000 0000 1234 5678 9013 6']], $imoveis, true);
        $igual($ok['pagamento'], ['metodo' => 'multibanco', 'entidade' => '12345', 'referencia' => '123 456 789'], 'IBAN inválido fica de fora');
        $igual(fatura_campos_validar(['periodo' => ['de' => '2026-09-01', 'ate' => '2026-08-01']], $imoveis, false)['periodo'], null, 'período ao contrário');
        $e = $falha(function () use ($imoveis) {
            fatura_campos_validar(['fornecedor' => 'X', 'tipo' => 'gas', 'total' => 100, 'imovel' => 'EXEMPLO-1'], $imoveis, true);
        }, 'tipo gás');
        $igual($e->getCode(), 422);
        $falha(function () use ($imoveis) { fatura_campos_validar(['fornecedor' => 'X', 'tipo' => 'agua', 'total' => 0, 'imovel' => 'EXEMPLO-1'], $imoveis, true); }, 'total zero');
        $falha(function () use ($imoveis) { fatura_campos_validar(['fornecedor' => 'X', 'tipo' => 'agua', 'total' => 100, 'imovel' => 'NAO-EXISTE'], $imoveis, true); }, 'imóvel desconhecido');
    });
    $t('IBAN: módulo 97', function () use ($verdade) {
        $verdade(iban_valido('PT50 0000 0000 1234 5678 9013 5'));
        $verdade(!iban_valido('PT50 0000 0000 1234 5678 9013 6'));
    });

    // ── entrar ───────────────────────────────────────────────────────────────────────────────
    $t('password: hash forte e verificação', function () use ($verdade, $igual) {
        $h = senha_hash('uma password comprida');
        $verdade(password_verify('uma password comprida', $h));
        $verdade(!password_verify('outra', $h));
        $verdade(strpos($h, '$argon2id$') === 0 || strpos($h, '$2y$') === 0, 'algoritmo ' . substr($h, 0, 10));
        $igual(senha_aceitavel('curta'), 'A password tem de ter pelo menos 10 caracteres.');
    });
    $t('limite de tentativas: 5 falhas bloqueiam 15 minutos', function () use ($verdade) {
        $tt = [];
        for ($i = 0; $i < 4; $i++) {
            tentativas_falhou($tt, 'email:x', 1000 + $i);
        }
        $verdade(!tentativas_bloqueada($tt, 'email:x', 1010), 'ainda não');
        tentativas_falhou($tt, 'email:x', 1010);
        $verdade(tentativas_bloqueada($tt, 'email:x', 1011), 'bloqueado');
        $verdade(!tentativas_bloqueada($tt, 'email:x', 1010 + TENTATIVAS_JANELA + 1), 'desbloqueado depois da janela');
    });
    $t('quem pode entrar: administrador e proprietários', function () use ($igual, $imoveis) {
        $u = utilizadores_conhecidos(['administrador' => ['email' => 'Admin@Example.com', 'nome' => 'Admin']], $imoveis);
        $igual($u['admin@example.com']['papel'], 'admin');
        $igual($u['proprietario1@example.com']['papel'], 'proprietario');
    });

    // ── ficheiros: estado e caixa ────────────────────────────────────────────────────────────
    $t('estado em JSON: escrever, ler, cópia anterior e permissões', function () use ($igual, $verdade, $tmp) {
        $pasta = $tmp . '/estado';
        estado_alterar(function (array &$e) { $e['instalado'] = true; }, $pasta);
        $r = estado_alterar(function (array &$e) { $e['senhas']['a@example.com'] = 'h'; return 'feito'; }, $pasta);
        $igual($r, 'feito');
        $e = estado_ler($pasta);
        $igual([$e['instalado'], $e['senhas']], [true, ['a@example.com' => 'h']]);
        $verdade(is_file($pasta . '/estado.json.anterior'), 'cópia anterior');
        $igual(fileperms($pasta . '/estado.json') & 0777, 0600, 'permissões');
    });
    $t('caixa: guarda o PDF, não repete o mesmo PDF, ignora remetentes de fora', function () use ($igual, $verdade, $eml, $tmp) {
        $estado = estado_vazio();
        $pasta = $tmp . '/faturas';
        $rem = ['proprietario1@example.com', 'proprietario2@example.com'];
        $r = caixa_guardar_mensagem($estado, $eml('reencaminhado_com_pdf.eml'), 11, $rem, $pasta, '2026-10-06T10:00:00+01:00');
        $igual($r['novas'], 1);
        $f = array_values($estado['faturas'])[0];
        $igual([$f['estado'], $f['remetente'], $f['assunto']], ['por_ler', 'proprietario1@example.com', 'Fwd: Fatura da água de agosto']);
        $verdade(is_file($pasta . '/' . $f['id'] . '.pdf'), 'PDF gravado');
        $igual(fileperms($pasta . '/' . $f['id'] . '.pdf') & 0777, 0600, 'PDF só para o dono');
        $igual(caixa_guardar_mensagem($estado, $eml('reencaminhado_com_pdf.eml'), 12, $rem, $pasta, 'x')['novas'], 0, 'repetido');
        $igual(caixa_guardar_mensagem($estado, $eml('anexo_rfc822.eml'), 13, ['so@example.com'], $pasta, 'x')['novas'], 0, 'remetente de fora');
        $verdade((string) caixa_guardar_mensagem($estado, $eml('sem_anexo.eml'), 14, $rem, $pasta, 'x')['nota'] !== '', 'nota sem PDF');
        $igual(count($estado['faturas']), 1);
    });
    $t('resposta da inquilina: comprovativo na pasta do imóvel, sem o texto citado, sugestão «sim»', function () use ($igual, $verdade, $eml, $tmp) {
        $estado = estado_vazio();
        $rem = ['proprietario1@example.com'];
        $inq = ['inquilina@example.com' => 'EXEMPLO-1'];
        $r = caixa_guardar_mensagem($estado, $eml('resposta_inquilina.eml'), 21, $rem, $tmp . '/faturas2', '2026-10-07T09:00:00+01:00', $inq, $tmp . '/comprovativos');
        $igual([$r['novas'], $r['respostas']], [0, 1]);
        $resp = array_values($estado['respostas'])[0];
        $igual([$resp['imovel'], $resp['estado'], $resp['sugestao']], ['EXEMPLO-1', 'por_ver', 'sim']);
        $igual($resp['texto'], 'Sim, já paguei hoje. Segue o comprovativo.', 'sem o que vem citado');
        $c = $estado['comprovativos'][$resp['comprovativos'][0]];
        $igual($c['tipo'], 'image/jpeg');
        $verdade((bool) preg_match('/^2026-10-07_[a-f0-9]{12}_Comprovativo-transferencia\.jpg$/', $c['ficheiro']), 'nome do ficheiro: ' . $c['ficheiro']);
        $verdade(is_file($tmp . '/comprovativos/EXEMPLO-1/' . $c['ficheiro']), 'ficheiro na pasta do imóvel');
        $igual(fileperms($tmp . '/comprovativos/EXEMPLO-1/' . $c['ficheiro']) & 0777, 0600, 'só para o dono');
        $igual(count($estado['faturas']), 0, 'não é fatura');
    });
    $t('o que a resposta parece dizer', function () use ($igual) {
        $igual(resposta_sugestao('Sim, está pago', false), 'sim');
        $igual(resposta_sugestao('Já transferi ontem', false), 'sim');
        $igual(resposta_sugestao('Ainda não paguei, pago na sexta', false), 'nao');
        $igual(resposta_sugestao('NÃO', false), 'nao');
        $igual(resposta_sugestao('Olá, tenho uma dúvida sobre a luz', false), null);
        $igual(resposta_sugestao('', true), 'sim');
        $igual(resposta_excerto("Pago.\n\nOn Mon, 6 Oct 2026, Gestão wrote:\n> texto"), 'Pago.');
    });
    $t('pagar com a confirmação do inquilino, lembretes e «ainda não»', function () use ($igual, $admin, $dono) {
        $q = '2026-10-08T10:00:00+01:00';
        $d = ['id' => 'd1', 'imovel' => 'EXEMPLO-1', 'estado' => 'enviada', 'enviada_em' => '2026-10-01T10:00:00+01:00', 'paga_em' => null, 'paga_por' => null];
        $l = despesa_mudar($d, 'lembrete', $admin, $q);
        $igual($l['lembretes'], [$q]);
        $n = despesa_mudar($d, 'nao_pagou', $admin, $q);
        $igual($n['ultima_resposta'], ['quando' => $q, 'valor' => 'nao']);
        $p = despesa_mudar($d, 'paga', $admin, $q, ['origem' => 'inquilino', 'comprovativos' => ['c1']]);
        $igual([$p['estado'], $p['paga_origem'], $p['comprovativos']], ['paga', 'inquilino', ['c1']]);
        $igual(despesa_mudar($d, 'paga', $dono, $q, ['origem' => 'inquilino'])['paga_origem'], 'proprietario', 'o proprietário só regista o que recebeu');
        $igual(despesa_mudar($p, 'desfazer', $admin, $q)['paga_origem'], null);
    });
    $t('tipos de anexo pelos bytes', function () use ($igual) {
        $igual(mime_tipo_real("%PDF-1.4\n"), 'application/pdf');
        $igual(mime_tipo_real("\xFF\xD8\xFF\xE0abc"), 'image/jpeg');
        $igual(mime_tipo_real("\x89PNG\r\n\x1A\nabc"), 'image/png');
        $igual(mime_tipo_real("....ftypheicxxxx"), 'image/heic');
        $igual(mime_tipo_real('MZ executável'), 'application/octet-stream');
    });
    $t('dados dentro da pasta pública são detetados', function () use ($verdade) {
        $verdade(dentro_de('/home/x/public_html/despesas/dados', '/home/x/public_html'));
        $verdade(!dentro_de('/home/x/despesas/dados', '/home/x/despesas/publico'));
        $verdade(!dentro_de('/home/x/public_html2', '/home/x/public_html'));
    });

    testes_apagar_pasta($tmp);
    $ok = count(array_filter($res, function ($r) { return $r['ok']; }));
    return ['passaram' => $ok, 'total' => count($res), 'resultados' => $res];
}

function testes_apagar_pasta(string $pasta): void
{
    if (!is_dir($pasta)) {
        return;
    }
    foreach (scandir($pasta) ?: [] as $f) {
        if ($f === '.' || $f === '..') {
            continue;
        }
        $c = $pasta . '/' . $f;
        is_dir($c) ? testes_apagar_pasta($c) : @unlink($c);
    }
    @rmdir($pasta);
}

if (PHP_SAPI === 'cli' && isset($argv[0]) && realpath($argv[0]) === __FILE__) {
    if (!defined('DESPESAS_RAIZ')) {
        require __DIR__ . '/arranque.php';
    }
    $r = testes_php_correr();
    foreach ($r['resultados'] as $x) {
        echo ($x['ok'] ? '  ok    ' : '  FALHA ') . $x['nome'] . ($x['ok'] ? '' : "\n        " . $x['erro']) . "\n";
    }
    echo "\n" . $r['passaram'] . '/' . $r['total'] . " testes do PHP passaram\n";
    exit($r['passaram'] === $r['total'] ? 0 : 1);
}
