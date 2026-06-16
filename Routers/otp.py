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
    otp_code: str = Field(min_length=1, max_length=12)


class OTPVerifyResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str


class SenderConfigResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str
    data: dict


def verify_api_key(api_key: str = Header(..., alias="API-Key")):
    expected = _get_api_key()
    if not expected:
        raise HTTPException(status_code=500, detail="OTP_API_KEY no configurada en el servidor")
    if api_key != expected:
        raise HTTPException(status_code=403, detail="API-Key invalida")
    return True


@router.post("/send", response_model=OTPSendResponse)
async def send_otp(request: OTPSendRequest, _=Depends(verify_api_key)):
    length = int(envManager.read_env("OTP_LENGTH") or "6")
    type_ = envManager.read_env("OTP_TYPE") or "alphanumeric"
    otp_code = securityUtil.generate_otp(length, type_)

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
    expected_length = int(envManager.read_env("OTP_LENGTH") or "6")
    if len(request.otp_code) != expected_length:
        return OTPVerifyResponse(errorCode=400, status="ERROR", errorMessage=f"El codigo debe tener {expected_length} caracteres")
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
        "OTP_LENGTH": int(env.get("OTP_LENGTH", "6")),
        "OTP_TYPE": env.get("OTP_TYPE", "alphanumeric"),
    }
    return SenderConfigResponse(errorCode=0, status="SUCCESS", errorMessage="OK", data=data)


class OtpParamsData(BaseModel):
    OTP_LENGTH: int
    OTP_TYPE: str


class OtpParamsResponse(BaseModel):
    errorCode: int
    status: str
    errorMessage: str
    data: OtpParamsData


class OtpParamsUpdate(BaseModel):
    length: int | None = Field(default=None, ge=4, le=12)
    type: str | None = Field(default=None, pattern=r"^(numeric|alphanumeric)$")


@router.patch("/params", response_model=OtpParamsResponse)
def patch_otp_params(params: OtpParamsUpdate, _=Depends(verify_api_key)):
    updates = {}
    if params.length is not None:
        updates["OTP_LENGTH"] = str(params.length)
    if params.type is not None:
        updates["OTP_TYPE"] = params.type
    if not updates:
        return OtpParamsResponse(errorCode=400, status="ERROR", errorMessage="No hay campos para actualizar", data=OtpParamsData(OTP_LENGTH=0, OTP_TYPE=""))
    if not envManager.update_env(updates):
        return OtpParamsResponse(errorCode=500, status="ERROR", errorMessage="Error al escribir .env", data=OtpParamsData(OTP_LENGTH=0, OTP_TYPE=""))
    length = int(envManager.read_env("OTP_LENGTH") or "6")
    type_ = envManager.read_env("OTP_TYPE") or "alphanumeric"
    return OtpParamsResponse(errorCode=0, status="SUCCESS", errorMessage="OK", data=OtpParamsData(OTP_LENGTH=length, OTP_TYPE=type_))
