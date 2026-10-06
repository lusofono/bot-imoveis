<?php
// Despesas — o estado da aplicação num ficheiro JSON (dados/estado.json), com trinco para escritas concorrentes.
// São poucos dados (algumas faturas por mês): um ficheiro chega, não precisa de base de dados nem de extensões.

function estado_vazio(): array
{
    return [
        'versao' => 1,
        'instalado' => false,
        'senhas' => [],        // email → hash da password
        'tentativas' => [],    // chave → {n, desde, bloqueado_ate}
        'caixa' => ['uidvalidity' => null, 'vistos' => [], 'ultima_leitura' => null, 'ultimo_erro' => null, 'sem_pdf' => []],
        'faturas' => [],       // id → fatura
        'despesas' => [],      // id → despesa
        'respostas' => [],     // id → resposta de um inquilino («já paguei», com ou sem comprovativo)
        'comprovativos' => [], // id → comprovativo de pagamento (o ficheiro está em dados/comprovativos/<REF>/)
        'registo' => [],       // últimas ações (quem, o quê, quando)
    ];
}

function estado_caminho(?string $pasta = null): string
{
    return ($pasta ?? DESPESAS_DADOS) . '/estado.json';
}

function estado_ler(?string $pasta = null): array
{
    $caminho = estado_caminho($pasta);
    if (!is_file($caminho)) {
        return estado_vazio();
    }
    $f = fopen($caminho, 'rb');
    if (!$f) {
        throw new RuntimeException('Não consegui abrir o estado.');
    }
    flock($f, LOCK_SH);
    $bruto = stream_get_contents($f);
    flock($f, LOCK_UN);
    fclose($f);
    return estado_descodificar((string) $bruto);
}

function estado_descodificar(string $bruto): array
{
    $dados = json_decode($bruto, true);
    if (!is_array($dados)) {
        throw new RuntimeException('O ficheiro de estado está estragado (JSON inválido). Repor a última cópia (estado.json.anterior).');
    }
    return array_replace(estado_vazio(), $dados);
}

// Lê, aplica $fn (que recebe o estado por referência e devolve um resultado) e grava — tudo debaixo de um trinco.
function estado_alterar(callable $fn, ?string $pasta = null)
{
    $pasta = $pasta ?? DESPESAS_DADOS;
    garantir_pasta($pasta);
    $trinco = fopen($pasta . '/estado.lock', 'c');
    if (!$trinco) {
        throw new RuntimeException('Não consegui criar o trinco do estado.');
    }
    flock($trinco, LOCK_EX);
    try {
        $caminho = estado_caminho($pasta);
        $estado = is_file($caminho) ? estado_descodificar((string) file_get_contents($caminho)) : estado_vazio();
        $resultado = $fn($estado);
        if (is_file($caminho)) {
            @copy($caminho, $caminho . '.anterior');
            @chmod($caminho . '.anterior', 0600);
        }
        escrever_atomico($caminho, json_codificar($estado, true));
        return $resultado;
    } finally {
        flock($trinco, LOCK_UN);
        fclose($trinco);
    }
}

function registar(array &$estado, string $quem, string $oque): void
{
    $estado['registo'][] = ['quando' => agora(), 'quem' => $quem, 'oque' => $oque];
    if (count($estado['registo']) > 500) {
        $estado['registo'] = array_slice($estado['registo'], -500);
    }
}
