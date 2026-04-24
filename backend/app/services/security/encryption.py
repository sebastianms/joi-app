from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.VECTOR_STORE_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "VECTOR_STORE_ENCRYPTION_KEY is not set. "
            "Generate one with: openssl rand -hex 32"
        )
    # Derive a 32-byte Fernet key from the hex string stored in the env var.
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode()
