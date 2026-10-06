<?php
// Despesas — a página «Verificação»: o que o alojamento tem, se os dados estão protegidos, se os imóveis estão
// completos, a ligação ao Gmail (só com ?imap=1) e os testes do PHP (os mesmos de php app/testes.php).

function verificacao_correr(): array
{
    $itens = [];
    $item = function (string $nome, bool $ok, string $detalhe = '', bool $grave = true) use (&$itens) {
        $itens[] = ['nome' => $nome, 'ok' => $ok, 'detalhe' => $detalhe, 'grave' => $grave];
    };
    $item('PHP 7.4 ou mais recente', version_compare(PHP_VERSION, '7.4.0', '>='), 'versão ' . PHP_VERSION);
    $item('Extensão openssl (ligação TLS ao Gmail)', extension_loaded('openssl'));
    $item('Extensão json', function_exists('json_encode'));
    $item('Password com Argon2id', defined('PASSWORD_ARGON2ID'), defined('PASSWORD_ARGON2ID') ? '' : 'usa bcrypt, também é seguro', false);
    $item('mbstring ou iconv (nomes de ficheiro com acentos)', function_exists('mb_convert_encoding') || function_exists('iconv'), 'há conversão própria se faltarem', false);
    $item('Ligação por HTTPS', eh_https());
    $raizWeb = realpath((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''));
    $dados = realpath(DESPESAS_DADOS) ?: DESPESAS_DADOS;
    $item('Dados fora da pasta pública', !$raizWeb || !dentro_de($dados, $raizWeb), 'raiz web: ' . basename((string) $raizWeb));
    $item('Pasta dos dados com escrita', is_dir(DESPESAS_DADOS) && is_writable(DESPESAS_DADOS));
    $cfg = DESPESAS_DADOS . '/config.php';
    if (is_file($cfg)) {
        $perm = fileperms($cfg) & 0777;
        $item('config.php só legível pelo dono', ($perm & 0077) === 0, sprintf('permissões %o (devem ser 600)', $perm), false);
    }
    $c = ler_config();
    $item('Caixa de correio configurada', !empty($c['imap']['utilizador']) && !empty($c['imap']['app_password']), (string) ($c['imap']['utilizador'] ?? ''));
    $item('Administrador configurado', email_normalizado($c['administrador']['email'] ?? '') !== '');

    $imoveis = imoveis_todos();
    $item('Imóveis', count($imoveis) > 0, count($imoveis) . ' em dados/imoveis');
    foreach ($imoveis as $im) {
        $falta = [];
        if ($im['proprietario']['email'] === '') {
            $falta[] = 'email do proprietário';
        }
        if ($im['proprietario']['iban'] === '' && $im['proprietario']['mbway'] === '') {
            $falta[] = 'IBAN ou MB WAY do proprietário (para o inquilino pagar)';
        } elseif ($im['proprietario']['iban'] !== '' && !iban_valido($im['proprietario']['iban'])) {
            $falta[] = 'IBAN do proprietário inválido';
        }
        if ($im['inquilino']['nome'] === '') {
            $falta[] = 'nome do inquilino';
        }
        $item('Imóvel ' . $im['nome'], !$falta, $falta ? 'falta: ' . implode(', ', $falta) : count($im['remetentes']) . ' remetente(s)', false);
    }
    $item('Remetentes que contam', count(remetentes_permitidos($imoveis, $c)) > 0, count(remetentes_permitidos($imoveis, $c)) . ' endereço(s)');

    if (isset($_GET['imap'])) {
        $leitor = new LeitorImap();
        try {
            $imap = (array) ($c['imap'] ?? []);
            $leitor->ligar((string) ($imap['servidor'] ?? 'imap.gmail.com'), (int) ($imap['porta'] ?? 993), 20);
            $leitor->entrar((string) ($imap['utilizador'] ?? ''), (string) ($imap['app_password'] ?? ''));
            $leitor->examinar((string) ($imap['pasta'] ?? 'INBOX'));
            $leitor->sair();
            $item('Ligação ao Gmail (só leitura)', true, 'login e EXAMINE da caixa com sucesso');
        } catch (Throwable $e) {
            $leitor->sair();
            $item('Ligação ao Gmail (só leitura)', false, $e->getMessage());
        }
    }
    require_once __DIR__ . '/testes.php';
    return ['itens' => $itens, 'testes' => testes_php_correr(), 'php' => PHP_VERSION, 'versao' => DESPESAS_VERSAO];
}
