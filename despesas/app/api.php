<?php
// Despesas — a API da página (JSON). index.php?a=<ação>. Os POST levam o token CSRF no cabeçalho X-CSRF.

function api_tratar(string $acao): void
{
    $metodo = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    $u = null;
    try {
        sessao_iniciar();
        $u = utilizador_atual();
        $publicas = ['sessao' => 'GET', 'entrar' => 'POST', 'instalar' => 'POST'];
        if (isset($publicas[$acao])) {
            if ($metodo !== $publicas[$acao]) {
                throw new ErroPedido('Método não permitido.', 405);
            }
        } elseif ($metodo === 'POST') {
            csrf_verificar();
        }
        switch ($acao) {
            case 'sessao':
                api_sessao($u);
                return;
            case 'entrar':
                api_entrar();
                return;
            case 'instalar':
                api_instalar();
                return;
            case 'sair':
                api_post($metodo);
                sessao_fechar();
                json_resposta(['ok' => true]);
                return;
            case 'estado':
                api_estado(exigir_utilizador());
                return;
            case 'pdf':
                api_pdf(exigir_utilizador());
                return;
            case 'ler_caixa':
                api_post($metodo);
                exigir_utilizador('admin');
                json_resposta(caixa_ler(15));
                return;
            case 'resultado':
                api_post($metodo);
                api_resultado(exigir_utilizador('admin'), entrada_json());
                return;
            case 'fatura_guardar':
                api_post($metodo);
                api_fatura_guardar(exigir_utilizador('admin'), entrada_json());
                return;
            case 'fatura_ignorar':
            case 'fatura_reler':
            case 'fatura_reabrir':
                api_post($metodo);
                api_fatura_mudar(exigir_utilizador('admin'), $acao, entrada_json());
                return;
            case 'despesas_enviadas':
            case 'despesa_paga':
            case 'despesa_desfazer':
            case 'despesa_anular':
                api_post($metodo);
                api_despesas_mudar(exigir_utilizador(), $acao, entrada_json());
                return;
            case 'resposta_registar':
                api_post($metodo);
                api_resposta_registar(exigir_utilizador('admin'), entrada_json());
                return;
            case 'resposta_ignorar':
                api_post($metodo);
                api_resposta_ignorar(exigir_utilizador('admin'), entrada_json());
                return;
            case 'lembrete_enviado':
                api_post($metodo);
                api_despesas_mudar(exigir_utilizador('admin'), 'lembrete_enviado', entrada_json());
                return;
            case 'comprovativo_enviar':
                api_post($metodo);
                api_comprovativo_enviar(exigir_utilizador('admin'));
                return;
            case 'comprovativo':
                api_comprovativo(exigir_utilizador());
                return;
            case 'fatura_comprovativo':
                api_post($metodo);
                api_fatura_comprovativo(exigir_utilizador('admin'), entrada_json());
                return;
            case 'senha_definir':
                api_post($metodo);
                api_senha_definir(exigir_utilizador('admin'), entrada_json());
                return;
            case 'verificacao':
                exigir_utilizador('admin');
                json_resposta(verificacao_correr());
                return;
        }
        throw new ErroPedido('Ação desconhecida.', 404);
    } catch (ErroPedido $e) {
        json_resposta(['erro' => $e->getMessage()], $e->getCode() ?: 400);
    } catch (Throwable $e) {
        error_log('Despesas: ' . get_class($e) . ': ' . $e->getMessage() . ' em ' . $e->getFile() . ':' . $e->getLine());
        $admin = $u && $u['papel'] === 'admin';
        json_resposta(['erro' => 'Erro no servidor' . ($admin ? ': ' . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')' : '.')], 500);
    }
}

function api_post(string $metodo): void
{
    if ($metodo !== 'POST') {
        throw new ErroPedido('Método não permitido.', 405);
    }
}

function api_sessao(?array $u): void
{
    $estado = estado_ler();
    json_resposta([
        'versao' => DESPESAS_VERSAO,
        'utilizador' => $u,
        'csrf' => $_SESSION['csrf'] ?? '',
        'instalado' => (bool) $estado['instalado'],
    ]);
}

function api_entrar(): void
{
    $d = entrada_json();
    $r = entrar((string) ($d['email'] ?? ''), (string) ($d['senha'] ?? ''), (string) ($_SERVER['REMOTE_ADDR'] ?? '?'));
    if (!$r['ok']) {
        throw new ErroPedido($r['erro'], 401);
    }
    sessao_abrir($r['utilizador']);
    json_resposta(['ok' => true, 'utilizador' => $r['utilizador'], 'csrf' => $_SESSION['csrf']]);
}

// Primeira vez: o administrador escolhe a password com o código de instalação de dados/config.php.
function api_instalar(): void
{
    $d = entrada_json();
    $cfg = ler_config();
    $codigo = (string) ($cfg['codigo_instalacao'] ?? '');
    $adm = email_normalizado($cfg['administrador']['email'] ?? '');
    if ($adm === '' || strlen($codigo) < 12) {
        throw new ErroPedido('Falta configurar o administrador e o código de instalação (12+ caracteres) em dados/config.php.', 503);
    }
    $senha = (string) ($d['senha'] ?? '');
    $problema = senha_aceitavel($senha);
    if ($problema) {
        throw new ErroPedido($problema, 422);
    }
    $ok = estado_alterar(function (array &$estado) use ($d, $codigo, $adm, $senha) {
        if ($estado['instalado']) {
            return 'já';
        }
        if (!hash_equals($codigo, (string) ($d['codigo'] ?? ''))) {
            return 'código';
        }
        $estado['senhas'][$adm] = senha_hash($senha);
        $estado['instalado'] = true;
        registar($estado, $adm, 'instalou a aplicação');
        return 'ok';
    });
    if ($ok === 'já') {
        throw new ErroPedido('A aplicação já está instalada.', 409);
    }
    if ($ok === 'código') {
        sleep(1);
        throw new ErroPedido('Código de instalação errado.', 403);
    }
    $u = utilizadores_conhecidos($cfg, imoveis_todos())[$adm];
    sessao_abrir($u);
    json_resposta(['ok' => true, 'utilizador' => $u, 'csrf' => $_SESSION['csrf']]);
}

function api_estado(array $u): void
{
    $estado = estado_ler();
    $imoveis = imoveis_de($u, imoveis_todos());
    $refs = array_keys($imoveis);
    $faturas = [];
    foreach ($estado['faturas'] as $f) {
        if ($u['papel'] === 'admin') {
            $faturas[] = $f;
        } elseif (in_array($f['imovel'] ?? null, $refs, true) && $f['estado'] === 'lida') {
            $faturas[] = fatura_para_pagina($f, $u['papel']);
        }
    }
    $despesas = array_values(array_filter($estado['despesas'], function ($d) use ($refs) {
        return in_array($d['imovel'], $refs, true);
    }));
    $comprovativos = array_values(array_map(function ($c) {
        unset($c['sha256']);
        return $c;
    }, array_filter($estado['comprovativos'], function ($c) use ($refs) { return in_array($c['imovel'], $refs, true); })));
    $resposta = [
        'utilizador' => $u,
        'imoveis' => array_values(array_map(function ($im) use ($u) { return imovel_para_pagina($im, $u['papel']); }, $imoveis)),
        'faturas' => $faturas,
        'despesas' => $despesas,
        'comprovativos' => $comprovativos,
    ];
    if ($u['papel'] === 'admin') {
        $cfg = ler_config();
        $conhecidos = utilizadores_conhecidos($cfg, imoveis_todos());
        $resposta['caixa'] = $estado['caixa'];
        unset($resposta['caixa']['vistos']);
        $resposta['caixa']['conta'] = (string) ($cfg['imap']['utilizador'] ?? '');
        $resposta['remetentes_administrador'] = array_values(array_filter(array_map('email_normalizado', (array) ($cfg['remetentes_administrador'] ?? []))));
        $resposta['assinatura'] = texto_curto($cfg['assinatura'] ?? '', 200);
        $resposta['respostas'] = array_values($estado['respostas']);
        $resposta['lembrete_dias'] = max(1, (int) ($cfg['lembrete_dias'] ?? 5));
        $resposta['email_respostas'] = email_normalizado($cfg['email_respostas'] ?? ($cfg['imap']['utilizador'] ?? ''));
        $resposta['utilizadores'] = array_values(array_map(function ($c) use ($estado) {
            $c['tem_senha'] = isset($estado['senhas'][$c['email']]);
            return $c;
        }, $conhecidos));
        $resposta['registo'] = array_slice($estado['registo'], -30);
    }
    json_resposta($resposta);
}

function api_pdf(array $u): void
{
    $id = (string) ($_GET['id'] ?? '');
    if (!preg_match('/^[a-f0-9]{12}$/', $id)) {
        throw new ErroPedido('Fatura inválida.', 400);
    }
    $estado = estado_ler();
    $f = $estado['faturas'][$id] ?? null;
    $refs = array_keys(imoveis_de($u, imoveis_todos()));
    if (!$f || ($u['papel'] !== 'admin' && (!in_array($f['imovel'] ?? null, $refs, true) || $f['estado'] !== 'lida'))) {
        throw new ErroPedido('Fatura não encontrada.', 404);
    }
    $caminho = caixa_pasta_faturas() . '/' . $id . '.pdf';
    if (!is_file($caminho)) {
        throw new ErroPedido('O PDF já não existe no servidor.', 404);
    }
    $nome = preg_replace('/[^A-Za-z0-9._ -]/', '_', (string) ($f['ficheiro'] ?? 'fatura.pdf'));
    header('Content-Type: application/pdf');
    header('Content-Length: ' . filesize($caminho));
    header('Content-Disposition: ' . (isset($_GET['descarregar']) ? 'attachment' : 'inline') . '; filename="' . $nome . '"');
    header('Cache-Control: private, no-store');
    readfile($caminho);
}

// O motor da página leu uma fatura «por_ler» (ou voltou a ler uma): guardar o resultado.
function api_resultado(array $u, array $d): void
{
    $id = (string) ($d['id'] ?? '');
    $a = is_array($d['analise'] ?? null) ? $d['analise'] : [];
    $imoveis = imoveis_todos();
    $campos = fatura_campos_validar($a, $imoveis, false);
    $estadoNovo = in_array($a['estado'] ?? '', ['lida', 'por_confirmar', 'por_identificar'], true) ? $a['estado'] : 'por_identificar';
    $avisos = array_slice(array_map(function ($x) { return texto_curto($x, 300); }, is_array($a['avisos'] ?? null) ? $a['avisos'] : []), 0, 20);
    $valores = [];
    foreach (array_slice(is_array($a['valores'] ?? null) ? $a['valores'] : [], 0, 80) as $v) {
        if (is_array($v) && is_int($v['cent'] ?? null)) {
            $valores[] = ['cent' => $v['cent'], 'contexto' => texto_curto($v['contexto'] ?? '', 80)];
        }
    }
    $datas = array_values(array_filter(is_array($a['datas'] ?? null) ? $a['datas'] : [], 'data_iso_valida'));
    $quando = agora();
    $r = estado_alterar(function (array &$estado) use ($id, $campos, $estadoNovo, $avisos, $valores, $datas, $imoveis, $quando, $u, $a) {
        if (!isset($estado['faturas'][$id])) {
            throw new ErroPedido('Fatura não encontrada.', 404);
        }
        $f = $estado['faturas'][$id];
        if ($f['estado'] !== 'por_ler') {
            return ['estado' => $f['estado'], 'ignorado' => true]; // outra janela já a leu
        }
        // «lida» só se a validação do servidor concordar que está tudo
        if ($estadoNovo === 'lida' && ($campos['tipo'] === null || $campos['total'] === null || $campos['imovel'] === null || $campos['fornecedor'] === '')) {
            $estadoNovo = 'por_identificar';
        }
        $f = array_merge($f, $campos, ['estado' => $estadoNovo, 'avisos' => $avisos, 'lida_em' => $quando, 'sem_texto' => !empty($a['sem_texto'])]);
        if ($estadoNovo === 'lida') {
            unset($f['valores'], $f['datas']);
            $did = id_novo();
            $estado['despesas'][$did] = despesa_de_fatura($f, $imoveis[$f['imovel']], $did, $quando);
            $f['despesa'] = $did;
        } else {
            $f['valores'] = $valores;
            $f['datas'] = $datas;
        }
        $estado['faturas'][$id] = $f;
        return ['estado' => $estadoNovo];
    });
    json_resposta($r);
}

// O administrador confirma ou identifica à mão: campos completos → lida + despesa.
function api_fatura_guardar(array $u, array $d): void
{
    $id = (string) ($d['id'] ?? '');
    $imoveis = imoveis_todos();
    $campos = fatura_campos_validar(is_array($d['campos'] ?? null) ? $d['campos'] : [], $imoveis, true);
    $quando = agora();
    $r = estado_alterar(function (array &$estado) use ($id, $campos, $imoveis, $quando, $u) {
        $f = $estado['faturas'][$id] ?? null;
        if (!$f) {
            throw new ErroPedido('Fatura não encontrada.', 404);
        }
        if (!in_array($f['estado'], ['por_confirmar', 'por_identificar', 'por_ler'], true)) {
            throw new ErroPedido('Esta fatura já está ' . $f['estado'] . '.', 409);
        }
        foreach ($estado['faturas'] as $outra) {
            if ($outra['id'] !== $id && $outra['estado'] === 'lida' && ($outra['fornecedor'] ?? '') === $campos['fornecedor']
                && ($outra['imovel'] ?? '') === $campos['imovel'] && ($outra['total'] ?? 0) === $campos['total']
                && ($outra['periodo'] ?? null) == $campos['periodo'] && empty($d['mesmo_assim'])) {
                throw new ErroPedido('Já há uma fatura igual (mesmo fornecedor, imóvel, período e total). Se for mesmo outra, guardar com «mesmo assim».', 409);
            }
        }
        $f = array_merge($f, $campos, ['estado' => 'lida', 'avisos' => [], 'confirmada_em' => $quando, 'confirmada_por' => $u['email']]);
        unset($f['valores'], $f['datas']);
        $did = id_novo();
        $estado['despesas'][$did] = despesa_de_fatura($f, $imoveis[$f['imovel']], $did, $quando);
        $f['despesa'] = $did;
        $estado['faturas'][$id] = $f;
        registar($estado, $u['email'], 'guardou a fatura ' . $f['fornecedor'] . ' de ' . $f['imovel']);
        return ['ok' => true, 'despesa' => $did];
    });
    json_resposta($r);
}

function api_fatura_mudar(array $u, string $acao, array $d): void
{
    $id = (string) ($d['id'] ?? '');
    $r = estado_alterar(function (array &$estado) use ($id, $acao, $u) {
        $f = $estado['faturas'][$id] ?? null;
        if (!$f) {
            throw new ErroPedido('Fatura não encontrada.', 404);
        }
        if ($acao === 'fatura_ignorar') {
            if ($f['estado'] === 'lida') {
                throw new ErroPedido('Uma fatura lida não se ignora: reabrir primeiro.', 409);
            }
            $f['estado'] = 'ignorada';
            unset($f['valores'], $f['datas']);
            @unlink(caixa_pasta_faturas() . '/' . $id . '.pdf'); // RGPD: o que não serve não se guarda
            $f['pdf_apagado'] = true;
        } elseif ($acao === 'fatura_reler') {
            if ($f['estado'] === 'lida' || $f['estado'] === 'ignorada') {
                throw new ErroPedido('Só se volta a ler uma fatura por confirmar ou por identificar.', 409);
            }
            $f['estado'] = 'por_ler';
        } else { // fatura_reabrir: tirar a despesa (se ainda não foi enviada) e voltar a confirmar
            if ($f['estado'] !== 'lida') {
                throw new ErroPedido('Só se reabre uma fatura lida.', 409);
            }
            $did = $f['despesa'] ?? null;
            if ($did && isset($estado['despesas'][$did])) {
                if ($estado['despesas'][$did]['estado'] !== 'nova') {
                    throw new ErroPedido('A despesa desta fatura já foi enviada ao inquilino: anular a despesa em vez de reabrir.', 409);
                }
                unset($estado['despesas'][$did]);
            }
            unset($f['despesa']);
            $f['estado'] = 'por_confirmar';
            $f['valores'] = [];
            $f['datas'] = [];
        }
        $estado['faturas'][$id] = $f;
        registar($estado, $u['email'], $acao . ' ' . $id);
        return ['ok' => true, 'estado' => $f['estado']];
    });
    json_resposta($r);
}

function api_despesas_mudar(array $u, string $acao, array $d): void
{
    $mapa = ['despesas_enviadas' => 'enviar', 'despesa_paga' => 'paga', 'despesa_desfazer' => 'desfazer', 'despesa_anular' => 'anular',
        'lembrete_enviado' => 'lembrete'];
    $varias = $acao === 'despesas_enviadas' || $acao === 'lembrete_enviado';
    $ids = $varias ? (is_array($d['ids'] ?? null) ? $d['ids'] : []) : [(string) ($d['id'] ?? '')];
    if (!$ids) {
        throw new ErroPedido('Nenhuma despesa indicada.', 400);
    }
    $refs = array_keys(imoveis_de($u, imoveis_todos()));
    $quando = agora();
    $r = estado_alterar(function (array &$estado) use ($ids, $acao, $mapa, $u, $refs, $quando) {
        $mudadas = [];
        foreach ($ids as $id) {
            $id = (string) $id;
            $desp = $estado['despesas'][$id] ?? null;
            if (!$desp || !in_array($desp['imovel'], $refs, true)) {
                throw new ErroPedido('Despesa não encontrada.', 404);
            }
            $estado['despesas'][$id] = despesa_mudar($desp, $mapa[$acao], $u, $quando);
            $mudadas[] = $id;
        }
        registar($estado, $u['email'], $mapa[$acao] . ': ' . implode(', ', $mudadas));
        return ['ok' => true, 'mudadas' => $mudadas];
    });
    json_resposta($r);
}

function api_senha_definir(array $u, array $d): void
{
    $email = email_normalizado($d['email'] ?? '');
    $senha = (string) ($d['senha'] ?? '');
    $conhecidos = utilizadores_conhecidos(ler_config(), imoveis_todos());
    if (!isset($conhecidos[$email])) {
        throw new ErroPedido('Esse email não é de nenhum proprietário nem do administrador.', 404);
    }
    $problema = senha_aceitavel($senha);
    if ($problema) {
        throw new ErroPedido($problema, 422);
    }
    estado_alterar(function (array &$estado) use ($email, $senha, $u) {
        $estado['senhas'][$email] = senha_hash($senha);
        registar($estado, $u['email'], 'definiu a password de ' . $email);
    });
    json_resposta(['ok' => true]);
}

// O administrador regista a resposta do inquilino (de um email «por ver», ou do WhatsApp/telefone):
//   sim → as despesas indicadas ficam pagas («a inquilina confirmou»), com os comprovativos; não → fica registado e o
//   prazo para o lembrete recomeça.
function api_resposta_registar(array $u, array $d): void
{
    $valor = ($d['valor'] ?? '') === 'sim' ? 'sim' : (($d['valor'] ?? '') === 'nao' ? 'nao' : '');
    if ($valor === '') {
        throw new ErroPedido('A resposta tem de ser «sim» ou «não».', 400);
    }
    $ids = array_map('strval', is_array($d['ids'] ?? null) ? $d['ids'] : []);
    $rid = (string) ($d['resposta'] ?? '');
    $comps = array_map('strval', is_array($d['comprovativos'] ?? null) ? $d['comprovativos'] : []);
    $quando = agora();
    $r = estado_alterar(function (array &$estado) use ($valor, $ids, $rid, $comps, $quando, $u) {
        if ($rid !== '') {
            if (!isset($estado['respostas'][$rid])) {
                throw new ErroPedido('Resposta não encontrada.', 404);
            }
            $comps = array_values(array_unique(array_merge($comps, $estado['respostas'][$rid]['comprovativos'])));
        }
        foreach ($comps as $c) {
            if (!isset($estado['comprovativos'][$c])) {
                throw new ErroPedido('Comprovativo não encontrado.', 404);
            }
        }
        $mudadas = [];
        foreach ($ids as $id) {
            if (!isset($estado['despesas'][$id])) {
                throw new ErroPedido('Despesa não encontrada.', 404);
            }
            $estado['despesas'][$id] = $valor === 'sim'
                ? despesa_mudar($estado['despesas'][$id], 'paga', $u, $quando, ['origem' => 'inquilino', 'comprovativos' => $comps])
                : despesa_mudar($estado['despesas'][$id], 'nao_pagou', $u, $quando);
            $mudadas[] = $id;
        }
        if ($rid !== '') {
            $estado['respostas'][$rid]['estado'] = 'registada';
            $estado['respostas'][$rid]['valor'] = $valor;
            $estado['respostas'][$rid]['registada_em'] = $quando;
            $estado['respostas'][$rid]['despesas'] = $mudadas;
        }
        registar($estado, $u['email'], 'resposta do inquilino «' . $valor . '»: ' . implode(', ', $mudadas));
        return ['ok' => true, 'mudadas' => $mudadas];
    });
    json_resposta($r);
}

function api_resposta_ignorar(array $u, array $d): void
{
    $rid = (string) ($d['id'] ?? '');
    estado_alterar(function (array &$estado) use ($rid, $u) {
        if (!isset($estado['respostas'][$rid])) {
            throw new ErroPedido('Resposta não encontrada.', 404);
        }
        $estado['respostas'][$rid]['estado'] = 'ignorada';
        registar($estado, $u['email'], 'ignorou a resposta ' . $rid);
    });
    json_resposta(['ok' => true]);
}

// Carregar um comprovativo na página (o que chegou por WhatsApp, por exemplo). Fica na pasta do imóvel.
function api_comprovativo_enviar(array $u): void
{
    $ref = (string) ($_POST['imovel'] ?? '');
    if (!isset(imoveis_todos()[$ref])) {
        throw new ErroPedido('Imóvel desconhecido.', 404);
    }
    $f = $_FILES['ficheiro'] ?? null;
    if (!$f || !is_array($f) || ($f['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
        $erro = is_array($f) ? (int) ($f['error'] ?? 0) : UPLOAD_ERR_NO_FILE;
        throw new ErroPedido($erro === UPLOAD_ERR_INI_SIZE || $erro === UPLOAD_ERR_FORM_SIZE
            ? 'O ficheiro passa o limite do alojamento (upload_max_filesize = ' . ini_get('upload_max_filesize') . ').'
            : 'Não chegou nenhum ficheiro (erro ' . $erro . ').', 400);
    }
    $dados = (string) file_get_contents($f['tmp_name']);
    $quando = agora();
    $id = estado_alterar(function (array &$estado) use ($ref, $f, $dados, $quando, $u) {
        $id = comprovativo_guardar($estado, $ref, (string) ($f['name'] ?? 'comprovativo'), $dados, 'carregado', $quando);
        if ($id !== null) {
            registar($estado, $u['email'], 'carregou um comprovativo para ' . $ref);
        }
        return $id;
    });
    if ($id === null) {
        throw new ErroPedido('O comprovativo tem de ser um PDF ou uma imagem (JPG, PNG, WEBP, HEIC) até 15 MB.', 422);
    }
    json_resposta(['ok' => true, 'id' => $id]);
}

function api_comprovativo(array $u): void
{
    $id = (string) ($_GET['id'] ?? '');
    $estado = estado_ler();
    $c = $estado['comprovativos'][$id] ?? null;
    $refs = array_keys(imoveis_de($u, imoveis_todos()));
    if (!$c || !in_array($c['imovel'], $refs, true)) {
        throw new ErroPedido('Comprovativo não encontrado.', 404);
    }
    $caminho = comprovativos_pasta($c['imovel']) . '/' . basename($c['ficheiro']);
    if (!is_file($caminho)) {
        throw new ErroPedido('O ficheiro já não existe no servidor.', 404);
    }
    header('Content-Type: ' . $c['tipo']);
    header('Content-Length: ' . filesize($caminho));
    header('Content-Disposition: ' . (isset($_GET['descarregar']) ? 'attachment' : 'inline') . '; filename="' . basename($c['ficheiro']) . '"');
    header('Cache-Control: private, no-store');
    readfile($caminho);
}

// Um PDF que chegou como fatura mas é um comprovativo de pagamento: passa para a pasta do imóvel e vira resposta.
function api_fatura_comprovativo(array $u, array $d): void
{
    $id = (string) ($d['id'] ?? '');
    $ref = (string) ($d['imovel'] ?? '');
    if (!isset(imoveis_todos()[$ref])) {
        throw new ErroPedido('Escolher o imóvel primeiro.', 422);
    }
    $quando = agora();
    $r = estado_alterar(function (array &$estado) use ($id, $ref, $quando, $u) {
        $f = $estado['faturas'][$id] ?? null;
        if (!$f || $f['estado'] === 'lida') {
            throw new ErroPedido('Só uma fatura por identificar ou por confirmar pode passar a comprovativo.', 409);
        }
        $caminho = caixa_pasta_faturas() . '/' . $id . '.pdf';
        $dados = is_file($caminho) ? (string) file_get_contents($caminho) : '';
        $cid = comprovativo_guardar($estado, $ref, (string) ($f['ficheiro'] ?? 'comprovativo.pdf'), $dados, 'reencaminhado', $quando);
        if ($cid === null) {
            throw new ErroPedido('Não consegui guardar o comprovativo.', 500);
        }
        @unlink($caminho);
        $rid = id_novo();
        $estado['respostas'][$rid] = ['id' => $rid, 'imovel' => $ref, 'de' => $f['remetente'] ?? '', 'assunto' => $f['assunto'] ?? '',
            'recebido_em' => $f['recebido_em'] ?? $quando, 'texto' => '', 'comprovativos' => [$cid], 'sugestao' => 'sim', 'estado' => 'por_ver',
            'origem' => 'fatura'];
        $estado['comprovativos'][$cid]['resposta'] = $rid;
        $f['estado'] = 'ignorada';
        $f['nota'] = 'era um comprovativo de pagamento';
        $f['pdf_apagado'] = true;
        unset($f['valores'], $f['datas']);
        $estado['faturas'][$id] = $f;
        registar($estado, $u['email'], 'passou a fatura ' . $id . ' a comprovativo de ' . $ref);
        return ['ok' => true, 'resposta' => $rid];
    });
    json_resposta($r);
}
