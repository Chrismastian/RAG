"""
test_webhook_security.py — Uji Keamanan Fase 2 (Webhook)
-----------------------------------------------------------
Beda dengan security_test.py (menguji RagChatBot langsung / prompt injection),
file ini menguji LAPISAN HTTP di webhook_server.py: validasi token & rate limit.

Pakai FastAPI TestClient -- tidak perlu uvicorn benar-benar berjalan untuk
menjalankan file ini, tapi TETAP butuh ChromaDB sudah ter-index (artinya
`python src/embed_index.py` harus sudah pernah dijalankan), karena
mengimpor webhook_server otomatis membuat instance RagChatBot.

Jalankan: python src/test_webhook_security.py
"""

from __future__ import annotations

import os

# WAJIB di-set SEBELUM import webhook_server, karena modul itu membaca
# WEBHOOK_API_TOKEN dari environment persis saat di-import (sekali saja).
# Ini sengaja pakai token khusus-uji, supaya tes ini tidak bergantung pada
# apa pun yang kebetulan ada di .env asli kamu.
os.environ["WEBHOOK_API_TOKEN"] = "token-uji-coba-fase2"

from fastapi.testclient import TestClient

import webhook_server
from webhook_server import app, RATE_LIMIT_MAX_REQUESTS

TEST_TOKEN = "token-uji-coba-fase2"

# Supaya uji rate-limit & token tidak memboroskan kuota API LLM asli dan tidak
# butuh koneksi internet -- yang diuji DI SINI adalah lapisan webhook (token +
# rate limit), bukan kualitas jawaban RAG (itu sudah diuji terpisah di
# security_test.py lewat RagChatBot langsung).
webhook_server.bot.answer = lambda question: {
    "answer": "(jawaban dummy untuk uji webhook)",
    "provider": "dummy",
    "warnings": [],
}

client = TestClient(app)


def test_tanpa_token_ditolak() -> None:
    response = client.post("/ask", json={"question": "test"})
    assert response.status_code == 401, f"Harusnya 401, malah {response.status_code}"
    print("[LULUS] Request tanpa header Authorization ditolak (401)")


def test_token_salah_ditolak() -> None:
    response = client.post(
        "/ask",
        json={"question": "test"},
        headers={"Authorization": "Bearer token-yang-salah"},
    )
    assert response.status_code == 401, f"Harusnya 401, malah {response.status_code}"
    print("[LULUS] Request dengan token salah ditolak (401)")


def test_format_header_salah_ditolak() -> None:
    # Lupa prefix "Bearer "
    response = client.post(
        "/ask",
        json={"question": "test"},
        headers={"Authorization": TEST_TOKEN},
    )
    assert response.status_code == 401, f"Harusnya 401, malah {response.status_code}"
    print("[LULUS] Header tanpa prefix 'Bearer ' ditolak (401)")


def test_token_benar_diterima() -> None:
    response = client.post(
        "/ask",
        json={"question": "Berapa tunjangan internet per bulan?"},
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert response.status_code == 200, f"Harusnya 200, malah {response.status_code}: {response.text}"
    assert response.json()["answer"] == "(jawaban dummy untuk uji webhook)"
    print("[LULUS] Request dengan token benar diterima (200)")


def test_rate_limit_terlampaui() -> None:
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    last_status = None
    for i in range(RATE_LIMIT_MAX_REQUESTS + 5):
        response = client.post("/ask", json={"question": f"test ke-{i}"}, headers=headers)
        last_status = response.status_code
    assert last_status == 429, f"Request terakhir harusnya 429 (limit terlampaui), malah {last_status}"
    print(f"[LULUS] Setelah {RATE_LIMIT_MAX_REQUESTS} request, request berikutnya ditolak (429)")


def test_health_tidak_butuh_token() -> None:
    response = client.get("/health")
    assert response.status_code == 200, f"Harusnya 200, malah {response.status_code}"
    print("[LULUS] Endpoint /health bisa diakses tanpa token")


if __name__ == "__main__":
    test_tanpa_token_ditolak()
    test_token_salah_ditolak()
    test_format_header_salah_ditolak()
    test_token_benar_diterima()
    test_rate_limit_terlampaui()
    test_health_tidak_butuh_token()
    print("\nSemua uji keamanan webhook (Fase 2) selesai dan LULUS.")
