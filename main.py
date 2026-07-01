import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routers import otp

LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "api.log"),
    maxBytes=10_000_000,
    backupCount=5
)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

logging.basicConfig(handlers=[handler], level=logging.INFO)
logger = logging.getLogger("2fa")

app = FastAPI(title="2FA - OTP Service")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"REQUEST  {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"RESPONSE {request.method} {request.url.path} -> {response.status_code}")
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(otp.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
