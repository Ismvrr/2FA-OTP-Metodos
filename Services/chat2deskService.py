import os
import httpx
import hashlib
import uuid
from datetime import datetime, timedelta

API_URL = ""
TOKEN = ""
CHANNEL_ID = ""
VAR2_TEXT = "52 55 4000 0652"

otp_store: dict[str, dict] = {}


def reload_config():
    global API_URL, TOKEN, CHANNEL_ID
    API_URL = os.getenv("CHAT2DESK_API_URL", "https://api.chat2desk.com.mx")
    TOKEN = os.getenv("CHAT2DESK_TOKEN", "")
    CHANNEL_ID = os.getenv("CHAT2DESK_CHANNEL_ID", "")


reload_config()


def _headers() -> dict:
    return {"Authorization": TOKEN, "Content-Type": "application/json"}


async def _get_or_create_client(telefono: str) -> int | None:
    existing_id = await _find_client(telefono)
    if existing_id:
        return existing_id

    url = f"{API_URL}/v1/clients"
    payload = {
        "phone": telefono,
        "transport": "wa_direct",
        "channel_id": int(CHANNEL_ID),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_headers(), json=payload)

    if resp.status_code not in (200, 201):
        try:
            err = resp.json()
            existing_id = err.get("errors", {}).get("client", [None, None])[1]
            if existing_id:
                import json as _json
                cid = _json.loads(existing_id).get("id")
                if cid:
                    print(f"[chat2desk] Cliente existente (extraido de error): id={cid}")
                    return cid
        except Exception:
            pass
        print(f"[chat2desk] Error POST clients: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    if data.get("data") and data["data"].get("id"):
        client_id = data["data"]["id"]
        print(f"[chat2desk] Cliente creado: id={client_id}")
        return client_id

    print(f"[chat2desk] Respuesta inesperada al crear cliente: {data}")
    return None


async def _find_client(telefono: str) -> int | None:
    url = f"{API_URL}/v1/clients?phone={telefono}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers())

    if resp.status_code != 200:
        print(f"[chat2desk] Error GET clients: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    if data.get("meta", {}).get("total", 0) > 0 and data.get("data"):
        client = data["data"][0]
        if client.get("channel_id") == int(CHANNEL_ID):
            print(f"[chat2desk] Cliente existente con channel_id={CHANNEL_ID}: id={client['id']}")
            return client["id"]
    return None


async def send_otp_whatsapp(to_telefono: str, otp_code: str) -> tuple[bool, str | None]:
    client_id = await _get_or_create_client(to_telefono)
    if not client_id:
        return False, None

    text = f"@HSM@\nverifycode|es\n{otp_code}\n{VAR2_TEXT}\n{otp_code}"

    url = f"{API_URL}/v1/messages"
    payload = {
        "client_id": client_id,
        "text": text,
        "transport": "wa_direct",
        "channel_id": int(CHANNEL_ID),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_headers(), json=payload)

    if resp.status_code in (200, 201):
        print(f"[chat2desk] OTP enviado a {to_telefono} (client_id={client_id})")
        return True, str(client_id)
    else:
        print(f"[chat2desk] Error al enviar mensaje: {resp.status_code} {resp.text}")
        return False, None


def store_otp(telefono: str | None, email: str | None, otp_code: str) -> None:
    code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    otp_id = str(uuid.uuid4())
    otp_store[otp_id] = {
        "code_hash": code_hash,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
        "attempts": 0,
        "telefono": telefono,
        "email": email,
    }


def verify_otp(otp_code: str) -> tuple[bool, str]:
    incoming_hash = hashlib.sha256(otp_code.encode()).hexdigest()

    for otp_id, record in list(otp_store.items()):
        if record["code_hash"] != incoming_hash:
            continue

        if datetime.utcnow() > record["expires_at"]:
            otp_store.pop(otp_id, None)
            return False, "OTP expirado"

        if record["attempts"] >= 3:
            otp_store.pop(otp_id, None)
            return False, "Demasiados intentos"

        record["attempts"] += 1
        if record["code_hash"] == incoming_hash:
            otp_store.pop(otp_id, None)
            return True, "OK"
        return False, "Codigo incorrecto"

    return False, "OTP no encontrado"
