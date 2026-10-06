<?php
// Despesas — entrar e sair. Duas espécies de utilizador:
//   admin        — o email em config 'administrador'; vê e gere tudo;
//   proprietario — o email do proprietário na pasta de cada imóvel; vê só os seus imóveis e marca o que recebeu.
// Passwords fixas dadas pelo administrador, guardadas só como hash (Argon2id ou bcrypt). Sessões só por HTTPS,
// cookie HttpOnly + SameSite=Strict, e um token CSRF em todos os pedidos que mudam alguma coisa.

const TENTATIVAS_MAX = 5;
const TENTATIVAS_JANELA = 900;      // 15 minutos
const SESSAO_INATIVA = 7200;        // 2 horas sem uso → sai

function senha_hash(string $senha): string
{
    $algo = defined('PASSWORD_ARGON2ID') ? PASSWORD_ARGON2ID : PASSWORD_DEFAULT;
    $h = password_hash($senha, $algo);
    if (!is_string($h)) {
        throw new RuntimeException('Não consegui calcular o hash da password.');
    }
    return $h;
}

function senha_aceitavel(string $senha): ?string
{
    if (strlen($senha) < 10) {
        return 'A password tem de ter pelo menos 10 caracteres.';
    }
    if (strlen($senha) > 200) {
        return 'A password é demasiado comprida.';
    }
    return null;
}

// Limite de tentativas (puro, para testar): bloqueia uma chave depois de TENTATIVAS_MAX falhas seguidas na janela.
function tentativas_bloqueada(array $t, string $chave, int $agora): bool
{
    return isset($t[$chave]) && ($t[$chave]['bloqueado_ate'] ?? 0) > $agora;
}

function tentativas_falhou(array &$t, string $chave, int $agora): void
{
    $r = $t[$chave] ?? ['n' => 0, 'desde' => $agora, 'bloqueado_ate' => 0];
    if ($agora - $r['desde'] > TENTATIVAS_JANELA) {
        $r = ['n' => 0, 'desde' => $agora, 'bloqueado_ate' => 0];
    }
    $r['n']++;
    if ($r['n'] >= TENTATIVAS_MAX) {
        $r['bloqueado_ate'] = $agora + TENTATIVAS_JANELA;
        $r['n'] = 0;
        $r['desde'] = $agora;
    }
    $t[$chave] = $r;
    // limpar registos velhos
    foreach ($t as $k => $v) {
        if (($v['bloqueado_ate'] ?? 0) < $agora && $agora - ($v['desde'] ?? 0) > TENTATIVAS_JANELA) {
            unset($t[$k]);
        }
    }
}

// Quem pode entrar e com que papel.
function utilizadores_conhecidos(array $cfg, array $imoveis): array
{
    $lista = [];
    foreach ($imoveis as $im) {
        $e = $im['proprietario']['email'];
        if ($e !== '') {
            $lista[$e] = ['email' => $e, 'nome' => $im['proprietario']['nome'] ?: $e, 'papel' => 'proprietario'];
        }
    }
    $adm = email_normalizado($cfg['administrador']['email'] ?? '');
    if ($adm !== '') {
        $lista[$adm] = ['email' => $adm, 'nome' => texto_curto($cfg['administrador']['nome'] ?? 'Administrador', 80), 'papel' => 'admin'];
    }
    return $lista;
}

function sessao_iniciar(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    $pasta = DESPESAS_DADOS . '/sessoes';
    garantir_pasta($pasta);
    session_save_path($pasta);
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    ini_set('session.gc_maxlifetime', (string) SESSAO_INATIVA);
    ini_set('session.gc_probability', '1');   // a pasta das sessões é nossa: ninguém mais a limpa
    ini_set('session.gc_divisor', '50');
    session_name('despesas_sessao');
    session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Strict']);
    session_start();
    $agora = time();
    if (isset($_SESSION['ultimo']) && $agora - (int) $_SESSION['ultimo'] > SESSAO_INATIVA) {
        $_SESSION = [];
        session_regenerate_id(true);
    }
    $_SESSION['ultimo'] = $agora;
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(32));
    }
}

function utilizador_atual(): ?array
{
    if (empty($_SESSION['email'])) {
        return null;
    }
    $conhecidos = utilizadores_conhecidos(ler_config(), imoveis_todos());
    $u = $conhecidos[$_SESSION['email']] ?? null;
    // Se o email deixou de existir (imóvel retirado, administrador trocado), a sessão deixa de valer.
    return ($u && $u['papel'] === ($_SESSION['papel'] ?? '')) ? $u : null;
}

function exigir_utilizador(?string $papel = null): array
{
    $u = utilizador_atual();
    if (!$u) {
        throw new ErroPedido('É preciso entrar.', 401);
    }
    if ($papel !== null && $u['papel'] !== $papel) {
        throw new ErroPedido('Sem permissão.', 403);
    }
    return $u;
}

function csrf_verificar(): void
{
    $enviado = (string) ($_SERVER['HTTP_X_CSRF'] ?? '');
    if (empty($_SESSION['csrf']) || !hash_equals((string) $_SESSION['csrf'], $enviado)) {
        throw new ErroPedido('Sessão expirada: recarregar a página.', 403);
    }
}

function entrar(string $email, string $senha, string $ip): array
{
    $email = email_normalizado($email);
    $cfg = ler_config();
    $conhecidos = utilizadores_conhecidos($cfg, imoveis_todos());
    $agora = time();
    return estado_alterar(function (array &$estado) use ($email, $senha, $ip, $conhecidos, $agora) {
        $chaves = ['ip:' . $ip, 'email:' . ($email !== '' ? $email : '?')];
        foreach ($chaves as $k) {
            if (tentativas_bloqueada($estado['tentativas'], $k, $agora)) {
                return ['ok' => false, 'erro' => 'Demasiadas tentativas. Esperar 15 minutos.'];
            }
        }
        $hash = $estado['senhas'][$email] ?? null;
        $u = $conhecidos[$email] ?? null;
        // Mesmo sem utilizador, verifica-se contra um hash qualquer: o tempo de resposta não denuncia quem existe.
        $ok = password_verify($senha, $hash ?: '$2y$12$abcdefghijklmnopqrstuuJlLcTQ8zv2t2Tz0Hy5yQ0eE4k3w8b6S');
        if (!$ok || !$u || !$hash) {
            foreach ($chaves as $k) {
                tentativas_falhou($estado['tentativas'], $k, $agora);
            }
            return ['ok' => false, 'erro' => 'Email ou password errados.'];
        }
        foreach ($chaves as $k) {
            unset($estado['tentativas'][$k]);
        }
        if (password_needs_rehash($hash, defined('PASSWORD_ARGON2ID') ? PASSWORD_ARGON2ID : PASSWORD_DEFAULT)) {
            $estado['senhas'][$email] = senha_hash($senha);
        }
        registar($estado, $email, 'entrou');
        return ['ok' => true, 'utilizador' => $u];
    });
}

function sessao_abrir(array $u): void
{
    session_regenerate_id(true);
    $_SESSION['email'] = $u['email'];
    $_SESSION['papel'] = $u['papel'];
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
    $_SESSION['ultimo'] = time();
}

function sessao_fechar(): void
{
    $_SESSION = [];
    if (session_status() === PHP_SESSION_ACTIVE) {
        session_regenerate_id(true);
        session_destroy();
    }
}
