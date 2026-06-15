import os
from Utils import cipher

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

SENSITIVE_KEYS = {"MAIL_PASSWORD", "META_ACCESS_TOKEN"}


def _decrypt_if_needed(key: str, value: str) -> str:
    if key in SENSITIVE_KEYS and value and not value.startswith("ENC:"):
        return value
    if key in SENSITIVE_KEYS and value.startswith("ENC:"):
        try:
            return cipher.decrypt(value[4:])
        except Exception:
            return value
    return value


def _encrypt_if_needed(key: str, value: str) -> str:
    if key in SENSITIVE_KEYS and value:
        return "ENC:" + cipher.encrypt(value)
    return value


def read_env(key: str) -> str | None:
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return _decrypt_if_needed(key, v.strip())
    return None


def read_all_env() -> dict:
    result = {}
    if not os.path.exists(ENV_PATH):
        return result
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            result[k.strip()] = _decrypt_if_needed(k.strip(), v.strip())
    return result


def update_env(updates: dict) -> bool:
    if not os.path.exists(ENV_PATH):
        return False

    with open(ENV_PATH, "r") as f:
        lines = f.readlines()

    keys_updated = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in updates:
            lines[i] = f"{k}={_encrypt_if_needed(k, updates[k])}\n"
            keys_updated.add(k)

    for k, v in updates.items():
        if k not in keys_updated:
            lines.append(f"{k}={_encrypt_if_needed(k, v)}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)

    return True
