import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT = b"2fa-otp-salt-2026"
KEY = None


def _get_key() -> bytes:
    global KEY
    if KEY is not None:
        return KEY
    raw = os.getenv("ENCRYPTION_KEY")
    if not raw:
        raise RuntimeError("ENCRYPTION_KEY no configurada en .env")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=600000)
    KEY = base64.urlsafe_b64encode(kdf.derive(raw.encode()))
    return KEY


def encrypt(plain_text: str) -> str:
    f = Fernet(_get_key())
    return f.encrypt(plain_text.encode()).decode()


def decrypt(cipher_text: str) -> str:
    f = Fernet(_get_key())
    return f.decrypt(cipher_text.encode()).decode()
