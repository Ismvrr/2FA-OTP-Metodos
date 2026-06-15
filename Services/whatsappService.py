import os
from Services import chat2deskService

CHAT2DESK_API_URL: str | None = None
CHAT2DESK_TOKEN: str | None = None
CHAT2DESK_CHANNEL_ID: str | None = None


def reload_config():
    global CHAT2DESK_API_URL, CHAT2DESK_TOKEN, CHAT2DESK_CHANNEL_ID
    chat2deskService.reload_config()


reload_config()


async def send_otp_whatsapp(to_telefono: str, otp_code: str) -> tuple[bool, str | None]:
    return await chat2deskService.send_otp_whatsapp(to_telefono, otp_code)
