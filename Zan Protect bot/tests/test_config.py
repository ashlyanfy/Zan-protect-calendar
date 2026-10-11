import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
        monkeypatch.delenv(name, raising=False)


def test_missing_secrets_do_not_expose_settings():
    sensitive = "private-provider-value"
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, openai_api_key=sensitive)
    message = str(error.value)
    assert "api_secret" in message
    assert "session_secret" in message
    assert sensitive not in message
    assert "input_value" not in message


def test_missing_bot_settings_list_names_only():
    config = Settings(_env_file=None, api_secret="a" * 32, session_secret="b" * 32)
    with pytest.raises(ValueError) as error:
        config.validate_bot()
    for name in ("TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "DATA_ENCRYPTION_KEY"):
        assert name in str(error.value)


def test_invalid_encryption_key_is_reported_without_value():
    config = Settings(_env_file=None, api_secret="a" * 32, session_secret="b" * 32,
                      telegram_bot_token="test", openai_api_key="test", data_encryption_key="private-invalid-key")
    with pytest.raises(ValueError) as error:
        config.validate_bot()
    assert "DATA_ENCRYPTION_KEY" in str(error.value)
    assert "private-invalid-key" not in str(error.value)


def test_valid_bot_settings():
    config = Settings(_env_file=None, api_secret="a" * 32, session_secret="b" * 32,
                      telegram_bot_token="test", openai_api_key="test",
                      data_encryption_key=Fernet.generate_key().decode())
    config.validate_bot()
