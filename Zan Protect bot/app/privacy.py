import hashlib
import hmac
import re
import time
from dataclasses import dataclass, field


def redact(text: str) -> str:
    """Best effort only. Names, free-form addresses and images require separate handling."""
    text = re.sub(r"https?://\S+", "[LINK_REDACTED]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"(?<!\w)KZ[0-9A-Z]{18}(?!\w)", "[IBAN]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)", "[ID_OR_CARD]", text)
    text = re.sub(r"(?<!\d)(?:\+?7|8)[ ()-]*(?:\d[ ()-]*){10}(?!\d)", "[PHONE]", text)
    text = re.sub(r"(?i)((?:код|code|пароль|құпиясөз)\s*[:=]?\s*)\S+", r"\1[SECRET]", text)
    return text


def session_key(user_id: int, secret: str) -> str:
    return hmac.new(secret.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


@dataclass
class Session:
    expires: float
    mode: str = "check"
    language: str = "ru"
    consent: bool = False
    web_consent: bool = False
    audio_consent: bool = False
    case_paused: bool = False
    history: list[str] = field(default_factory=list)
    busy: bool = False
    last_request: float = 0
    case: dict = field(default_factory=dict)


class Sessions:
    """One-process MVP, no persistence or backups. Scheduled purge is required."""
    def __init__(self, ttl: int, capacity: int = 2000):
        self.ttl = ttl
        self.capacity = capacity
        self.items: dict[str, Session] = {}

    def purge(self):
        now = time.monotonic()
        for key in list(self.items):
            if self.items[key].expires <= now and not self.items[key].busy:
                del self.items[key]

    def get(self, key: str) -> Session:
        self.purge()
        if key not in self.items:
            if len(self.items) >= self.capacity:
                raise ValueError("Session capacity exceeded")
            self.items[key] = Session(expires=time.monotonic() + self.ttl)
        return self.items[key]

    def delete(self, key: str):
        self.items.pop(key, None)
