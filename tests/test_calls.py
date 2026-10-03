"""02/10: the portal's call notices — read at «Ler emails» (or N days back), kept apart from the queue, tied to a
property by the reference the notice names and to a customer by the phone."""
from unittest.mock import patch
import pytest
from test_properties import REF, lead, read, service  # noqa: F401 (service is a fixture)


def call_notice(key, phone="351900000001", ref=REF, answered=False):
    body = (f"Uma pessoa interessada nos teus anúncios realizou uma chamada:\nO seu número de telefone é: {phone}\n"
            f"Data e hora: 30/09/2026 16:18:14\nEstado: {'atendida' if answered else 'nao respondida'}\n"
            f"Duração em segundos: {44 if answered else 0}\n"
            + (f"Código do anúncio contactado: 12345678 - Ref. {ref}\n" if ref else ""))
    return {"gmail_message_id": key, "message_id": f"<{key}@idealista>", "date": "2026-10-02T10:00:00+00:00",
            "from": [{"name": "idealista", "email": "naoresponder@idealista.pt"}],
            "subject": f"Chamada {'atendida' if answered else 'nao respondida'} de um interessado nos teus anuncios",
            "body_text": body}


def test_a_call_goes_to_its_property_never_the_queue_and_finds_its_customer_by_the_phone(service):
    read(service, [lead("1"), call_notice("c1")])  # the lead's phone is 900 000 001
    assert [email["id"] for email in service.pending()["properties"][0]["emails"]] == ["1"]
    [call] = service.calls_view()["calls"]
    assert (call["property_ref"], call["answered"], call["at"], call["name"]) == (REF, False, "2026-09-30 16:18:14", "Ana Exemplo")
    assert call["phone_shown"] == "+351 900 000 001" and call["international"] == "351900000001"
    read(service, [call_notice("c1")])  # the same notice again: once
    assert len(service.calls_view()["calls"]) == 1


def test_a_call_naming_no_property_takes_its_customers_or_none(service):
    read(service, [lead("1"), call_notice("c1", ref=None, answered=True), call_notice("c2", phone="351911111111", ref=None)])
    known, unknown = sorted(service.calls_view()["calls"], key=lambda call: call["id"])
    assert (known["property_ref"], known["name"], known["answered"], known["seconds"]) == (REF, "Ana Exemplo", True, 44)
    assert (unknown["property_ref"], unknown["name"]) == (None, "")


def test_older_calls_are_found_n_days_back(service):
    with pytest.raises(ValueError, match="de 1 a 365"):
        service.scan_calls(0)
    with patch("backend.service.app_password", return_value="fake"), patch(
            "backend.service.read_messages", return_value=([call_notice("c9")], 40, "INBOX")) as fetch:
        result = service.scan_calls(60)
    assert result["added"] == 1 and len(result["calls"]) == 1
    assert fetch.call_args.kwargs["accept"](call_notice("c10")) is True
    assert fetch.call_args.kwargs["accept"](lead("2")) is False  # only the call notices


def test_a_call_about_a_listing_not_in_the_aria_keeps_its_reference_and_no_property(service):
    read(service, [call_notice("c1", phone="351922222222", ref="OUTRO_ANUNCIO")])
    [call] = service.calls_view()["calls"]
    assert (call["property_ref"], call["ref"]) == (None, "OUTRO_ANUNCIO")  # the page leaves it out of «sem imóvel»
