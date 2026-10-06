<?php
// Despesas — um cliente IMAP mínimo, SÓ DE LEITURA, sobre TLS (não precisa da extensão imap do PHP).
// Usa EXAMINE (abre a pasta em modo de leitura: o servidor não deixa mudar nada) e BODY.PEEK[] (não marca como lido).
// Não existe aqui nenhum comando que altere a caixa: nada de STORE, COPY, MOVE, EXPUNGE, APPEND nem DELETE.

class LeitorImap
{
    private $entrada = null;   // fluxo de onde se lê (o socket; nos testes, um ficheiro em memória)
    private $saida = null;     // fluxo onde se escreve (o mesmo socket; nos testes, outro)
    private $n = 0;
    private $proprios = false; // só se fecham os fluxos que este leitor abriu
    public $enviados = [];     // comandos enviados, sem a password (para diagnóstico e testes)

    public function ligar(string $servidor, int $porta = 993, int $timeout = 30): void
    {
        $ctx = stream_context_create(['ssl' => [
            'verify_peer' => true, 'verify_peer_name' => true, 'peer_name' => $servidor, 'SNI_enabled' => true,
        ]]);
        $erro = 0;
        $msg = '';
        $s = @stream_socket_client('ssl://' . $servidor . ':' . $porta, $erro, $msg, $timeout, STREAM_CLIENT_CONNECT, $ctx);
        if (!$s) {
            throw new RuntimeException('Não consegui ligar a ' . $servidor . ':' . $porta . ' (' . ($msg ?: 'erro ' . $erro)
                . '). O servidor pode não deixar sair ligações para a porta ' . $porta . '.');
        }
        stream_set_timeout($s, $timeout);
        $this->usarFluxos($s, $s);
        $this->proprios = true;
        $saudacao = $this->linha();
        if (strpos($saudacao, '* OK') !== 0) {
            throw new RuntimeException('O servidor IMAP não respondeu como esperado.');
        }
    }

    public function usarFluxos($entrada, $saida): void
    {
        $this->entrada = $entrada;
        $this->saida = $saida;
    }

    public static function aspas(string $s): string
    {
        return '"' . str_replace(['\\', '"'], ['\\\\', '\\"'], $s) . '"';
    }

    public function entrar(string $utilizador, string $senha): void
    {
        try {
            $this->comando('LOGIN ' . self::aspas($utilizador) . ' ' . self::aspas($senha), 'LOGIN ' . self::aspas($utilizador) . ' "***"');
        } catch (RuntimeException $e) {
            throw new RuntimeException('O Gmail recusou o login. Confirmar o email e a App Password (16 letras, criada com a verificação em 2 passos ligada).');
        }
    }

    // Abre a pasta só para leitura. Devolve o UIDVALIDITY (se mudar, os UIDs antigos deixam de valer).
    public function examinar(string $pasta): int
    {
        $r = $this->comando('EXAMINE ' . self::aspas($pasta));
        foreach ($r['linhas'] as $l) {
            if (preg_match('/\[UIDVALIDITY (\d+)\]/i', $l, $m)) {
                return (int) $m[1];
            }
        }
        return 0;
    }

    /** @return int[] */
    public function procurar(string $criterio): array
    {
        $r = $this->comando('UID SEARCH ' . $criterio);
        $uids = [];
        foreach ($r['linhas'] as $l) {
            if (preg_match('/^\* SEARCH\b(.*)$/i', $l, $m)) {
                foreach (preg_split('/\s+/', trim($m[1])) as $u) {
                    if (ctype_digit($u)) {
                        $uids[] = (int) $u;
                    }
                }
            }
        }
        sort($uids);
        return $uids;
    }

    // A mensagem inteira, sem a marcar como lida.
    public function buscar(int $uid): string
    {
        $r = $this->comando('UID FETCH ' . $uid . ' (BODY.PEEK[])');
        foreach ($r['respostas'] as $resp) {
            if (preg_match('/FETCH \(.*BODY\[\]/i', $resp['texto']) && $resp['literais']) {
                return $resp['literais'][0];
            }
        }
        throw new RuntimeException('Não consegui ler a mensagem ' . $uid . '.');
    }

    public function sair(): void
    {
        try {
            $this->comando('LOGOUT');
        } catch (Throwable $e) {
            // já está a sair: não interessa
        }
        if ($this->proprios && is_resource($this->entrada)) {
            @fclose($this->entrada);
        }
        $this->entrada = $this->saida = null;
    }

    private function comando(string $cmd, ?string $paraRegisto = null): array
    {
        if (preg_match('/^(?:UID\s+)?(STORE|COPY|MOVE|EXPUNGE|APPEND|DELETE|RENAME|SELECT|CREATE)\b/i', $cmd)) {
            throw new LogicException('Comando IMAP proibido nesta aplicação: só leitura.');
        }
        $this->n++;
        $tag = sprintf('D%04d', $this->n);
        $this->enviados[] = $tag . ' ' . ($paraRegisto ?? $cmd);
        $this->escrever($tag . ' ' . $cmd . "\r\n");
        $linhas = [];
        $respostas = [];
        while (true) {
            $resp = $this->resposta();
            if (strpos($resp['texto'], $tag . ' ') === 0) {
                $fim = substr($resp['texto'], strlen($tag) + 1);
                if (stripos($fim, 'OK') !== 0) {
                    throw new RuntimeException('IMAP: ' . $fim);
                }
                return ['linhas' => $linhas, 'respostas' => $respostas, 'fim' => $fim];
            }
            $linhas[] = $resp['texto'];
            $respostas[] = $resp;
        }
    }

    // Uma resposta completa: uma linha que pode trazer literais {n} (blocos de n bytes) a meio.
    private function resposta(): array
    {
        $texto = '';
        $literais = [];
        while (true) {
            $l = $this->linha();
            if (preg_match('/\{(\d+)\}\r?\n$/', $l, $m)) {
                $texto .= substr($l, 0, -strlen($m[0])) . '{' . $m[1] . '}';
                $literais[] = $this->ler((int) $m[1]);
                continue;
            }
            $texto .= rtrim($l, "\r\n");
            return ['texto' => $texto, 'literais' => $literais];
        }
    }

    private function linha(): string
    {
        $l = fgets($this->entrada, 65536);
        if ($l === false) {
            $this->falhou();
        }
        while (substr($l, -1) !== "\n") {
            $mais = fgets($this->entrada, 65536);
            if ($mais === false) {
                break;
            }
            $l .= $mais;
        }
        return $l;
    }

    private function ler(int $n): string
    {
        $dados = '';
        while (strlen($dados) < $n) {
            $p = fread($this->entrada, min(65536, $n - strlen($dados)));
            if ($p === false || $p === '') {
                $meta = stream_get_meta_data($this->entrada);
                if (!empty($meta['timed_out']) || feof($this->entrada)) {
                    $this->falhou();
                }
                continue;
            }
            $dados .= $p;
        }
        return $dados;
    }

    private function escrever(string $s): void
    {
        $total = strlen($s);
        $feito = 0;
        while ($feito < $total) {
            $n = fwrite($this->saida, substr($s, $feito));
            if ($n === false || $n === 0) {
                $this->falhou();
            }
            $feito += $n;
        }
    }

    private function falhou(): void
    {
        $meta = is_resource($this->entrada) ? stream_get_meta_data($this->entrada) : [];
        throw new RuntimeException(!empty($meta['timed_out']) ? 'IMAP: o servidor demorou demasiado a responder.' : 'IMAP: a ligação fechou-se.');
    }
}
