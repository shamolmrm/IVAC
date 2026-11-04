"""Field-level encryption for sensitive personal data (passport / NID numbers).

- `encrypt` / `decrypt`: AES-256-GCM with a random nonce per value ("v1:" + base64(nonce|ct)).
- `blind_index`: keyed HMAC-SHA256 of the normalised value, for exact-match lookups and
  duplicate detection without storing the plain value.

Both sub-keys are derived from DATA_ENCRYPTION_KEY (32 random bytes, base64). Losing that key
means losing the encrypted data, so it must be backed up outside the server.
"""

import base64
import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

_PREFIX = "v1:"


@lru_cache
def _keys() -> tuple[bytes, bytes]:
    raw = base64.b64decode(get_settings().data_encryption_key)
    if len(raw) != 32:
        raise RuntimeError("DATA_ENCRYPTION_KEY must be 32 bytes, base64-encoded.")
    enc = hmac.new(raw, b"ivac/encrypt/v1", hashlib.sha256).digest()
    idx = hmac.new(raw, b"ivac/blind-index/v1", hashlib.sha256).digest()
    return enc, idx


def encrypt(value: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_keys()[0]).encrypt(nonce, value.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode()


def decrypt(token: str) -> str:
    if not token.startswith(_PREFIX):
        raise ValueError("unknown ciphertext format")
    blob = base64.b64decode(token[len(_PREFIX) :])
    return AESGCM(_keys()[0]).decrypt(blob[:12], blob[12:], None).decode()


@lru_cache
def _file_key() -> bytes:
    raw = base64.b64decode(get_settings().data_encryption_key)
    return hmac.new(raw, b"ivac/files/v1", hashlib.sha256).digest()


def encrypt_bytes(data: bytes, aad: bytes) -> bytes:
    """Encrypt a whole file. `aad` (e.g. the document id) binds the ciphertext to its record."""
    nonce = os.urandom(12)
    return b"IVF1" + nonce + AESGCM(_file_key()).encrypt(nonce, data, aad)


def decrypt_bytes(blob: bytes, aad: bytes) -> bytes:
    if blob[:4] != b"IVF1":
        raise ValueError("unknown file format")
    return AESGCM(_file_key()).decrypt(blob[4:16], blob[16:], aad)


def blind_index(value: str) -> str:
    return hmac.new(_keys()[1], value.encode(), hashlib.sha256).hexdigest()
