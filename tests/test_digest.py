"""The «Ponto de situação» (27/09): one report per property, for its owner, written from the data on the Painel, kept as
edited for the day, and sent only with a click, to the address in Voz e estilo."""
from datetime import date, timedelta
import json
from unittest.mock import patch
import pytest
from backend.store import load_digest, save_digest, save_json
from test_followups import VOICE_BASE
from test_merge import follow_up
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

RECIPIENT = "owner.inbox@example.com"
OTHER = "bruno.exemplo@example.com"


def page(service, ref=REF, view=None):
    return next(item for item in (view or service.digest_view())["properties"] if item["property_ref"] == ref)


def sending(smtp=SMTP):
    return patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", smtp)


def test_the_report_is_written_from_the_data_without_a_read_of_the_day_or_a_recipient(service):
    read(service, [lead("1")])
    report = page(service)
    assert report["contacted"] == 1 and report["reply_status"] == "draft" and not report["edited"]
    assert report["reply_text"].startswith("Ponto de situação — ") and "1 cliente contactou-nos" in report["reply_text"]
    assert load_digest(service.folder) is None  # looking at it writes nothing


def test_the_owner_reads_who_contacted_answered_is_active_booked_and_visited_not_the_queue(service):
    read(service, [lead("1"), lead("2", reply_to=(OTHER,), body_email=OTHER)])
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [follow_up("c2", 1, "Somos duas pessoas.", service)])
    data = service.load(REF)
    data["conversations"][CUSTOMER]["ficha"] = {"trabalho": "Enfermeira, contrato sem termo.", "agregado": "Casal, sem filhos"}
    service.save(data, REF)
    day = date.today() - timedelta(days=2)
    service.check_visit(REF, CUSTOMER, True, at=f"{day.isoformat()} 17:00")
    report = page(service)
    assert {key: report[key] for key in ("contacted", "responded", "still_active", "booked")} == {
        "contacted": 2, "responded": 1, "still_active": 1, "booked": 1}
    assert [person["name"] for person in report["visited"]] == ["Ana Exemplo"] and report["upcoming"] == []
    text = report["reply_text"]
    for line in ("- 2 clientes contactaram-nos;", "- 1 respondeu à nossa primeira mensagem;",
                 "- 1 marcou visita e 1 já visitou o imóvel.", "- 1 cliente continua em conversa connosco.",
                 f"- Ana Exemplo (visitou a {day.strftime('%d/%m')})", "  Situação profissional: Enfermeira, contrato sem termo.",
                 "  Agregado familiar: Casal, sem filhos."):
        assert line in text.splitlines()
    assert not any(word in text for word in ("rascunho", "por preparar", "pendente", "na fila"))


def test_still_active_leaves_out_who_declined_went_silent_or_asked_to_stop(service):
    read(service, [lead("1")])
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [follow_up("c2", 1, "Afinal já não quero visitar.", service)])
    assert (page(service)["responded"], page(service)["still_active"]) == (1, 1)
    data = service.load(REF)
    data["conversations"][CUSTOMER]["visit"] = "nao_quer"
    service.save(data, REF)
    assert (page(service)["responded"], page(service)["still_active"]) == (1, 0)


def test_each_owner_gets_only_their_own_property(service):
    profile = json.loads((service.folder / "properties" / REF / "profile.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = profile["match"]["subject_property_reference_equals"] = "OUTRO"
    profile["property"]["description"] = "Outro apartamento"
    save_json(service.folder / "properties" / "OUTRO" / "profile.json", profile)
    read(service, [lead("1"), lead("2", ref="OUTRO", reply_to=(OTHER,), body_email=OTHER)])
    view = service.digest_view()
    assert sorted(item["property_ref"] for item in view["properties"]) == sorted([REF, "OUTRO"])
    assert page(service, "OUTRO", view)["reply_text"].startswith("Ponto de situação — Outro apartamento")
    assert page(service, REF, view)["contacted"] == page(service, "OUTRO", view)["contacted"] == 1
    with pytest.raises(ValueError, match="property_ref"):
        service.save_digest_text("Sem imóvel.")  # with several properties, the page is always named


def test_an_edit_is_kept_for_the_day_and_atualizar_writes_it_again_from_now(service):
    read(service, [lead("1")])
    service.save_digest_text("Texto editado à mão.", REF)
    assert (page(service)["reply_text"], page(service)["edited"]) == ("Texto editado à mão.", True)
    read(service, [lead("2", reply_to=(OTHER,), body_email=OTHER)])
    assert page(service)["contacted"] == 2 and page(service)["reply_text"] == "Texto editado à mão."  # numbers of now
    refreshed = page(service, view=service.refresh_digest(REF))
    assert "2 clientes contactaram-nos" in refreshed["reply_text"] and not refreshed["edited"]


def test_yesterdays_pages_and_the_single_text_of_before_start_over(service):
    read(service, [lead("1")])
    save_digest(service.folder, {"date": "2026-01-01", "pages": {REF: {"reply_text": "Velho.", "reply_status": "sent"}}})
    assert page(service)["reply_status"] == "draft" and page(service)["reply_text"] != "Velho."
    save_digest(service.folder, {"date": date.today().isoformat(), "reply_text": "Tudo junto.", "reply_status": "draft"})
    assert page(service)["reply_text"].startswith("Ponto de situação — ")


def test_send_needs_a_confirmation_and_a_recipient(service):
    read(service, [lead("1")])
    with pytest.raises(ValueError, match="[Cc]onfirma"):
        service.send_digest(False, REF)
    with pytest.raises(ValueError, match="destinatário"):
        service.send_digest(True, REF)


def test_send_goes_to_the_configured_recipient_once_with_the_property_in_the_subject(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    SMTP.sent = []
    password, smtp = sending()
    with password, smtp:
        result = service.send_digest(True, REF)
    assert result == {"status": "sent", "property_ref": REF}
    [msg] = SMTP.sent
    assert msg["To"] == RECIPIENT and "In-Reply-To" not in msg and msg["Subject"].startswith("Ponto de situação — ")
    assert "1 cliente contactou-nos" in msg.get_content() and msg.get_content().rstrip().endswith("ARIA Assistente")
    sent = page(service)
    assert sent["reply_status"] == "sent" and sent["sent_at"]
    with pytest.raises(ValueError, match="já foi enviado"):
        service.send_digest(True, REF)
    with pytest.raises(ValueError, match="já foi enviado"):
        service.save_digest_text("Outro texto.", REF)


def test_send_connection_failure_is_uncertain_and_can_be_retried(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])

    class Failing(SMTP):
        def send_message(self, msg):
            raise ConnectionError("boom")

    password, smtp = sending(Failing)
    with password, smtp:
        assert service.send_digest(True, REF)["status"] == "uncertain"
    with pytest.raises(ValueError, match="incerto"):
        service.save_digest_text("Mudado depois.", REF)  # it may have gone: the text stays as it was
    SMTP.sent = []
    password, smtp = sending()
    with password, smtp:
        assert service.send_digest(True, REF)["status"] == "sent" and len(SMTP.sent) == 1


def test_digest_recipient_must_look_like_an_email(service):
    with pytest.raises(ValueError, match="email"):
        service.save_voice({**VOICE_BASE, "digest_recipient": "não é um email"})


OWNER = "proprietario@example.com"


def with_owner(service, ref=REF, email=OWNER, description="Apartamento T3 na Rua Exemplo, Lisboa"):
    service.save_property({"reference": ref, "description": description, "sender": "reply@idealista.pt", "owner_email": email})


def test_the_owner_email_is_kept_on_the_property_and_an_extraction_never_wipes_it(service):
    with_owner(service)
    [saved] = [item for item in service.settings()["properties"] if item["reference"] == REF]
    assert saved["owner_email"] == OWNER
    service.save_property({"reference": REF, "description": "Apartamento T3 na Rua Exemplo, Lisboa"})  # no owner_email
    assert service.settings()["properties"][0]["owner_email"] == OWNER
    with pytest.raises(ValueError, match="proprietário"):
        with_owner(service, email="não é um email")
    with_owner(service, email="")  # the form sends it empty: cleared
    assert service.settings()["properties"][0]["owner_email"] is None


def test_to_the_owner_with_a_copy_to_the_user_signed_by_aria(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    with pytest.raises(ValueError, match="email do proprietário"):
        service.send_digest(True, REF, "owner")
    with_owner(service)
    assert page(service)["owner_email"] == OWNER
    SMTP.sent = []
    password, smtp = sending()
    with password, smtp:
        assert service.send_digest(True, REF, "owner")["status"] == "sent"
    [msg] = SMTP.sent
    assert (msg["To"], msg["Cc"]) == (OWNER, RECIPIENT)
    assert msg["Subject"].startswith("Ponto de situação — Apartamento T3 na Rua Exemplo, Lisboa — ")
    assert msg.get_content().rstrip().endswith("ARIA Assistente")
    assert page(service)["sent_to"] == "owner"
    with pytest.raises(ValueError, match="já foi enviado"):
        service.send_digest(True, REF, "me")  # once a day per property, whichever way it went


def test_the_summary_of_every_property_goes_to_the_user_and_leaves_the_pages_as_they_are(service):
    profile = json.loads((service.folder / "properties" / REF / "profile.json").read_text(encoding="utf-8"))
    profile["property"]["reference"] = profile["match"]["subject_property_reference_equals"] = "OUTRO"
    profile["property"]["description"] = "Outro apartamento"
    save_json(service.folder / "properties" / "OUTRO" / "profile.json", profile)
    read(service, [lead("1"), lead("2", ref="OUTRO", reply_to=(OTHER,), body_email=OTHER)])
    service.save_digest_text("Nota à mão para o outro proprietário.\n\nARIA Assistente", "OUTRO")
    with pytest.raises(ValueError, match="destinatário"):
        service.send_digest_all(True)
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    SMTP.sent = []
    password, smtp = sending()
    with password, smtp:
        assert service.send_digest_all(True) == {"status": "sent"}
    [msg] = SMTP.sent
    body = msg.get_content()
    assert msg["To"] == RECIPIENT and msg["Cc"] is None and "todos os imóveis" in msg["Subject"]
    assert "Nota à mão para o outro proprietário." in body and "Ponto de situação — " in body
    assert body.count("ARIA Assistente") == 1  # one signature, at the end
    view = service.digest_view()
    assert view["all"]["reply_status"] == "sent" and all(item["reply_status"] == "draft" for item in view["properties"])
    with pytest.raises(ValueError, match="já foi enviado"):
        service.send_digest_all(True)
