from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.audio import audio_attachment
from app.config import Settings
from app.llm import Assistant


def test_audio_sent_as_document():
    doc = SimpleNamespace(file_name="call.M4A")
    assert audio_attachment(SimpleNamespace(voice=None, audio=None, document=doc)) == (doc, "call.M4A")


async def test_transcription_parameters_and_redaction():
    cfg = Settings(_env_file=None, api_secret="a" * 32, session_secret="b" * 32, openai_api_key="test")
    assistant = Assistant(cfg, None)
    create = AsyncMock(return_value=SimpleNamespace(text="Мне сказали код: 123456"))
    assistant.client.audio.transcriptions.create = create
    try:
        text = await assistant.transcribe("private-person.ogg", b"fake-audio")
        assert "123456" not in text
        assert create.call_args.kwargs["file"] == ("recording.ogg", b"fake-audio", "audio/ogg")
        assert create.call_args.kwargs["response_format"] == "json"
        with pytest.raises(ValueError):
            await assistant.transcribe("script.exe", b"bad")
        assert create.await_count == 1
    finally:
        await assistant.client.close()
