"""30/09: the agency's know-how in three — common, rentals only and sales only —, each property getting the common one
and its own kind's; and the prompt knows the day and time it is written."""
from datetime import datetime, timezone
import pytest
from backend.ai import reply_prompt
from test_properties import REF, lead, read, service  # noqa: F401 (service is a fixture)


def instructions(service):
    return next(queue for queue in service.pending()["properties"] if queue["property_ref"] == REF)["instructions"]


def test_each_property_gets_the_common_know_how_and_only_its_own_kinds(service):
    service.save_knowledge(None, "comum.md", "# Comum\n- Resposta em 24 horas.", "agency")
    service.save_knowledge(None, "regras.md", "# Arrendar\n- Pedimos fiador.", "agency-arrendamento")
    service.save_knowledge(None, "regras.md", "# Vender\n- Nunca pedimos fiador.", "agency-venda")
    assert (service.folder / "arrendamento" / "knowledge" / "regras.md").exists()
    text = instructions(service)  # a property without a kind is a rental
    assert "Resposta em 24 horas." in text and "Pedimos fiador." in text and "Nunca pedimos fiador." not in text
    assert "para arrendar" in text
    fields = {"reference": REF, "description": "Moradia T4", "listing_id": "00000000", "deal": "venda"}
    service.save_property(fields)
    text = instructions(service)
    assert "Nunca pedimos fiador." in text and "Pedimos fiador." not in text and "para vender" in text
    assert service.settings()["properties"][0]["deal"] == "venda"
    files = service.knowledge(REF)["files"]
    assert [f["file"] for f in files["agency-arrendamento"]] == ["regras.md"] and files["agency-venda"]
    # A note for «every property of this kind» goes to the sales' know-how
    service.add_note(REF, "Visitas de venda com hora marcada.", "agency-deal")
    assert "Visitas de venda com hora marcada." in (service.folder / "venda" / "knowledge" / "notas.md").read_text()
    with pytest.raises(ValueError):
        service.save_property({**fields, "deal": "trespasse"})


def test_the_prompt_knows_the_day_and_time_it_is_written(service):
    read(service, [lead("1")])
    queue = next(queue for queue in service.pending()["properties"] if queue["property_ref"] == REF)
    prompt = reply_prompt(queue, ["1"], now=datetime(2026, 9, 30, 19, 5, tzinfo=timezone.utc))
    assert prompt.startswith("AGORA: quarta-feira, 30/09/2026, 19:05.") and "Nunca digas «hoje» de um dia que já passou." in prompt
    assert not reply_prompt(queue, ["1"]).startswith("AGORA")
