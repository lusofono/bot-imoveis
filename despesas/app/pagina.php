<?php
// Despesas — a porta de entrada: obriga a HTTPS, recusa trabalhar com os dados dentro da pasta pública,
// encaminha a API (?a=…) e serve a página (o resto desenha-o o app.js).

function pagina_tratar(): void
{
    if (!eh_https()) {
        $host = preg_replace('/[^A-Za-z0-9.\-:]/', '', (string) ($_SERVER['HTTP_HOST'] ?? ''));
        if ($host !== '') {
            header('Location: https://' . $host . ($_SERVER['REQUEST_URI'] ?? '/'), true, 301);
            return;
        }
        http_response_code(403);
        echo 'Só por HTTPS.';
        return;
    }
    $acao = isset($_GET['a']) ? (string) $_GET['a'] : '';
    cabecalhos_seguranca($acao !== 'pdf' && $acao !== 'comprovativo');

    $raizWeb = realpath((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''));
    $dados = realpath(DESPESAS_DADOS) ?: DESPESAS_DADOS;
    if ($raizWeb && dentro_de($dados, $raizWeb)) {
        http_response_code(500);
        header('Content-Type: text/html; charset=utf-8');
        echo '<!doctype html><meta charset="utf-8"><title>Despesas</title><p style="font:16px sans-serif;max-width:40em;margin:3em auto">'
            . 'A pasta <b>dados</b> está dentro da pasta pública do site: as faturas e as passwords ficariam acessíveis por endereço. '
            . 'Mudar a raiz do (sub)domínio para a pasta <b>despesas/publico</b> (ver o README). Até lá, a aplicação não trabalha.</p>';
        return;
    }
    if ($acao !== '') {
        api_tratar($acao);
        return;
    }
    pagina_html();
}

function pagina_html(): void
{
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    $v = rawurlencode(DESPESAS_VERSAO);
    $ficheiros = ['motor/util.js', 'motor/pdf.js', 'motor/regras.js', 'motor/tabela.js', 'app.js'];
    $scripts = '';
    foreach ($ficheiros as $f) {
        $scripts .= '<script src="' . $f . '?v=' . $v . '" defer></script>' . "\n";
    }
    echo '<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Despesas</title>
<link rel="icon" href="icone.svg" type="image/svg+xml">
<link rel="stylesheet" href="estilo.css?v=' . $v . '">
</head>
<body>
<header class="capota">
  <div class="capota-dentro">
    <a class="marca" href="./" title="Despesas · versão ' . htmlspecialchars(DESPESAS_VERSAO) . '"><span class="bandeira" aria-hidden="true"></span><span class="marca-nome">Despesas</span><span class="marca-por">por BigLearn</span></a>
    <nav id="menu" class="menu" aria-label="Secções"></nav>
    <div id="quem" class="quem"></div>
  </div>
</header>
<main id="app" class="conteudo"><p class="a-carregar">A carregar…</p></main>
<footer class="rodape"><span id="versao">v' . htmlspecialchars(DESPESAS_VERSAO) . '</span></footer>
<div id="aviso" class="aviso" role="status" aria-live="polite"></div>
' . $scripts . '</body>
</html>';
}
