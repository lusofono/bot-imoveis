"""02/10: after the 4th interaction — a customer who goes on writing with no visit booked — three steps (they had no
prompt, and the draft came back empty): the 5th to the 7th answer what is asked and wait for the owner (the grey list,
if it makes sense); the 8th is conclusive and asks the owner to step in; from the 9th on, the closing — the rounds
leave them out."""
from backend.ai import (CLOSING_FROM, CLOSING_REPLY_RULE, CONCLUSIVE_AT, CONCLUSIVE_REPLY_RULE, LATER_REPLY_RULE,
                        reply_prompt)
from test_merge import follow_up
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def writes_again(service, stage, key):
    """The customer was proposed a visit, asked for another date, and writes again after our stage-th email."""
    queue = service.load(REF)
    conversation = queue["conversations"][CUSTOMER]
    conversation["stage"], conversation["visit"] = stage, "outra_data"
    service.save(queue, REF)
    read(service, [follow_up(key, 1, "Ainda não sei quando posso.", service)])
    return service.pending()["properties"][0]


def intervene_task(service):
    return [task for task in service.todo()["tasks"] if task["kind"] == "intervene"]


def test_the_fifth_waits_the_eighth_asks_the_owner_and_the_ninth_closes(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")

    queue = writes_again(service, 4, "c2")
    [card] = queue["emails"]
    assert (card["interaction"], card["conclusive_reply"], card["closing_reply"]) == (5, False, False)
    assert any("lista cinzenta" in warning for warning in card["warnings"])
    instructions = queue["instructions"]
    assert "sem prompt configurada; avisa o proprietário" not in instructions
    assert all(rule in instructions for rule in (LATER_REPLY_RULE, CONCLUSIVE_REPLY_RULE, CLOSING_REPLY_RULE))
    assert "interação: 5.ª |" in reply_prompt(queue, ["c2"])

    draft_and_send(service, "c2", "Vamos ver e respondemos em breve.")
    queue = writes_again(service, CONCLUSIVE_AT - 1, "c3")
    [card] = queue["emails"]
    assert (card["interaction"], card["conclusive_reply"], card["closing_reply"]) == (CONCLUSIVE_AT, True, False)
    assert any("Precisa da tua intervenção" in warning for warning in card["warnings"])
    assert f"interação: {CONCLUSIVE_AT}.ª, conclusiva |" in reply_prompt(queue, ["c3"])
    assert intervene_task(service) == []  # the 8th not sent yet
    draft_and_send(service, "c3", "Quer continuar com o processo?")
    [task] = intervene_task(service)  # sent: the owner is asked to step in, in «A fazer»
    assert task["tab"] == "contacts" and task["count"] == 1

    queue = writes_again(service, CLOSING_FROM - 1, "c4")
    [card] = queue["emails"]
    assert (card["interaction"], card["conclusive_reply"], card["closing_reply"]) == (CLOSING_FROM, False, True)
    assert f"interação: fecho ({CLOSING_FROM}.ª) |" in reply_prompt(queue, ["c4"])

    # once the closing went out, the rounds leave them out (we stopped insisting) and the task is gone
    draft_and_send(service, "c4", "Obrigado pelo seu interesse.")
    [customer] = service.visit_candidates()["customers"]
    assert customer["state"] == "closed" and "fecho" in customer["reason"]
    assert intervene_task(service) == []


def test_the_oficina_changes_the_closing_for_every_property(service):
    read(service, [lead("1")])
    service.save_common_prompts({"closing_reply": "Despede-te em duas linhas."})
    instructions = service.pending()["properties"][0]["instructions"]
    assert "Despede-te em duas linhas." in instructions and CLOSING_REPLY_RULE not in instructions
    service.save_common_prompts({"closing_reply": CLOSING_REPLY_RULE})  # the code's own again: it follows the code
    assert CLOSING_REPLY_RULE in service.pending()["properties"][0]["instructions"]


def test_closing_the_contact_by_hand_is_a_goodbye_and_no_more_rounds_without_the_grey_list(service):
    # 02/10: «Encerrar contacto»: any time, the reply becomes the closing; once sent, closed — not ignored
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [follow_up("c2", 1, "Ainda estou a pensar.", service)])
    service.farewell(REF, "c2")
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]
    assert card["farewell"] and card["closing_reply"] and not card["conclusive_reply"]
    assert "interação: fecho (encerrar contacto) |" in reply_prompt(queue, ["c2"])
    draft_and_send(service, "c2", "Obrigado pelo seu interesse; ficamos por aqui.")
    [customer] = service.visit_candidates()["customers"]
    assert customer["state"] == "closed" and "encerrado" in customer["reason"]
    conversation = service.load(REF)["conversations"][CUSTOMER]
    assert conversation.get("closed_at") and not conversation.get("ignored")
    assert service.notices()["notices"] == []  # the owner's own decision: nothing on the board
