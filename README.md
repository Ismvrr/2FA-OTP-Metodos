# OTP Service

Servicio independiente para envío y verificación de códigos OTP por Email (SMTP Brevo) y WhatsApp (Chat2Desk API con HSM template).

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

# Parámetros del OTP (configurables via PATCH /otp/params)
OTP_LENGTH=6
OTP_TYPE=alphanumeric
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

## Despliegue con systemd

```ini
[Unit]
Description=2FA OTP Service
After=network.target

[Service]
Type=simple
User=deployer
WorkingDirectory=/ruta/al/proyecto/otp-service
ExecStart=/ruta/al/proyecto/otp-service/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now 2fa-otp.service
sudo systemctl restart 2fa-otp.service
```

## Autenticación

Todas las rutas requieren el header:

```
API-Key: tu-api-key
```

## Endpoints

---

### `POST /otp/send`

Envía un código OTP al canal especificado. La longitud y el tipo (numeric/alphanumeric) se leen del `.env` en cada request — no necesita reinicio tras un `PATCH /otp/params`.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `method` | string | sí | `email`, `whatsapp`, o `both` |
| `email` | string | según method | Correo destino |
| `telefono` | string | según method | Teléfono destino (WhatsApp, formato `52155...`) |

**Ejemplos:**

```json
{"method": "email", "email": "usuario@ejemplo.com"}
{"method": "whatsapp", "telefono": "521550000000"}
{"method": "both", "email": "usuario@ejemplo.com", "telefono": "521550000000"}
```

**Respuesta exitosa:**
```json
{"errorCode": 0, "status": "SUCCESS", "errorMessage": "OK"}
```

**Respuesta con error:**
```json
{"errorCode": 500, "status": "ERROR", "errorMessage": "Error al enviar WhatsApp"}
```

**Ejemplo con curl:**
```bash
curl -X POST https://2fa.chat2desk.support/otp/send \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"method": "email", "email": "usuario@ejemplo.com"}'
```

---

### `POST /otp/verify`

Verifica un código OTP. Cada código puede verificarse **una sola vez** y expira a los **5 minutos**. Máximo **3 intentos** por código.

**Body:**
```json
{"otp_code": "AB12CD"}
```

La longitud esperada se valida contra `OTP_LENGTH` del `.env`. Si no coincide, responde con `errorCode: 400`.

**Respuesta exitosa:**
```json
{"errorCode": 0, "status": "SUCCESS", "errorMessage": "OK"}
```

**Respuestas de error:**

| errorCode | errorMessage | Descripción |
|-----------|-------------|-------------|
| 400 | El codigo debe tener N caracteres | Longitud incorrecta según config |
| 401 | OTP no encontrado | Código nunca enviado o ya consumido |
| 401 | OTP expirado | Pasaron más de 5 minutos |
| 401 | Demasiados intentos | 3 intentos fallidos agotados |

**Ejemplo con curl:**
```bash
curl -X POST https://2fa.chat2desk.support/otp/verify \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"otp_code": "AB12CD"}'
```

---

### `GET /otp/config`

Muestra la configuración actual del servidor. Las contraseñas y tokens se muestran como `********`.

**Ejemplo con curl:**
```bash
curl https://2fa.chat2desk.support/otp/config \
  -H "API-Key: tu-api-key"
```

**Respuesta:**
```json
{
  "errorCode": 0,
  "status": "SUCCESS",
  "errorMessage": "OK",
  "data": {
    "MAIL_FROM": "info@chat2desk.mx",
    "MAIL_USER": "8a404c001@smtp-brevo.com",
    "MAIL_PASSWORD": "********",
    "MAIL_SERVER": "smtp-relay.brevo.com",
    "MAIL_PORT": "587",
    "CHAT2DESK_TOKEN": "********",
    "CHAT2DESK_CHANNEL_ID": "16673",
    "OTP_LENGTH": 6,
    "OTP_TYPE": "alphanumeric"
  }
}
```

---

### `PATCH /otp/params`

Actualiza los parámetros de generación del OTP. Los cambios se reflejan en el siguiente `POST /otp/send` sin reiniciar el servidor.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `length` | int | no | Longitud del OTP (4-12) |
| `type` | string | no | `numeric` o `alphanumeric` |

Se pueden enviar uno o ambos campos.

**Ejemplo:**
```json
{"length": 8, "type": "numeric"}
```

**Respuesta:**
```json
{
  "errorCode": 0,
  "status": "SUCCESS",
  "errorMessage": "OK",
  "data": {
    "OTP_LENGTH": 8,
    "OTP_TYPE": "numeric"
  }
}
```

**Ejemplo con curl:**
```bash
curl -X PATCH https://2fa.chat2desk.support/otp/params \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"length": 8, "type": "numeric"}'
```

---

## Flujo completo (ejemplo)

```bash
# 1. Configurar OTP de 8 dígitos numéricos
curl -X PATCH https://2fa.chat2desk.support/otp/params \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"length": 8, "type": "numeric"}'

# 2. Enviar OTP por email
curl -X POST https://2fa.chat2desk.support/otp/send \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"method": "email", "email": "usuario@ejemplo.com"}'

# 3. Verificar el código recibido
curl -X POST https://2fa.chat2desk.support/otp/verify \
  -H "API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"otp_code": "12345678"}'
```

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
| Configuracion | `GET /otp/config`, `PATCH /otp/params` |

Variables a configurar:

| Variable | Valor |
|----------|-------|
| `base_url` | `https://tudominio.com` |
| `api_key` | Tu API Key |

## Consideraciones

- Los OTP se almacenan **en memoria** (volátil). Un reinicio del servidor pierde los códigos activos.
- Las credenciales sensibles (`MAIL_PASSWORD`, `CHAT2DESK_TOKEN`) se cifran con AES (Fernet) en el archivo `.env`.
- La clave de cifrado está en `ENCRYPTION_KEY` del `.env`.
- La longitud y tipo del OTP se leen del `.env` en cada request, por lo que un `PATCH /otp/params` se refleja sin reiniciar el servidor.
