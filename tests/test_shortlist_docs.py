"""03/10: a short-list customer's next reply asks for the documents by itself (no button); once asked, each reply says
what came — by what they wrote and the attached files' names, nothing opened — and the documents are marked arrived."""
from backend.ai import parse_documents, reply_prompt, short_id
from test_merge import follow_up
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def test_the_short_list_reply_asks_for_the_documents_then_reads_what_came(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    service.set_selection(REF, CUSTOMER, "shortlist")
    read(service, [follow_up("c2", 1, "Gostei muito da visita.", service)])
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]
    assert (card["phase"], card["docs_requested"]) == ("shortlist", False)
    prompt = reply_prompt(queue, ["c2"])
    assert "interação: short list · pedir documentos |" in prompt and f"Documentos a pedir: Documento de identificação (CC, passaporte ou título de residência); Recibos de vencimento" in prompt
    draft_and_send(service, "c2", "Gostaríamos de passar à fase seguinte: envie-nos, por favor, os documentos.")
    assert service.load(REF)["conversations"][CUSTOMER]["selection"]["docs_requested_at"]

    sent = {**follow_up("c3", 1, "Envio o IRS em anexo; os recibos seguem amanhã.", service), "attachments": ["IRS 2025.pdf"]}
    read(service, [sent])
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]
    assert card["docs_requested"] and card["attachments"] == ["IRS 2025.pdf"] and "Recibos de vencimento" in card["docs_missing"]
    prompt = reply_prompt(queue, ["c3"])
    assert "interação: short list · documentos |" in prompt and "Anexos (só os nomes): IRS 2025.pdf" in prompt
    answer = ('{"respostas": [{"id": "' + short_id("c3") + '", "reply_text": "Recebemos o IRS.", '
              '"documentos": ["candidato:irs", "fiador:irs", "inventado"]}]}')
    found = parse_documents(answer, queue)
    assert found == [{"id": "c3", "docs": ["candidato:irs", "fiador:irs"]}]
    assert service.mark_documents(REF, found) == 1  # no guarantor: only the candidate's
    selection = service.load(REF)["conversations"][CUSTOMER]["selection"]
    assert selection["docs"] == {"candidato:irs": True}
    [card] = service.pending()["properties"][0]["emails"]
    assert "IRS do ano anterior (ou dos dois anteriores)" not in card["docs_missing"]


def test_asking_for_the_documents_of_a_customer_with_an_email_in_the_queue_goes_into_that_card(service):
    # 05/10: one card per customer: «Pedir documentos» leaves an instruction for that reply only in the email already in
    # the queue (the documents still missing), never a second card; it reaches the prompt and can be taken off
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    service.set_selection(REF, CUSTOMER, "shortlist")
    read(service, [follow_up("c2", 1, "Tenho muito interesse.", service)])
    result = service.request_documents(REF, CUSTOMER)
    assert result["attached"] is True
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]  # still one
    assert card["id"] == result["id"] and card["reply_note"].startswith("Pede os documentos da candidatura que ainda faltam: ")
    assert "Recibos de vencimento" in card["reply_note"]
    prompt = reply_prompt(queue, [card["id"]])
    assert "Instrução do proprietário só para esta resposta (segue-a): Pede os documentos" in prompt
    service.set_reply_note(REF, card["id"], "")
    assert not service.pending()["properties"][0]["emails"][0]["reply_note"]
