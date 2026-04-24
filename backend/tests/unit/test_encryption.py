import pytest

from app.core.config import settings
from app.services.security import encryption


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_ENCRYPTION_KEY", "deadbeef" * 8)
    plaintext = '{"url": "http://localhost:6333"}'
    ciphertext = encryption.encrypt(plaintext)
    assert isinstance(ciphertext, bytes)
    assert encryption.decrypt(ciphertext) == plaintext


def test_ciphertext_differs_from_plaintext(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_ENCRYPTION_KEY", "deadbeef" * 8)
    plaintext = "secret"
    ciphertext = encryption.encrypt(plaintext)
    assert plaintext.encode() not in ciphertext


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_ENCRYPTION_KEY", None)
    with pytest.raises(RuntimeError, match="VECTOR_STORE_ENCRYPTION_KEY"):
        encryption.encrypt("any")
