# OTP Service

Servicio independiente para envío y verificación de códigos OTP por Email (SMTP) y WhatsApp (Chat2Desk API).

## Stack

- **FastAPI** — framework web
- **Uvicorn** — servidor ASGI
- **Brevo SMTP** — envío de correos
- **Chat2Desk API** — envío de WhatsApp (HSM templates)
- **Cryptography (Fernet)** — cifrado de credenciales en reposo

## Requisitos

- Python 3.12+
- Cuenta Brevo (SMTP) — para email
- Cuenta Chat2Desk con WhatsApp Business API — para WhatsApp
- Token y channel_id de Chat2Desk
- Plantilla HSM `verifycode` (idioma `es`) aprobada en Meta

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Brevo SMTP
MAIL_FROM=info@tudominio.com
MAIL_USER=usuario@smtp-brevo.com
MAIL_PASSWORD=tu-contraseña-smtp
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587

# API Key para autenticar las peticiones
OTP_API_KEY=cambia-esta-clave

# Clave para cifrado de credenciales en .env
ENCRYPTION_KEY=una-clave-segura-de-32-caracteres

# Chat2Desk
CHAT2DESK_API_URL=https://api.chat2desk.com.mx
CHAT2DESK_TOKEN=tu-token-chat2desk
CHAT2DESK_CHANNEL_ID=tu-channel-id
```

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Autenticación

Todas las rutas requieren el header:

```
API-Key: tu-api-key
```

## Endpoints

### `POST /otp/send`

Envía un código OTP de 6 caracteres alfanuméricos al canal especificado.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `method` | string | sí | `email`, `whatsapp`, o `both` |
| `email` | string | según method | Correo destino |
| `telefono` | string | según method | Teléfono destino (WhatsApp, formato `5255...`) |

**Ejemplos:**

```json
{"method": "email", "email": "usuario@ejemplo.com"}
{"method": "whatsapp", "telefono": "525500000000"}
{"method": "both", "email": "usuario@ejemplo.com", "telefono": "525500000000"}
```

**Respuesta exitosa:**
```json
{"errorCode": 0, "status": "SUCCESS", "errorMessage": "OK"}
```

**Respuesta con error:**
```json
{"errorCode": 500, "status": "ERROR", "errorMessage": "Error al enviar WhatsApp"}
```

---

### `POST /otp/verify`

Verifica un código OTP. Cada código puede verificarse **una sola vez** y expira a los **5 minutos**. Máximo **3 intentos** por código.

**Body:**
```json
{"otp_code": "AB12CD"}
```

**Respuesta exitosa:**
```json
{"errorCode": 0, "status": "SUCCESS", "errorMessage": "OK"}
```

**Respuestas de error:**
```json
{"errorCode": 401, "status": "ERROR", "errorMessage": "OTP no encontrado"}
{"errorCode": 401, "status": "ERROR", "errorMessage": "OTP expirado"}
{"errorCode": 401, "status": "ERROR", "errorMessage": "Demasiados intentos"}
```

---

### `GET /otp/config`

Muestra la configuración actual. Las contraseñas y tokens se muestran como `********`.

## Documentación interactiva

Con el servidor corriendo, abrir:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Postman

Incluye el archivo `2FA-OTP-Postman.json` en la raíz. Importar en Postman y configurar las variables. La colección está organizada en 3 carpetas:

| Carpeta | Métodos |
|---------|---------|
| Envio de OTP | `POST /otp/send` (email, whatsapp, both) |
| Verificacion de OTP | `POST /otp/verify` |
| Configuracion | `GET /otp/config` |

Variables a configurar:

| Variable | Valor |
|----------|-------|
| `base_url` | `https://tudominio.com` |
| `api_key` | Tu API Key |

## Consideraciones

- Los OTP se almacenan **en memoria** (volátil). Un reinicio del servidor pierde los códigos activos.
- Las credenciales sensibles (`MAIL_PASSWORD`, `CHAT2DESK_TOKEN`) se cifran con AES (Fernet) en el archivo `.env`.
- La clave de cifrado está en `ENCRYPTION_KEY` del `.env`.
