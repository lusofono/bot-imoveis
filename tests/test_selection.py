"""The short list at the top of Contactos: 2 or 3 candidates, one chosen and one reserve, documents as ticks."""
import pytest
from backend.ai import reply_prompt
from backend.rules import documents_summary
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)
from test_visits import customer


def two_customers(service):
    read(service, [customer("1", "a@example.com"), customer("2", "b@example.com")])
    draft_and_send(service, "1", "Olá.")
    draft_and_send(service, "2", "Olá.")


def test_one_chosen_and_one_reserve_per_property(service):
    two_customers(service)
    assert service.contacts()["selection"] == []  # empty until the owner picks someone
    with pytest.raises(ValueError, match="inválido"):
        service.set_selection(REF, "a@example.com", "favorito")
    service.set_selection(REF, "a@example.com", "shortlist")
    service.set_selection(REF, "b@example.com", "shortlist")
    assert {f["email"]: f["selection"] for f in service.contacts()["fichas"]} == {"a@example.com": "shortlist",
                                                                                 "b@example.com": "shortlist"}
    service.set_selection(REF, "a@example.com", "chosen")
    service.set_selection(REF, "b@example.com", "chosen")  # another chosen: the first goes back to the short list
    assert [(c["email"], c["status"]) for c in service.contacts()["selection"]] == [
        ("b@example.com", "chosen"), ("a@example.com", "shortlist")]
    service.set_selection(REF, "a@example.com", "suplente")
    assert [c["label"] for c in service.contacts()["selection"]] == ["Escolhido", "Suplente"]
    service.set_selection(REF, "a@example.com", None)
    assert [c["email"] for c in service.contacts()["selection"]] == ["b@example.com"]


def test_documents_are_ticks_and_asked_only_of_the_short_list(service):
    two_customers(service)
    with pytest.raises(ValueError, match="short list"):
        service.request_documents(REF, "a@example.com")
    service.set_selection(REF, "a@example.com", "shortlist")
    [candidate] = service.contacts()["selection"]
    assert candidate["documents"]["missing"] == ["Recibos de vencimento", "IRS do ano anterior (ou dos dois anteriores)"]
    service.set_document(REF, "a@example.com", fiador=True)
    service.set_document(REF, "a@example.com", "candidato:recibos", True)
    service.set_document(REF, "a@example.com", "candidato:irs", True)
    with pytest.raises(ValueError, match="Documento desconhecido"):
        service.set_document(REF, "a@example.com", "candidato:passaporte", True)
    [candidate] = service.contacts()["selection"]
    assert candidate["documents"]["missing"] == ["Recibos de vencimento do fiador",
                                                 "IRS do ano anterior (ou dos dois anteriores) do fiador"]
    assert documents_summary({"docs": {"candidato:recibos": True, "candidato:irs": True}})["complete"]

    key = service.request_documents(REF, "a@example.com")["id"]
    with pytest.raises(ValueError, match="já está na fila"):
        service.request_documents(REF, "a@example.com")
    queue = service.pending()["properties"][0]
    [request] = [e for e in queue["emails"] if e["id"] == key]
    assert request["kind"] == "docs_request" and request["docs_request"] == {"fiador": True}
    prompt = reply_prompt(queue, [key])
    assert "interação: pedido de documentos" in prompt and "Recibos de vencimento" in prompt
    assert "pede também os mesmos do fiador" in prompt and "Pedido de documentos (emails marcados" in queue["instructions"]
    stage = service.load(REF)["conversations"]["a@example.com"]["stage"]
    draft_and_send(service, key, "Pedimos os seguintes documentos…")
    assert service.load(REF)["conversations"]["a@example.com"]["stage"] == stage  # not an interaction


def test_every_booking_says_where_its_customer_stands_in_the_selection(service):
    from datetime import date
    from backend.store import load_visits, save_visits
    two_customers(service)
    agenda = load_visits(service.folder, REF)
    agenda["slots"].append({"at": f"{date.today().isoformat()} 00:00", "customer": "a@example.com", "name": "Ana"})
    save_visits(service.folder, REF, agenda)
    service.check_visit(REF, "a@example.com", True)
    [slot] = service.settings()["properties"][0]["visits"]["slots"]
    assert slot["check"]["attended"] is True and slot["selection"] is None  # «Quem já visitou», not on the list yet
    service.set_selection(REF, "a@example.com", "shortlist")
    assert service.settings()["properties"][0]["visits"]["slots"][0]["selection"] == "shortlist"
