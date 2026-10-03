"""03/10: «Reconstruir a partir do Gmail» — read twice N days back (our conversations rebuilt from Sent, then the
customers' replies to them) and PROPOSE what is missing — visits, surveys, the short list, the queue tidied — from our
emails' hidden mark, or because we asked for identification or the IRS; applied only when ticked; nothing is sent."""
from datetime import date, timedelta
from unittest.mock import patch
import pytest
from backend import mark
from backend.secrets import tag_key
from backend.store import load_visits
from test_direct_replies import direct
from test_properties import CUSTOMER, REF, lead, service  # noqa: F401 (service is a fixture)


def marked(key, hours_ago, text, fields, service):
    item = direct(key, hours_ago, text)
    item["aria"] = mark.header({"ref": REF, **fields}, tag_key(service.folder, "owner@example.com"))
    return item


def scan(service, incoming, sent, days=60):
    def fake(*args, accept=None, outgoing=None, accept_outgoing=None, **kwargs):
        taken = [message for message in incoming if not accept or accept(message)]  # by arrival: the notice before our reply
        if outgoing is not None:
            outgoing.extend(message for message in sent if accept_outgoing(message))
        return taken, len(incoming), "[Gmail]/All Mail"
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.read_messages", side_effect=fake):
        return service.rebuild_scan(REF, days)


def test_the_gmail_rebuilds_the_conversation_and_proposes_the_visit_the_survey_and_the_short_list(service):
    with pytest.raises(ValueError, match="de 1 a 365"):
        service.rebuild_scan(REF, 0)
    visit = (date.today() - timedelta(days=5)).isoformat() + "T17:30"
    first = lead("1")
    first["thread_id"] = "t1"
    first["date"] = (date.today() - timedelta(days=9)).isoformat() + "T10:00:00+00:00"
    sent = [marked("m1", 200, "Olá, Ana. Quando pode visitar?", {"n": 1, "k": "lead"}, service),
            marked("m2", 150, "Fica marcada a visita.", {"n": 3, "k": "follow_up", "vis": visit}, service),
            marked("m3", 100, "Obrigado pela visita: 1) O imóvel: 2) O consultor:", {"n": 4, "k": "visit_thanks", "vis": visit}, service),
            direct("m4", 50, "Para avançarmos, envie-nos o IRS e os recibos de vencimento.")]  # an old one, without the mark
    survey = {"gmail_message_id": "s1", "thread_id": "t1", "message_id": "<s1@cliente>", "date": "",
              "from": [{"name": "Ana", "email": CUSTOMER}], "in_reply_to": "<m3@mail.gmail.com>", "subject": "Re: Nova mensagem",
              "body_text": "1) O imóvel: 5\n2) O consultor: 4\n4) Mantém o interesse? sim"}
    from test_direct_replies import at
    survey["date"] = at(90)
    result = scan(service, [first, survey], sent)
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["stage"] >= 4 and len(conversation["marks"]) == 3  # what our emails were, from their mark
    kinds = {(entry["kind"], entry.get("source")) for entry in result["proposals"]}
    assert ("visit", "marca") in kinds and ("survey", "marca") in kinds and ("shortlist", "pedido de documentos") in kinds
    assert load_visits(service.folder, REF)["slots"] == []  # only proposed
    ids = [entry["id"] for entry in result["proposals"] if entry["kind"] in ("visit", "survey", "shortlist")]
    done = service.rebuild_apply(REF, ids)
    assert done == {"visit": 1, "survey": 1, "shortlist": 1}
    [slot] = load_visits(service.folder, REF)["slots"]
    assert (slot["customer"], slot["at"], slot["source"]) == (CUSTOMER, visit.replace("T", " "), "reconstrucao")
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation["visit_survey"]["imovel"] == 5 and conversation["selection"]["status"] == "shortlist"
    assert service.rebuild_apply(REF, ids) == {}  # applied once: the proposals are gone
