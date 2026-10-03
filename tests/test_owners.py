"""02/10: a property's owner (property.owner_email) is not a customer: their emails go to a queue of their own (the
Proprietários tab), with their own conversation and a prompt of their own; never in the customers' cards, rounds,
contacts or the Painel's numbers. What came in from them as a customer moves to their side once their email is set."""
from backend.store import load_contacts
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

OWNER = "dono@example.com"


def from_owner(key, text="Como estão as visitas ao apartamento?", subject="Ponto de situação"):
    return {"gmail_message_id": key, "thread_id": f"o{key}", "message_id": f"<{key}@dono>",
            "from": [{"name": "Rui Dono", "email": OWNER}], "subject": subject, "body_text": text}


def set_owner(service):
    service.save_property({"reference": REF, "description": "Apartamento T3 na Rua Exemplo, Lisboa", "owner_email": OWNER})


def test_the_owners_email_goes_to_their_own_queue_never_the_customers(service):
    set_owner(service)
    read(service, [lead("1"), from_owner("o1")])
    queue = service.pending()["properties"][0]
    owner_card = next(email for email in queue["emails"] if email["id"] == "o1")
    assert owner_card["kind"] == "owner" and owner_card["owner"] is True and owner_card["interaction"] is None
    assert owner_card["recipient"]["email"] == OWNER and not owner_card["blocked"]
    data = service.load(REF)
    assert OWNER not in data["conversations"] and OWNER in data["owner_conversations"]
    assert [c["email"] for c in service.visit_candidates()["customers"]] == []  # the customer: no reply yet
    assert (OWNER, REF) not in load_contacts(service.folder)
    kinds = {task["kind"] for task in service.todo()["tasks"]}
    assert "owner" in kinds
    assert next(p for p in service.metrics()["properties"] if p["property_ref"] == REF)["pending"] == 1  # the customer's


def test_what_came_in_as_a_customer_moves_to_the_owner_once_their_email_is_set(service):
    owner_as_customer = lead("1", reply_to=(OWNER,), body_email=OWNER)
    read(service, [owner_as_customer])
    draft_and_send(service, "1", "Olá.")  # answered as if a customer
    assert OWNER in service.load(REF)["conversations"] and (OWNER, REF) in load_contacts(service.folder)
    set_owner(service)
    data = service.load(REF)
    assert OWNER not in data["conversations"] and data["owner_conversations"][OWNER]["sent_message_ids"]
    assert (OWNER, REF) not in load_contacts(service.folder)
    read(service, [from_owner("o2", "Obrigado. E a renda, mantemos?")])  # a reply of theirs: the owner's queue
    [card] = service.pending()["properties"][0]["emails"]
    assert card["kind"] == "owner" and [turn["who"] for turn in card["conversation"]][-1] == "cliente"


def test_the_owners_prompt_has_the_propertys_state_and_the_owners_know_how_and_the_send_keeps_their_side(service):
    set_owner(service)
    service.save_knowledge(None, "proprietarios.md", "# Com proprietários\n- Relatório às sextas-feiras.", scope="owners")
    assert (service.folder / "proprietarios" / "knowledge" / "proprietarios.md").exists()
    read(service, [lead("1"), from_owner("o1")])
    ref, prompt, chosen = service.owner_prompt_for(REF, ["o1"])
    assert ref == REF and [item["id"] for item in chosen["emails"]] == ["o1"]
    assert "PROPRIETÁRIO DO IMÓVEL" in prompt and "Relatório às sextas-feiras." in prompt
    assert "ESTADO DO IMÓVEL AGORA" in prompt and "Como estão as visitas" in prompt
    assert CUSTOMER not in prompt and "900 000 001" not in prompt  # never a customer's contact
    draft_and_send(service, "o1", "Bom dia, Rui. Esta semana houve um pedido novo.")
    data = service.load(REF)
    talk = data["owner_conversations"][OWNER]
    assert len(talk["sent_message_ids"]) == 1 and talk["history"][-1]["who"] == "nos"
    assert OWNER not in data["conversations"]
    sent = next(p for p in service.metrics()["properties"] if p["property_ref"] == REF)
    assert sum(day["sent"] for day in sent["by_day"]) == 0  # not a reply to a customer


def test_a_property_without_owner_email_keeps_reading_as_before(service):
    read(service, [from_owner("o1")])  # no owner set: an unknown sender is not ours
    assert service.pending()["properties"][0]["emails"] == []


def test_the_owner_is_set_in_the_owners_tab_and_written_to_first_with_a_subject_of_its_own(service):
    import pytest
    from test_properties import SMTP
    with pytest.raises(ValueError, match="endereço de email"):
        service.set_owner(REF, "não é email")
    with pytest.raises(ValueError, match="desta conta"):
        service.set_owner(REF, "owner@example.com")
    service.set_owner(REF, OWNER, "Rui Dono")
    prop = next(item for item in service.settings()["properties"] if item["reference"] == REF)
    assert (prop["owner_email"], prop["owner_name"]) == (OWNER, "Rui Dono")
    made = service.write_to_owner(REF, "Renda de novembro")
    [card] = [email for email in service.pending()["properties"][0]["emails"] if email["id"] == made["id"]]
    assert card["owner"] and card["outbound"] and card["new_subject"] == "Renda de novembro"
    _, prompt, _ = service.owner_prompt_for(REF, [made["id"]], extra="Pergunta se aceita baixar 50 €.")
    assert "és tu que lhe escreves" in prompt and "Pergunta se aceita baixar 50 €." in prompt
    draft_and_send(service, made["id"], "Bom dia, Rui. Escrevemos por causa da renda de novembro.")
    [sent] = SMTP.sent
    assert sent["Subject"] == "Renda de novembro" and sent["In-Reply-To"] is None and sent["To"].endswith(f"<{OWNER}>")
    assert service.load(REF)["owner_conversations"][OWNER]["history"][-1]["who"] == "nos"
    service.set_owner(REF, "")  # taken off
    assert next(item for item in service.settings()["properties"] if item["reference"] == REF)["owner_email"] is None
    with pytest.raises(ValueError, match="ainda não tem o email do proprietário"):
        service.write_to_owner(REF)


def test_the_owners_reply_in_a_customers_thread_leaves_the_customers_history(service):
    # 02/10: the owner answered in a customer's Gmail thread before their email was set: it was read as the customer's
    from test_merge import follow_up
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    owners_words = {**follow_up("o1", 1, "Por mim, a entrada pode ser quando quiserem.", service),
                    "from": [{"name": "Rui Dono", "email": OWNER}]}
    read(service, [owners_words])
    [card] = service.pending()["properties"][0]["emails"]
    assert card["blocked"] and card["kind"] == "follow_up"  # read as the customer's, in their thread
    set_owner(service)
    [card] = service.pending()["properties"][0]["emails"]
    assert card["kind"] == "owner" and card["recipient"]["email"] == OWNER and not card["blocked"]
    data = service.load(REF)
    assert "quando quiserem" not in str(data["conversations"][CUSTOMER]["history"])  # no longer the customer's words
    assert "quando quiserem" in str(data["owner_conversations"][OWNER]["history"])


def test_an_owner_with_no_property_has_an_inbox_and_is_answered_from_it(service):
    # 03/10: in the owners' list without a property: their emails go to the owners' inbox, never a customer's
    import pytest
    from unittest.mock import patch
    from test_properties import SMTP
    with pytest.raises(ValueError, match="endereço de email"):
        service.add_owner("não é email")
    service.add_owner("outro.dono@example.com", "Rita Dona")
    owners = {owner["email"]: owner for owner in service.pending()["owners"]["owners"]}
    assert owners["outro.dono@example.com"] == {"email": "outro.dono@example.com", "name": "Rita Dona", "refs": []}
    message = {**from_owner("r1", "Tenho um T2 para arrendar em breve."), "from": [{"name": "Rita", "email": "outro.dono@example.com"}]}
    read(service, [message])
    read(service, [message])  # the same email again: once
    assert service.pending()["properties"][0]["emails"] == []  # never a customer's card
    [card] = service.pending()["owners"]["inbox"]
    assert card["property_ref"] == "_caixa" and card["recipient"]["email"] == "outro.dono@example.com"
    ref, prompt, chosen = service.owner_prompt_for("_caixa", [card["id"]])
    assert ref == "_caixa" and "ainda não tem imóveis" in prompt and "T2 para arrendar" in prompt
    service.caixa_drafts([{"id": card["id"], "reply_text": "Bom dia, Rita. Com todo o gosto."}])
    preview = service.caixa_preview(card["id"])
    assert preview["to"] == "outro.dono@example.com"
    with pytest.raises(ValueError, match="mudou"):
        service.caixa_send(card["id"], "outra", True)
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.caixa_send(card["id"], preview["check"], True)
    [sent] = SMTP.sent
    assert sent["X-ARIA"] and sent["In-Reply-To"] == "<r1@dono>"
    assert service.pending()["owners"]["inbox"] == []
    made = service.write_to_owner("_caixa", "Visita ao T2", "outro.dono@example.com")
    [card] = service.pending()["owners"]["inbox"]
    assert card["id"] == made["id"] and card["outbound"] and card["new_subject"] == "Visita ao T2"
    service.caixa_dismiss(card["id"])
    assert service.pending()["owners"]["inbox"] == []
