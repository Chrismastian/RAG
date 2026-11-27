"""
webhook_server.py — Fase 2: Secure Webhook Agent
--------------------------------------------------
Membungkus RagChatBot (Fase 1) dengan lapisan HTTP supaya bisa dipanggil n8n:
  1. Validasi token (Bearer token, pakai secrets.compare_digest -- tahan timing attack)
  2. Rate limiting sederhana in-memory (sliding window per token)
  3. Panggil RagChatBot.answer() -- LOGIKA RAG DI FASE 1 TIDAK DIUBAH SAMA SEKALI

Jalankan server:
    uvicorn webhook_server:app --reload --port 8000

Lalu expose ke internet supaya n8n Cloud bisa menjangkau (n8n Cloud TIDAK BISA
reach localhost laptop kamu secara langsung):
    ngrok http 8000
    # atau deploy ke Render/Railway free tier untuk yang lebih permanen

Panggil endpoint:
    curl -X POST http://localhost:8000/ask \
      -H "Authorization: Bearer <isi WEBHOOK_API_TOKEN dari .env>" \
      -H "Content-Type: application/json" \
      -d '{"question": "Berapa tunjangan internet per bulan?"}'
"""

from __future__ import annotations


import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from auth import Identity, authenticate

from rag_chat import RagChatBot

load_dotenv()



# Catatan desain: karena baru ada SATU token yang valid (belum multi-user/role
# seperti Fase 3), rate limit di bawah ini pada praktiknya berlaku global untuk
# semua pemanggil yang memakai token itu -- bukan per-user. Cukup untuk n8n
# sebagai satu-satunya pemanggil di fase ini.
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

app = FastAPI(title="RAG FAQ Bot Webhook — Fase 2")

# Dibuat SEKALI saat proses server start (load model embedding + koneksi ChromaDB
# berat), dipakai ulang di semua request berikutnya -- bukan dibuat ulang per-request.
# Perlu embed_index.py sudah pernah dijalankan sebelum server ini dinyalakan,
# kalau belum, RagChatBot() di bawah akan langsung raise RuntimeError saat start.
bot = RagChatBot()

# Rate limiter in-memory sederhana: {token: deque([timestamp, ...])}
# Batasan yang jujur diakui: reset kalau proses server di-restart, dan tidak
# sinkron kalau dijalankan sebagai multi-instance (butuh Redis untuk itu --
# di luar cakupan fase ini, cukup untuk portofolio single-instance).
_request_log: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(token: str) -> bool:
    """True kalau request ini masih diizinkan; False kalau limit sudah terlampaui."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    log = _request_log[token]

    while log and log[0] < window_start:
        log.popleft()

    if len(log) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    log.append(now)
    return True


def _authenticate_request(authorization: str | None) -> Identity:
    """Header Authorization -> Identity yang ditentukan SERVER. Fail-closed."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Header 'Authorization: Bearer <token>' wajib ada")

    token = authorization[len("Bearer "):].strip()
    identity = authenticate(token)   # perbandingan constant-time ada di auth.py
    if identity is None:
        raise HTTPException(status_code=401, detail="Token tidak valid")
    return identity


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    provider: str | None
    warnings: list[str]

class AskResponse(BaseModel):
    answer: str
    role: str
    provider: str | None
    warnings: list[str]


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, authorization: str | None = Header(default=None)):
    identity = _authenticate_request(authorization)

    # Rate limit sekarang PER USER (key = user_id), bukan global per-token.
    if not _check_rate_limit(identity.user_id):
        raise HTTPException(status_code=429, detail="Rate limit terlampaui, coba lagi nanti")

    # Role datang dari identity (hasil validasi token), BUKAN dari body request.
    result = bot.answer(payload.question, role=identity.role)

    return AskResponse(
        answer=result["answer"],
        role=identity.role,
        provider=result["provider"],
        warnings=result["warnings"],
    )


@app.get("/health")
def health():
    """Endpoint ringan untuk cek server hidup, tidak butuh token (dipakai n8n/monitoring)."""
    return {"status": "ok"}
