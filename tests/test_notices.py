"""02/10: the notice board — the system's important messages for the owner, on the Painel: each one once, read or
archived by the owner; from the sends (the conclusive 8th, the closing), the API's tank and a failed read."""
from unittest.mock import patch
import pytest
from backend.ai import CLOSING_FROM, CONCLUSIVE_AT
from test_later_interactions import writes_again
from test_properties import REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def test_a_notice_comes_once_and_the_owner_reads_or_archives_it(service):
    assert service.notify("a", "Primeiro aviso.", REF) is True
    assert service.notify("a", "Outra vez o mesmo.", REF) is False  # one per key
    service.notify("b", "Segundo aviso.", None, "bad", "replies")
    board = service.notices()
    assert [notice["text"] for notice in board["notices"]] == ["Segundo aviso.", "Primeiro aviso."]  # newest first
    assert board["unread"] == 2 and board["notices"][0]["level"] == "bad" and board["notices"][0]["tab"] == "replies"
    first = board["notices"][1]["id"]
    assert service.update_notices([first], "read")["unread"] == 1
    board = service.update_notices([first], "archive")
    assert [notice["text"] for notice in board["notices"]] == ["Segundo aviso."]
    assert service.update_notices(None, "archive") == {"notices": [], "unread": 0}
    with pytest.raises(ValueError, match="Ação desconhecida"):
        service.update_notices(None, "delete")


def test_the_conclusive_eighth_and_the_closing_leave_a_notice(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    writes_again(service, CONCLUSIVE_AT - 1, "c2")
    assert service.notices()["notices"] == []
    draft_and_send(service, "c2", "Quer continuar com o processo?")
    [notice] = service.notices()["notices"]
    assert f"{CONCLUSIVE_AT}.ª interação sem visita marcada" in notice["text"] and notice["ref"] == REF
    assert notice["tab"] == "contacts" and notice["level"] == "warn" and "Ana" in notice["text"]
    writes_again(service, CLOSING_FROM - 1, "c3")
    draft_and_send(service, "c3", "Obrigado pelo seu interesse.")
    closing, _ = service.notices()["notices"]
    assert "levou o email de fecho" in closing["text"] and closing["level"] == "info"


def test_the_tank_in_the_reserve_and_empty_each_leave_one_notice(service):
    read(service, [lead("1")])
    service.fill_fuel(REF, 1)
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.9)
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.01)
    [reserve] = service.notices()["notices"]
    assert "na reserva" in reserve["text"] and "0,10 €" in reserve["text"]
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.2)
    empty, _ = service.notices()["notices"]
    assert "está vazio" in empty["text"] and empty["level"] == "bad"


def test_a_failed_read_leaves_a_notice_and_still_fails(service):
    with patch.object(type(service), "read_now", side_effect=ValueError("Falta a palavra-passe da app do Gmail.")):
        with pytest.raises(ValueError):
            service.read()
        with pytest.raises(ValueError):
            service.read()  # the same failure again the same day: one notice
    [notice] = service.notices()["notices"]
    assert notice["text"] == "A leitura do Gmail falhou: Falta a palavra-passe da app do Gmail." and notice["tab"] == "replies"


def test_the_ai_flags_an_insulting_message_on_its_card_and_on_the_board(service):
    from backend.ai import parse_alerts, short_id
    read(service, [lead("1")])
    queue = service.pending()["properties"][0]
    answer = ('{"respostas": [{"id": "' + short_id("1") + '", "reply_text": "Olá.", "alerta": "insulto", '
              '"alerta_motivo": "O cliente insulta a agência."}]}')
    alerts = parse_alerts(answer, queue)
    assert alerts == [{"id": "1", "kind": "insulto", "reason": "O cliente insulta a agência."}]
    assert parse_alerts('{"respostas": [{"id": "' + short_id("1") + '", "reply_text": "Olá."}]}', queue) == []
    service.flag_alerts(REF, alerts)
    [card] = service.pending()["properties"][0]["emails"]
    assert any("insultuosa" in warning for warning in card["warnings"])
    [notice] = service.notices()["notices"]
    assert "mensagem insultuosa — O cliente insulta a agência." in notice["text"] and notice["level"] == "bad"
    assert "lista negra" in notice["text"] and notice["tab"] == "replies"


def test_a_customer_waiting_three_days_is_on_the_board_once_a_day(service):
    read(service, [lead("1")])
    data = service.load(REF)
    data["emails"][0]["date"] = "2026-01-01T10:00:00+00:00"  # long ago: waiting for our answer
    service.waiting_notices(REF, data)
    service.waiting_notices(REF, data)  # the same day: one notice
    [notice] = service.notices()["notices"]
    assert notice["text"].startswith(f"1 cliente(s) de {REF} à espera da nossa resposta há 3 dias ou mais")


def test_someone_on_the_short_list_who_writes_is_urgent_on_the_board(service):
    from test_merge import follow_up
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    queue = service.load(REF)
    queue["conversations"]["ana.exemplo@example.com"]["selection"] = {"status": "chosen"}
    service.save(queue, REF)
    read(service, [follow_up("c2", 1, "Já tenho os documentos.", service)])
    [notice] = service.notices()["notices"]
    assert "na short list (Escolhido)" in notice["text"] and notice["level"] == "bad" and notice["tab"] == "replies"
    [card] = service.pending()["properties"][0]["emails"]
    assert any("short list" in warning for warning in card["warnings"])
