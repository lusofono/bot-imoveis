import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from backend.service import MailService
from backend.store import save_json, locked


def message(key, recipient="person@example.com"):
    return {"gmail_message_id": key, "message_id": f"<{key}@example.com>",
            "from": [{"email": recipient}], "subject": "Visita", "body_text": "Quando posso visitar?"}


@pytest.fixture
def service(tmp_path):
    save_json(tmp_path / "config.json", {"account": "owner@example.com", "lookback_days": 2})
    return MailService(tmp_path)


def read(service, messages):
    with patch("backend.service.app_password", return_value="fake"), patch(
        "backend.service.read_messages", return_value=(messages, len(messages), "INBOX")) as fetch:
        result = service.read()
    return result, fetch


class SMTP:
    sent = []
    fail_at = None
    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def login(self, *args): pass
    def send_message(self, msg):
        if self.fail_at is not None and len(self.sent) == self.fail_at:
            raise ConnectionError("uncertain")
        self.sent.append(msg)
        return {}


def test_batch_append_send_and_no_reimport(service):
    messages = [message(str(i)) for i in range(10)]
    initial, _ = read(service, messages)
    service.drafts([{"id": str(i), "reply_text": f"Olá {i}"} for i in range(10)], initial["revision"])
    reread, _ = read(service, [message(str(i)) for i in range(11)])
    assert reread["added"] == 1
    assert reread["emails"][0]["reply_text"] == "Olá 0"
    preview = service.preview([str(i) for i in range(10)])
    SMTP.sent, SMTP.fail_at = [], None
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        result = service.send(preview["preview_token"], True)
    assert len(SMTP.sent) == 10 and result["remaining"] == 1
    assert all(m['In-Reply-To'] and not list(m.iter_attachments()) for m in SMTP.sent)
    assert [e['id'] for e in service.pending()['emails']] == ['10']
    assert read(service, messages)[0]["added"] == 0
    assert not list(service.folder.glob('queue_*.json'))


def test_weekly_gap_and_preserve_pending(service):
    read(service, [message("1")])
    data = service.load()
    date = datetime.now(timezone.utc) - timedelta(days=21)
    data["last_read_at"] = date.isoformat()
    service.save(data)
    _, fetch = read(service, [])
    assert fetch.call_args.args[3] == (date.date() - timedelta(days=1)).isoformat()
    assert len(service.pending()["emails"]) == 1


def test_stale_draft_and_unknown_ids_are_atomic(service):
    data, _ = read(service, [message("1")])
    with pytest.raises(ValueError):
        service.drafts([{"id": "1", "reply_text": "x"}, {"id": "wrong", "reply_text": "y"}], data["revision"])
    assert service.pending()["emails"][0]["reply_text"] == ""
    with pytest.raises(ValueError):
        service.drafts([{"id": "1", "reply_text": "x"}], data["revision"]-1)


def test_send_requires_current_preview_and_confirmation(service):
    data, _ = read(service, [message("1")])
    service.drafts([{"id": "1", "reply_text": "ok"}], data["revision"])
    preview = service.preview(["1"])
    with pytest.raises(ValueError): service.send(preview["preview_token"], False)
    service.drafts([{"id": "1", "reply_text": "changed"}], service.pending()["revision"])
    with pytest.raises(ValueError): service.send(preview["preview_token"], True)


def test_uncertain_delivery_retained_and_cannot_retry(service):
    data, _ = read(service, [message("1"), message("2")])
    service.drafts([{"id": key, "reply_text": "ok"} for key in ("1", "2")], data["revision"])
    preview = service.preview(["1", "2"])
    SMTP.sent, SMTP.fail_at = [], 0
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", SMTP):
        service.send(preview["preview_token"], True)
    pending = service.pending()["emails"]
    assert pending[0]["reply_status"] == "uncertain"
    assert pending[1]["reply_status"] == "draft"
    with pytest.raises(ValueError): service.preview(["1"])
    service.resolve("1", True)
    assert [e["id"] for e in service.pending()["emails"]] == ["2"]


def test_lock_account_isolation_and_permissions(service):
    with locked(service.folder):
        with pytest.raises(RuntimeError): service.pending()
    read(service, [message("1")])
    assert service.path.stat().st_mode & 0o077 == 0
    save_json(service.folder / "config.json", {"account": "other@example.com"})
    with pytest.raises(ValueError): service.pending()


def test_expired_preview_and_failure_before_send(service):
    data, _ = read(service, [message("1")])
    service.drafts([{"id": "1", "reply_text": "ok"}], data["revision"])
    preview = service.preview(["1"])
    data = service.load()
    data["send_preview"]["expires"] = 0
    service.save(data)
    with pytest.raises(ValueError): service.send(preview["preview_token"], True)
    assert service.pending()["emails"][0]["reply_status"] == "draft"


def test_smtp_rejection_retained(service):
    import smtplib
    class Rejected(SMTP):
        def send_message(self, msg):
            raise smtplib.SMTPRecipientsRefused({"person@example.com": (550, b"no")})
    data, _ = read(service, [message("1")])
    service.drafts([{"id": "1", "reply_text": "ok"}], data["revision"])
    preview = service.preview(["1"])
    with patch("backend.service.app_password", return_value="fake"), patch("backend.service.smtplib.SMTP_SSL", Rejected):
        result = service.send(preview["preview_token"], True)
    assert result["remaining"] == 1
    assert service.pending()["emails"][0]["reply_status"] == "error"
