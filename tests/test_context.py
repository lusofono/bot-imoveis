"""03/10: the customer's context — the owner's notes, our WhatsApp and SMS, their calls (by the phone) — on the card and
in the prompt of that customer's emails only; each entry goes with one click (a call is only hidden from it)."""
import pytest
from backend.ai import reply_prompt
from test_calls import call_notice
from test_properties import CUSTOMER, REF, lead, read, service  # noqa: F401 (service is a fixture)


def test_the_context_has_the_calls_the_notes_and_our_whatsapp_and_reaches_only_this_customers_prompt(service):
    read(service, [lead("1"), call_notice("k1"), call_notice("k2", answered=True)])  # the lead's phone: 900 000 001
    service.add_context(REF, CUSTOMER, "Prefere ser contactada depois das 18h.")
    service.add_context(REF, CUSTOMER, "", "whatsapp")
    with pytest.raises(ValueError, match="até 500"):
        service.add_context(REF, CUSTOMER, "")
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]
    assert card["contact_counts"] == {"calls": 2, "answered": 1, "whatsapp": 1, "sms": 0}
    texts = [entry["text"] for entry in card["context"]]
    assert "Ligou-nos — não atendida" in texts and "Ligou-nos — atendida (44 s)" in texts
    assert "Prefere ser contactada depois das 18h." in texts and "Abrimos o WhatsApp para lhe escrever" in texts
    prompt = reply_prompt(queue, ["1"])
    assert "Contexto deste cliente, fora dos emails" in prompt and "depois das 18h" in prompt and "não atendida" in prompt
    note = next(entry for entry in card["context"] if entry["source"] == "manual")
    service.delete_context(REF, CUSTOMER, note["id"])
    service.delete_context(REF, CUSTOMER, "k1")  # a call: hidden from the context
    [card] = service.pending()["properties"][0]["emails"]
    assert sorted(entry["text"] for entry in card["context"]) == ["Abrimos o WhatsApp para lhe escrever", "Ligou-nos — atendida (44 s)"]
    service.delete_context(REF, CUSTOMER)  # all
    [card] = service.pending()["properties"][0]["emails"]
    assert card["context"] == [] and "Contexto deste cliente" not in reply_prompt(service.pending()["properties"][0], ["1"])
