import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

MAIL_FROM: str | None = None
MAIL_USER: str | None = None
MAIL_PASSWORD: str | None = None
MAIL_SERVER: str | None = None
MAIL_PORT: int = 587


def reload_config():
    global MAIL_FROM, MAIL_USER, MAIL_PASSWORD, MAIL_SERVER, MAIL_PORT
    MAIL_FROM = os.getenv("MAIL_FROM", "")
    MAIL_USER = os.getenv("MAIL_USER", "") or os.getenv("MAIL_FROM", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))


reload_config()


def send_otp_email_sync(to_email: str, otp_code: str, username: str) -> bool:
    if not MAIL_FROM or not MAIL_PASSWORD:
        print("[mailService] MAIL_FROM o MAIL_PASSWORD no configurados")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Tu codigo de verificacion - 2FA"
        msg["From"] = MAIL_FROM
        msg["To"] = to_email

        html = f"""<html><body style="font-family: Arial, sans-serif; text-align: center; padding: 40px;">
            <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-bottom: 8px;">Codigo de verificacion</h2>
                <p style="color: #666; font-size: 16px;">Hola <strong>{username}</strong>,</p>
                <p style="color: #666;">Ingresa el siguiente codigo para completar tu inicio de sesion:</p>
                <div style="font-size: 42px; letter-spacing: 10px; font-weight: bold; color: #2d2d2d; background: #f5f5f5; padding: 20px; border-radius: 12px; margin: 24px auto; max-width: 280px; font-family: 'Courier New', monospace;">{otp_code}</div>
                <p style="color: #999; font-size: 14px;">Valido por 5 minutos. No compartas este codigo con nadie.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="color: #aaa; font-size: 12px;">Si no solicitaste este codigo, ignora este correo.</p>
            </div>
        </body></html>"""

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_FROM, [to_email], msg.as_string())

        print(f"[mailService] OTP enviado correctamente a {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print(f"[mailService] Error de autenticacion SMTP")
        return False
    except smtplib.SMTPException as e:
        print(f"[mailService] Error SMTP: {e}")
        return False
    except Exception as e:
        print(f"[mailService] Error inesperado: {e}")
        return False


async def send_otp_email(to_email: str, otp_code: str, username: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_otp_email_sync, to_email, otp_code, username)
