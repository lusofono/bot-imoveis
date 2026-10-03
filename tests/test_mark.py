"""02/10: the hidden mark — every email the ARIA sends carries, in ASCII and out of sight, what it was (the X-ARIA header,
in our own copy) and a Message-ID that the customer's reply carries back; both signed with a key that stays on the Mac."""
from backend import mark
from backend.secrets import tag_key
from test_merge import follow_up
from test_properties import REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def test_the_mark_is_sealed_reads_back_only_with_the_key_and_a_changed_one_is_refused():
    value = mark.header({"ref": "AP_X", "n": 4, "k": "docs_request", "sel": "suplente", "vis": "uma hora", "x": "1"}, "chave")
    # it travels with the email («Mostrar original»): nothing readable in it
    assert value.startswith("1.") and "suplente" not in value and "AP_X" not in value and value.isascii()
    assert mark.read_header(value, "chave") == {"ref": "AP_X", "n": "4", "k": "docs_request", "sel": "suplente"}
    assert mark.read_header(value, "outra") is None and mark.read_header(value, None) is None
    changed = value[:-3] + ("a" if value[-3] != "a" else "b") + value[-2:]
    assert mark.read_header(changed, "chave") is None and mark.read_header("qualquer coisa", "chave") is None
    ours = mark.message_id({"n": 4, "k": "visit_proposal"}, "chave")
    assert "visit_proposal" not in ours and ours.endswith("@gmail.com>")
    assert mark.read_message_id(f"<x@y> {ours}", "chave") == {"n": 4, "k": "visit_proposal"}
    assert mark.read_message_id(ours, "outra") is None and mark.read_message_id("<CAF123@mail.gmail.com>", "chave") is None
    assert mark.message_id({"n": 4, "k": "lead"}, "chave") != mark.message_id({"n": 4, "k": "lead"}, "chave")  # unique


def test_every_email_sent_carries_the_mark_and_the_reply_brings_it_back(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    [sent] = SMTP.sent
    key = tag_key(service.folder, "owner@example.com")
    assert mark.read_header(sent["X-ARIA"], key) == {"ref": REF, "n": "1", "k": "lead"}
    assert mark.read_message_id(sent["Message-ID"], key) == {"n": 1, "k": "lead"}
    assert "lead" not in sent["Message-ID"] and REF not in sent["X-ARIA"]  # sealed
    # the customer's reply carries our Message-ID: it is their conversation, and it says which of our emails it answers
    reply = follow_up("c2", 1, "Somos dois.", service)
    assert reply["in_reply_to"] == sent["Message-ID"]
    read(service, [reply])
    [card] = service.pending()["properties"][0]["emails"]
    assert card["kind"] == "follow_up" and card["interaction"] == 2
    assert mark.read_message_id(reply["in_reply_to"], key)["n"] == 1
    service.farewell(REF, "c2")
    draft_and_send(service, "c2", "Obrigado; ficamos por aqui.")
    assert mark.read_header(SMTP.sent[0]["X-ARIA"], key)["k"] == "farewell"
    assert mark.read_header(SMTP.sent[0]["X-ARIA"], key)["n"] == "2"
