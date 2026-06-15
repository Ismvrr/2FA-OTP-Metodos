import os
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from Utils import securityUtil, envManager
from Services import mailService, whatsappService, chat2deskService

router = APIRouter(prefix="/otp", tags=["OTP"])


def _get_api_key() -> str | None:
    return os.getenv("OTP_API_KEY") or envManager.read_env("OTP_API_KEY")


class OTPSendRequest(BaseModel):
    email: str | None = Field(default=None)
    telefono: str | None = Field(default=None)
    method: str = Field(pattern=r"^(email|whatsapp|both)$")


class OTPSendResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str


class OTPVerifyRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=6)


class OTPVerifyResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str


class SenderConfigResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str
    data: dict


class SenderConfigUpdate(BaseModel):
    MAIL_FROM: str | None = Field(default=None)
    MAIL_USER: str | None = Field(default=None)
    MAIL_PASSWORD: str | None = Field(default=None)
    MAIL_SERVER: str | None = Field(default=None)
    MAIL_PORT: int | None = Field(default=None)
    CHAT2DESK_TOKEN: str | None = Field(default=None)
    CHAT2DESK_CHANNEL_ID: str | None = Field(default=None)


def verify_api_key(api_key: str = Header(..., alias="API-Key")):
    expected = _get_api_key()
    if not expected:
        raise HTTPException(status_code=500, detail="OTP_API_KEY no configurada en el servidor")
    if api_key != expected:
        raise HTTPException(status_code=403, detail="API-Key invalida")
    return True


@router.post("/send", response_model=OTPSendResponse)
async def send_otp(request: OTPSendRequest, _=Depends(verify_api_key)):
    otp_code = securityUtil.generate_otp(6, "alphanumeric")

    email_sent = False
    whatsapp_sent = False
    whatsapp_client_id = None
    email_to = None
    telefono_to = None

    if request.method in ("email", "both"):
        if not request.email:
            return OTPSendResponse(errorCode=400, status="ERROR", errorMessage="email requerido para method='email' o 'both'")
        email_to = request.email
        email_sent = await mailService.send_otp_email(
            to_email=email_to,
            otp_code=otp_code,
            username=email_to.split("@")[0]
        )

    if request.method in ("whatsapp", "both"):
        if not request.telefono:
            return OTPSendResponse(errorCode=400, status="ERROR", errorMessage="telefono requerido para method='whatsapp' o 'both'")
        telefono_to = request.telefono
        whatsapp_sent, whatsapp_client_id = await whatsappService.send_otp_whatsapp(
            to_telefono=telefono_to,
            otp_code=otp_code
        )

    chat2deskService.store_otp(telefono_to, email_to, otp_code)

    if request.method == "email" and not email_sent:
        return OTPSendResponse(errorCode=500, status="ERROR", errorMessage="Error al enviar email")

    if request.method == "whatsapp" and not whatsapp_sent:
        return OTPSendResponse(errorCode=500, status="ERROR", errorMessage="Error al enviar WhatsApp")

    if request.method == "both":
        errores = []
        if not email_sent:
            errores.append("email")
        if not whatsapp_sent:
            errores.append("whatsapp")
        if errores:
            return OTPSendResponse(errorCode=500, status="ERROR", errorMessage=f"Error al enviar: {', '.join(errores)}")

    return OTPSendResponse(errorCode=0, status="SUCCESS", errorMessage="OK")


@router.post("/verify", response_model=OTPVerifyResponse)
def verify_otp(request: OTPVerifyRequest, _=Depends(verify_api_key)):
    ok, msg = chat2deskService.verify_otp(request.otp_code)
    if ok:
        return OTPVerifyResponse(errorCode=0, status="SUCCESS", errorMessage="OK")
    return OTPVerifyResponse(errorCode=401, status="ERROR", errorMessage=msg)


@router.get("/config", response_model=SenderConfigResponse)
def get_sender_config(_=Depends(verify_api_key)):
    env = envManager.read_all_env()
    data = {
        "MAIL_FROM": env.get("MAIL_FROM", ""),
        "MAIL_USER": env.get("MAIL_USER", ""),
        "MAIL_PASSWORD": "********" if env.get("MAIL_PASSWORD") else "",
        "MAIL_SERVER": env.get("MAIL_SERVER", ""),
        "MAIL_PORT": env.get("MAIL_PORT", ""),
        "CHAT2DESK_TOKEN": "********" if env.get("CHAT2DESK_TOKEN") else "",
        "CHAT2DESK_CHANNEL_ID": env.get("CHAT2DESK_CHANNEL_ID", ""),
    }
    return SenderConfigResponse(errorCode=0, status="SUCCESS", errorMessage="OK", data=data)


@router.patch("/config", response_model=SenderConfigResponse)
def patch_sender_config(updates: SenderConfigUpdate, _=Depends(verify_api_key)):
    filtered = {k: str(v) for k, v in updates.model_dump(exclude_none=True).items()}
    if not filtered:
        return SenderConfigResponse(errorCode=400, status="ERROR", errorMessage="No hay campos para actualizar", data={})
    ok = envManager.update_env(filtered)
    if not ok:
        return SenderConfigResponse(errorCode=500, status="ERROR", errorMessage="Error al escribir .env", data={})

    os.environ.update(filtered)
    mailService.reload_config()
    whatsappService.reload_config()

    return get_sender_config(_)


@router.put("/config", response_model=SenderConfigResponse)
def put_sender_config(updates: SenderConfigUpdate, _=Depends(verify_api_key)):
    return patch_sender_config(updates, _)
