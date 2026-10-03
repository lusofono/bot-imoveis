"""03/10, RGPD: what the AI gets of a customer is minimised — the first name only (for the greeting), never the surnames,
the emails or the phone numbers, not even the ones written inside a message."""
from backend.ai import reply_prompt, scrub
from test_merge import follow_up
from test_properties import CUSTOMER, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def test_scrub_takes_out_contacts_and_surnames_but_keeps_dates_prices_and_the_first_name():
    text = ("Olá, sou a Ana Exemplo. Liguem-me para +351 912 345 678 ou 00351912345678, ou escrevam para "
            "ana.exemplo@example.com. Posso entrar a 01/10/2026; a renda de 1.200 € serve. Ana Exemplo")
    clean = scrub(text, "Ana Exemplo")
    assert "Exemplo" not in clean and "912" not in clean and "@" not in clean
    assert clean.count("[telefone]") == 2 and "[email]" in clean and "[apelido]" in clean
    assert "01/10/2026" in clean and "1.200 €" in clean and "Ana" in clean


def test_the_reply_prompt_carries_only_the_first_name_and_no_contacts(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana Exemplo.")
    read(service, [follow_up("c2", 1, "O meu telemóvel é o 912 345 678. Cumprimentos, Ana Exemplo", service)])
    prompt = reply_prompt(service.pending()["properties"][0], ["c2"])
    assert "Cliente: Ana" in prompt and "Ana Exemplo" not in prompt and "912 345 678" not in prompt
    assert CUSTOMER not in prompt and "[telefone]" in prompt
