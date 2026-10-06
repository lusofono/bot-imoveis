<?php
// Exemplo FICTÍCIO da configuração. Copiar para dados/config.php (fora do Git e fora da pasta pública),
// preencher, e deixar com permissões 600:  chmod 600 dados/config.php
return [
    // A caixa de correio das faturas (Gmail): só leitura. A password é uma App Password da Google
    // (Conta Google → Segurança → Verificação em 2 passos → Palavras-passe de apps), nunca a password da conta.
    'imap' => [
        'servidor' => 'imap.gmail.com',
        'porta' => 993,
        'utilizador' => 'contas@example.com',
        'app_password' => 'xxxx xxxx xxxx xxxx',
        'pasta' => 'INBOX',
    ],

    // Quem gere tudo. Escolhe a password na primeira entrada, com o código de instalação abaixo.
    'administrador' => ['email' => 'admin@example.com', 'nome' => 'Administrador'],

    // Código para a primeira entrada (pelo menos 12 caracteres; depois de instalado deixa de servir).
    'codigo_instalacao' => 'trocar-por-um-codigo-comprido',

    // Endereços do administrador que também enviam faturas (com o proprietário ou o imóvel no assunto).
    'remetentes_administrador' => ['admin@example.com'],

    // Ler emails a partir desta data (a primeira leitura não vai buscar anos de correio).
    'ler_desde' => '2026-09-01',

    // Dias sem resposta do inquilino (depois do envio, de um lembrete ou de um «ainda não paguei») até a página sugerir
    // um lembrete.
    'lembrete_dias' => 5,

    // Para onde os inquilinos enviam a confirmação e o comprovativo (vai em CC no «Abrir email»). Por omissão: a caixa
    // das faturas, que a aplicação lê.
    // 'email_respostas' => 'contas@example.com',

    // Assinatura das mensagens para os inquilinos (cada imóvel pode ter a sua em imovel.json → mensagem).
    'assinatura' => 'Gestão de Contas',
];
