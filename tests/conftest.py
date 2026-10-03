"""Shared test helpers."""
from datetime import date, datetime, timezone
import pytest

# 02/10: these tests mix the local day and the UTC day; they fail only in the hour when the two differ (00:00–01:00 in
# Lisbon in summer). Skipped then, until they are made independent of the time of day — run them at any other hour.
midnight_sensitive = pytest.mark.skipif(date.today() != datetime.now(timezone.utc).date(),
                                        reason="o dia local e o dia UTC são diferentes (entre a meia-noite e a uma)")


@pytest.fixture(autouse=True)
def mark_key(tmp_path_factory, monkeypatch):
    """02/10: the hidden mark's key in a file of the tests' own, never the Mac's Keychain."""
    monkeypatch.setenv("BOT_MAIL_TAG_KEY_FILE", str(tmp_path_factory.getbasetemp() / "aria_tag_key"))


@pytest.fixture(autouse=True)
def portal_defaults():
    """02/10: the portal's rules are the module's: a test that changes them never leaks into the next."""
    yield
    from backend.rules import apply_portal
    apply_portal()
