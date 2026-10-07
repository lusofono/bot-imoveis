"""A customer on a blue (offered) or orange (accepted) time who did come: the check records that visit."""
from datetime import date
from backend.store import load_visits
from test_properties import REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

TODAY = date.today().isoformat()


def test_checking_an_offered_time_books_it_as_the_visit(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá.")
    data = service.load(REF)
    email = next(iter(data["conversations"]))
    data["conversations"][email]["visit_offered"] = {"at": f"{TODAY} 14:30", "evidence": "x"}
    service.save(data, REF)
    result = service.check_visit(REF, email, True, "veio com a mulher", "foi um prazer", at=f"{TODAY} 14:30")
    [slot] = load_visits(service.folder, REF)["slots"]
    assert (slot["at"], slot["customer"], slot["source"], slot["check"]["attended"]) == (f"{TODAY} 14:30", email, "check", True)
    assert result["at"] == f"{TODAY} 14:30" and "visit_offered" not in service.load(REF)["conversations"][email]
    assert service.visit_thanks(REF, email)["id"]
