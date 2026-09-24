import os
from unittest.mock import patch
import pytest
from backend.secrets import has_openai_api_key, openai_api_key, save_openai_key


def test_openai_key_file_fallback_needs_600_and_a_clear_message_when_missing(tmp_path):
    with pytest.raises(RuntimeError, match="mac/openai_key.command"):
        openai_api_key(tmp_path, "owner@example.com")
    assert has_openai_api_key(tmp_path, "owner@example.com") is False

    key_file = tmp_path / "key.txt"
    key_file.write_text("sk-test-123\n")
    key_file.chmod(0o644)  # too open
    with patch.dict(os.environ, {"BOT_MAIL_OPENAI_KEY_FILE": str(key_file)}):
        with pytest.raises(RuntimeError, match="permissões 600"):
            openai_api_key(tmp_path, "owner@example.com")
        key_file.chmod(0o600)
        assert openai_api_key(tmp_path, "owner@example.com") == "sk-test-123"
        assert has_openai_api_key(tmp_path, "owner@example.com") is True


def test_save_openai_key_rejects_an_empty_one():
    with pytest.raises(ValueError, match="vazia"):
        save_openai_key("/tmp", "owner@example.com", "   ")
