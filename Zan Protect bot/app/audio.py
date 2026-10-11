"""Telegram audio metadata routing; original bytes stay in memory only."""
from pathlib import Path

AUDIO_FORMATS = {".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".wav": "audio/wav",
                 ".m4a": "audio/mp4", ".mp4": "audio/mp4", ".mpeg": "audio/mpeg",
                 ".mpga": "audio/mpeg", ".flac": "audio/flac", ".webm": "audio/webm"}


def audio_attachment(message):
    if message.voice:
        return message.voice, "voice.ogg"
    if message.audio:
        return message.audio, message.audio.file_name or "audio.mp3"
    if message.document and Path(message.document.file_name or "").suffix.lower() in AUDIO_FORMATS:
        return message.document, message.document.file_name
    return None
