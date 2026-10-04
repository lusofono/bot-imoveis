"""02/10: the notice board — the system's important messages for the owner, on the Painel: each one once, read by the
owner; from the sends (the conclusive 8th, the closing), the API's tank and a failed read. 04/10: no archiving — a
notice stays while what it says is true and leaves by itself once over; the owner may pin a note of 25 characters."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from backend.ai import CLOSING_FROM, CONCLUSIVE_AT
from backend.store import load_notices, save_notices
from test_later_interactions import writes_again
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def test_a_notice_comes_once_the_owner_reads_it_and_pins_a_note_but_cannot_archive_it(service):
    assert service.notify("a", "Primeiro aviso.", REF) is True
    assert service.notify("a", "Outra vez o mesmo.", REF) is False  # one per key
    service.notify("b", "Segundo aviso.", None, "bad", "replies")
    board = service.notices()
    assert [notice["text"] for notice in board["notices"]] == ["Segundo aviso.", "Primeiro aviso."]  # newest first
    assert board["unread"] == 2 and board["notices"][0]["level"] == "bad" and board["notices"][0]["tab"] == "replies"
    first = board["notices"][1]["id"]
    assert service.update_notices([first], "read")["unread"] == 1
    for action in ("archive", "delete"):
        with pytest.raises(ValueError, match="Ação desconhecida"):
            service.update_notices([first], action)
    # the owner's own note, up to 25 characters, spaces tidied; empty takes it off
    board = service.update_notices([first], "note", "  Liguei   ao dono  ")
    assert board["notices"][1]["note"] == "Liguei ao dono" and len(board["notices"]) == 2
    with pytest.raises(ValueError, match="25 caracteres"):
        service.update_notices([first], "note", "x" * 26)
    with pytest.raises(ValueError, match="um aviso de cada vez"):
        service.update_notices(None, "note", "Tudo")
    assert "note" not in service.update_notices([first], "note", "")["notices"][1]
    assert service.update_notices(None, "read")["unread"] == 0
    assert len(service.notices()["notices"]) == 2  # read, still on the board


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
    [closing] = service.notices()["notices"]  # the 8th's is over: the customer moved on to the closing
    assert "levou o email de fecho" in closing["text"] and closing["level"] == "ok"


def test_the_eighth_leaves_the_board_when_the_owner_puts_the_customer_on_the_grey_list(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    writes_again(service, CONCLUSIVE_AT - 1, "c2")
    draft_and_send(service, "c2", "Quer continuar com o processo?")
    assert len(service.notices()["notices"]) == 1
    queue = service.load(REF)
    queue["conversations"][CUSTOMER]["ignored"] = True
    service.save(queue, REF)
    assert service.notices()["notices"] == []


def test_green_and_grey_news_leave_after_a_week_the_others_stay(service):
    service.notify("noticia", "Tudo certo.", REF, "ok")
    service.notify("problema", "Algo por ver.", None, "warn")
    board = load_notices(service.folder)
    for notice in board["notices"]:
        notice["at"] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    save_notices(service.folder, board)
    assert [notice["text"] for notice in service.notices()["notices"]] == ["Algo por ver."]
    assert service.notify("noticia", "Tudo certo.", REF, "ok") is True  # over: the same news may come again


def test_the_tank_in_the_reserve_and_empty_each_leave_one_notice(service):
    read(service, [lead("1")])
    service.fill_fuel(REF, 1)
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.9)
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.01)
    [reserve] = service.notices()["notices"]
    assert "na reserva" in reserve["text"] and "0,10 €" in reserve["text"]
    service.log("openai_usage", model="gpt-6-luna", prompt_tokens=1, completion_tokens=1, reference=REF, cost_usd=0.2)
    [empty] = service.notices()["notices"]  # the reserve's is over: the empty one says it all
    assert "está vazio" in empty["text"] and empty["level"] == "bad"
    service.fill_fuel(REF, 5)
    assert service.notices()["notices"] == []  # filled again: over


def test_a_failed_read_leaves_a_notice_and_still_fails(service):
    with patch.object(type(service), "read_now", side_effect=ValueError("Falta a palavra-passe da app do Gmail.")):
        with pytest.raises(ValueError):
            service.read()
        with pytest.raises(ValueError):
            service.read()  # the same failure again the same day: one notice
    [notice] = service.notices()["notices"]
    assert notice["text"] == "A leitura do Gmail falhou: Falta a palavra-passe da app do Gmail." and notice["tab"] == "replies"
    with patch.object(type(service), "read_now", return_value={}):
        service.read()
    assert service.notices()["notices"] == []  # a read that worked: over


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
    draft_and_send(service, "1", "Olá, Ana.")
    assert service.notices()["notices"] == []  # answered: over


def test_a_customer_waiting_three_days_is_on_the_board_once_a_day(service):
    read(service, [lead("1")])
    data = service.load(REF)
    data["emails"][0]["date"] = "2026-01-01T10:00:00+00:00"  # long ago: waiting for our answer
    service.save(data, REF)
    service.waiting_notices(REF, data)
    service.waiting_notices(REF, data)  # the same day: one notice
    [notice] = service.notices()["notices"]
    assert notice["text"].startswith(f"1 cliente(s) de {REF} à espera da nossa resposta há 3 dias ou mais")
    draft_and_send(service, "1", "Olá, Ana.")
    assert service.notices()["notices"] == []  # answered: no one waits, over


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
    draft_and_send(service, "c2", "Obrigado, Ana.")
    assert service.notices()["notices"] == []  # answered: over
