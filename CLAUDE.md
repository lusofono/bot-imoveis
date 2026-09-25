# Regras para quem trabalha neste projeto (Claude e outros agentes)

Antes de mexer, lê o `README.md`, o `docs/PLANO-VERSAO-LOCAL.md`, o `docs/DECISOES.md` e o `CHANGELOG.md`.
O utilizador escreve em português de Portugal; as respostas e os textos da página também.

## Testar
- **Testa com código, nunca com o browser.** Não abras a página no preview ou no browser nem tires capturas de
  ecrã para testar: corre os testes (`.venv/bin/python -m pytest -q`) e faz verificações em código (por exemplo,
  confirmar que o CSS e o SVG são válidos, ou que uma chamada à API devolve o que deve). A verificação visual
  faz o utilizador, que é mais rápido e gasta menos tokens. (Pedido do utilizador, 25/09/2026.)
- Experiências só em pastas de demonstração (`bot-mail demo <pasta>`) ou em cópias; nunca em `data/`.

## Vários agentes ao mesmo tempo
- Pode haver mais do que um agente a trabalhar nesta pasta (por exemplo, um fork da mesma conversa). Cada um
  mexe só nos ficheiros da sua tarefa: um pedido só de design toca apenas no CSS (`frontend/themes/*.css`,
  `frontend/style.css`), nunca em `backend/` nem em `frontend/app.js`.
- Antes de editar, vê o `git status`: ficheiros alterados que não são teus são de outro agente. Não os revertas
  nem os sobrescrevas.
- Enquanto outro agente estiver a trabalhar, não mexas na versão nem no `CHANGELOG.md` sem combinar: fica para
  quem juntar o trabalho.

## Sempre
- Cada pedido que muda a página ou o backend sobe a versão em `pyproject.toml` e ganha uma entrada no
  `CHANGELOG.md` (a mais recente primeiro).
- O repositório é público: nada de dados reais no Git (emails, telefones, moradas, nomes de clientes, chaves).
  A pasta `data/` nunca entra.
- Commit e push só quando o utilizador pedir.
