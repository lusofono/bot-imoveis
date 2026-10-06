<?php
// Despesas — as respostas dos inquilinos («já paguei», com ou sem comprovativo) e os comprovativos de pagamento.
// Os comprovativos ficam numa pasta por imóvel: dados/comprovativos/<REF>/AAAA-MM-DD_<id>_<nome>, fora da pasta
// pública, e só se abrem com login (o administrador; o proprietário, os do seu imóvel).
// Registar «paga» a partir de uma resposta é um clique do administrador: um email pode ser sobre outra coisa ou
// cobrir só parte das despesas. Confirmar se o dinheiro entrou mesmo fica para as pessoas (o «Recebi» do proprietário).

const TIPOS_COMPROVATIVO = ['application/pdf' => 'pdf', 'image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp', 'image/heic' => 'heic'];
const COMPROVATIVO_MAX = 15 * 1024 * 1024;

function comprovativos_pasta(string $ref, ?string $base = null): string
{
    return ($base ?? DESPESAS_DADOS . '/comprovativos') . '/' . preg_replace('/[^A-Za-z0-9_-]/', '_', $ref);
}

// Guarda um comprovativo (se for PDF ou imagem e ainda não existir) e devolve o id; null se não servir.
function comprovativo_guardar(array &$estado, string $ref, string $nome, string $dados, string $origem, string $quando, ?string $base = null): ?string
{
    $tipo = mime_tipo_real($dados);
    if (!isset(TIPOS_COMPROVATIVO[$tipo]) || strlen($dados) > COMPROVATIVO_MAX) {
        return null;
    }
    $sha = hash('sha256', $dados);
    foreach ($estado['comprovativos'] as $c) {
        if ($c['sha256'] === $sha && $c['imovel'] === $ref) {
            return $c['id'];
        }
    }
    $id = id_novo();
    $base_nome = preg_replace('/\.[A-Za-z0-9]{1,5}$/', '', $nome);
    $base_nome = trim(preg_replace('/[^A-Za-z0-9._-]+/', '-', iconv_ou_ascii($base_nome)), '-.') ?: 'comprovativo';
    $ficheiro = substr($quando, 0, 10) . '_' . $id . '_' . substr($base_nome, 0, 60) . '.' . TIPOS_COMPROVATIVO[$tipo];
    escrever_atomico(comprovativos_pasta($ref, $base) . '/' . $ficheiro, $dados);
    $estado['comprovativos'][$id] = [
        'id' => $id, 'imovel' => $ref, 'nome' => texto_curto($nome, 150), 'ficheiro' => $ficheiro, 'tipo' => $tipo,
        'tamanho' => strlen($dados), 'sha256' => $sha, 'recebido_em' => $quando, 'origem' => $origem,
    ];
    return $id;
}

// Nomes de ficheiro sem acentos (para a pasta ser fácil de ver no cPanel), sem depender de iconv.
function iconv_ou_ascii(string $s): string
{
    $mapa = ['á' => 'a', 'à' => 'a', 'â' => 'a', 'ã' => 'a', 'ä' => 'a', 'é' => 'e', 'è' => 'e', 'ê' => 'e', 'í' => 'i', 'ó' => 'o', 'ò' => 'o',
        'ô' => 'o', 'õ' => 'o', 'ö' => 'o', 'ú' => 'u', 'ü' => 'u', 'ç' => 'c', 'ñ' => 'n', 'Á' => 'A', 'À' => 'A', 'Â' => 'A', 'Ã' => 'A',
        'É' => 'E', 'Ê' => 'E', 'Í' => 'I', 'Ó' => 'O', 'Ô' => 'O', 'Õ' => 'O', 'Ú' => 'U', 'Ç' => 'C', 'º' => 'o', 'ª' => 'a'];
    return strtr($s, $mapa);
}

// O texto da resposta sem o que vem citado da mensagem anterior.
function resposta_excerto(string $texto): string
{
    $linhas = preg_split("/\r?\n/", str_replace("\r\n", "\n", $texto)) ?: [];
    $boas = [];
    foreach ($linhas as $l) {
        $t = trim($l);
        if ($t !== '' && $t[0] === '>') {
            break;
        }
        if (preg_match('/^(On .+ wrote:|Em .+ escreveu:|No dia .+ escreveu:|-{2,}\s*(Original|Mensagem original|Forwarded)|De: .+@|From: .+@|Enviado do meu)/i', $t)) {
            break;
        }
        $boas[] = $t;
    }
    $s = trim(preg_replace("/\n{3,}/", "\n\n", implode("\n", $boas)) ?? '');
    return texto_curto($s, 600);
}

// O que a resposta parece dizer (só sugestão: quem decide é o administrador).
function resposta_sugestao(string $excerto, bool $temComprovativo): ?string
{
    $d = strtolower(iconv_ou_ascii($excerto));
    if (preg_match('/^\W*(nao|ainda nao)\b|\b(ainda nao (paguei|fiz|transferi)|nao (paguei|consegui))\b/u', $d)) {
        return 'nao';
    }
    if ($temComprovativo || preg_match('/^\W*sim\b|\b(ja paguei|paguei|ja transferi|transferi|ja esta pago|esta pago|pagamento (feito|efetuado)|segue (o )?comprovativo|em anexo)\b/u', $d)) {
        return 'sim';
    }
    return null;
}

// Um email de um inquilino: guarda os comprovativos na pasta do imóvel e cria a resposta «por ver».
function resposta_de_email(array &$estado, array $m, string $ref, string $quando, ?string $base = null): string
{
    $ids = [];
    foreach ($m['anexos'] as $ax) {
        $id = comprovativo_guardar($estado, $ref, $ax['nome'], $ax['dados'], 'email', $quando, $base);
        if ($id !== null && !in_array($id, $ids, true)) {
            $ids[] = $id;
        }
    }
    $excerto = resposta_excerto((string) $m['texto']);
    $rid = id_novo();
    $estado['respostas'][$rid] = [
        'id' => $rid, 'imovel' => $ref, 'de' => $m['de'], 'assunto' => $m['assunto'], 'recebido_em' => $m['data'] ?: $quando,
        'texto' => $excerto, 'comprovativos' => $ids, 'sugestao' => resposta_sugestao($excerto, (bool) $ids),
        'estado' => 'por_ver', 'origem' => 'email',
    ];
    foreach ($ids as $id) {
        $estado['comprovativos'][$id]['resposta'] = $rid;
    }
    return $rid;
}

// Os emails dos inquilinos (minúsculas) → a referência do imóvel.
function inquilinos_emails(array $imoveis): array
{
    $mapa = [];
    foreach ($imoveis as $im) {
        $e = $im['inquilino']['email'] ?? '';
        if ($e !== '' && !isset($mapa[$e])) {
            $mapa[$e] = $im['ref'];
        }
    }
    return $mapa;
}
