from unittest.mock import patch
import pytest
from backend.store import load_digest
from test_followups import VOICE_BASE
from test_properties import CUSTOMER, REF, SMTP, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)

RECIPIENT = "owner.inbox@example.com"


def test_no_digest_without_a_recipient_configured(service):
    read(service, [lead("1")])
    assert load_digest(service.folder) is None


def test_digest_prepared_after_read_and_not_recreated_the_same_day(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    digest = load_digest(service.folder)
    assert digest["reply_status"] == "draft" and digest["sent_at"] is None
    assert REF in digest["reply_text"] and "1 pendentes" in digest["reply_text"]

    # Once a day: a second read the same day never overwrites an already-prepared digest.
    draft_and_send(service, "1", "Olá, Ana.")
    read(service, [])
    assert load_digest(service.folder)["reply_text"] == digest["reply_text"]


def test_send_digest_requires_confirmation_and_a_prepared_draft(service):
    with pytest.raises(ValueError, match="por enviar"):
        service.send_digest(True)
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    with pytest.raises(ValueError, match="[Cc]onfirma"):
        service.send_digest(False)


def test_send_digest_success_goes_to_the_configured_recipient(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        result = service.send_digest(True)
    assert result["status"] == "sent"
    assert SMTP.sent[0]["To"] == RECIPIENT and "In-Reply-To" not in SMTP.sent[0]
    digest = load_digest(service.folder)
    assert digest["reply_status"] == "sent" and digest["sent_at"]
    # Nothing left to send a second time.
    with pytest.raises(ValueError, match="por enviar"):
        service.send_digest(True)


def test_send_digest_connection_failure_is_uncertain_and_can_be_retried(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])

    class Failing(SMTP):
        def send_message(self, msg):
            raise ConnectionError("boom")

    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", Failing):
        result = service.send_digest(True)
    assert result["status"] == "uncertain"

    SMTP.sent = []
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        result = service.send_digest(True)
    assert result["status"] == "sent" and len(SMTP.sent) == 1


def test_save_digest_text_edits_the_draft_before_sending(service):
    service.save_voice({**VOICE_BASE, "digest_recipient": RECIPIENT})
    read(service, [lead("1")])
    service.save_digest_text("Texto editado à mão.")
    assert load_digest(service.folder)["reply_text"] == "Texto editado à mão."


def test_digest_recipient_must_look_like_an_email(service):
    with pytest.raises(ValueError, match="email"):
        service.save_voice({**VOICE_BASE, "digest_recipient": "não é um email"})
