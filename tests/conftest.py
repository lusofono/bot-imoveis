"""Shared test helpers."""
from datetime import date, datetime, timezone
import pytest

# 02/10: these tests mix the local day and the UTC day; they fail only in the hour when the two differ (00:00–01:00 in
# Lisbon in summer). Skipped then, until they are made independent of the time of day — run them at any other hour.
midnight_sensitive = pytest.mark.skipif(date.today() != datetime.now(timezone.utc).date(),
                                        reason="o dia local e o dia UTC são diferentes (entre a meia-noite e a uma)")
