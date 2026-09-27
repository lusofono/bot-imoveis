"""How far back each read goes (27/09): a new property's first read reaches back the days chosen when it was created
(45 by default), in and out; after that, every read goes on from the day before the last one."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from test_properties import CUSTOMER, REF, lead, read, service  # noqa: F401 (service is a fixture)

NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
NEW = "NOVO"


def ago(days, hours=0):
    return (NOW - timedelta(days=days, hours=hours)).isoformat()


def scan(service, incoming, sent=()):
    """read_messages as Gmail's All Mail goes: by arrival, the customers' emails before the owner's replies."""
    def fake(*args, accept=None, outgoing=None, accept_outgoing=None, **kwargs):
        kept = [message for message in incoming if accept(message)]
        outgoing.extend(message for message in sent if accept_outgoing(message))
        return kept, len(incoming) + len(sent), "[Gmail]/All Mail"
    with patch("backend.service.app_password", return_value="fake"), \
            patch("backend.service.read_messages", side_effect=fake) as fetch:
        return service.read(), fetch.call_args.args[3]


def create(service, days=None):
    return service.save_property({"reference": NEW, "description": "Apartamento T2 na Rua Exemplo",
                                  "sender": "reply@idealista.pt"}, days)


def queue(service, ref):
    return next(item for item in service.pending()["properties"] if item["property_ref"] == ref)


def test_a_property_never_read_goes_back_45_days_then_each_read_from_the_day_before_the_last(service):
    _, start = scan(service, [])
    assert start == (TODAY - timedelta(days=45)).isoformat()
    _, start = scan(service, [])
    assert start == (TODAY - timedelta(days=1)).isoformat()
    # The terminal and the MCP may still reach further back, once.
    with patch("backend.service.app_password", return_value="fake"), patch(
            "backend.service.read_messages", return_value=([], 0, "INBOX")) as fetch:
        service.read(days=30)
    assert fetch.call_args.args[3] == (TODAY - timedelta(days=30)).isoformat()


def test_the_days_are_chosen_when_the_property_is_created_and_the_page_is_told_where_it_starts(service):
    read(service, [])
    assert create(service, 20)["created"] is True
    assert queue(service, NEW)["read_from"] == (datetime.now().date() - timedelta(days=20)).isoformat()
    assert queue(service, REF)["read_from"] is None  # read already: it goes on from its last read
    _, start = scan(service, [])
    assert start == (datetime.now().date() - timedelta(days=20)).isoformat()
    assert queue(service, NEW)["read_from"] is None and queue(service, NEW)["last_read_at"]
    # Editing it later changes nothing about its reads.
    assert create(service, 40)["created"] is False
    assert queue(service, NEW)["read_from"] is None
    with pytest.raises(ValueError, match="primeira leitura"):
        service.save_property({"reference": "OUTRO", "description": "Moradia", "sender": "reply@idealista.pt"}, 0)
    assert service.settings()["first_read_days"] == 45 and "lookback_days" not in service.settings()


def test_a_new_propertys_wide_first_read_never_brings_old_mail_to_the_others(service):
    read(service, [])  # REF read today
    create(service)  # 45 days by default
    old_here, old_new, fresh = (dict(lead("r-old"), date=ago(30)), dict(lead("n-old", ref=NEW), date=ago(30)),
                                dict(lead("r-new", reply_to=("bruno.exemplo@example.com",)), date=ago(0, 1)))
    result, start = scan(service, [old_here, old_new, fresh])
    assert start == (datetime.now().date() - timedelta(days=45)).isoformat()
    assert [email["id"] for email in queue(service, REF)["emails"]] == ["r-new"]
    assert [email["id"] for email in queue(service, NEW)["emails"]] == ["n-old"]


def test_a_reply_written_in_gmail_to_a_customer_first_seen_in_this_same_read_is_recorded(service):
    create(service)
    notice = dict(lead("n1", ref=NEW), date=ago(10))
    reply = {"gmail_message_id": "gd1", "thread_id": "tn1", "message_id": "<d1@mail.gmail.com>", "date": ago(9),
             "from": [{"name": "Equipa", "email": "owner@example.com"}], "to": [{"name": "Ana Exemplo", "email": CUSTOMER}],
             "cc": [], "subject": "Re: Nova mensagem", "body_text": "Olá Ana, pode visitar amanhã às 18:00."}
    result, _ = scan(service, [notice], [reply])
    assert result["direct"] == 1
    [kept] = queue(service, NEW)["emails"]
    assert any("diretamente no Gmail" in warning for warning in kept["warnings"])
    assert service.load(NEW)["conversations"][CUSTOMER]["stage"] == 1
