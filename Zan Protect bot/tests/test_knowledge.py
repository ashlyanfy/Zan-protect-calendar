from datetime import date

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.knowledge import LegalMaterial, cosine, fuse
from app.storage import PrivateStore


def test_semantic_cosine_and_fusion():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    assert fuse(["a", "b"], ["b", "c"])[0] == "b"


def test_encrypted_storage_detects_wrong_key():
    store = PrivateStore(None, Fernet.generate_key().decode())
    data = store.seal({"text": "private-personal-material"})
    assert b"private-personal-material" not in data
    assert store.open(data)["text"] == "private-personal-material"
    with pytest.raises(InvalidToken):
        PrivateStore(None, Fernet.generate_key().decode()).open(data)


@pytest.mark.parametrize("url", ["http://gov.kz", "https://gov.kz.evil.example", "https://127.0.0.1", "https://user@gov.kz"])
def test_legal_source_domain_validation(url):
    with pytest.raises(ValueError):
        LegalMaterial(id="law-1", title="Title of law", url=url, language="ru", excerpt="x"*100,
                      checked_on=date(2026, 10, 11), review_due=date(2026, 11, 11))
