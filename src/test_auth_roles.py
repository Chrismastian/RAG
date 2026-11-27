"""
test_auth_roles.py — Uji prasyarat Fase 4: role berasal dari token, bukan dari pemanggil
Jalankan: python src/test_auth_roles.py
"""

from __future__ import annotations

import os

# Token uji -- di-set SEBELUM import modul yang membacanya.
os.environ["TOKEN_EMP_001"] = "token-uji-budi"
os.environ["TOKEN_EMP_002"] = "token-uji-sari"
os.environ["TOKEN_HR_001"] = "token-uji-rina-hr"
os.environ["WEBHOOK_API_TOKEN"] = "token-uji-legacy"

from fastapi.testclient import TestClient

import webhook_server
from auth import authenticate

# Rekam role yang BENAR-BENAR diterima bot, tanpa memanggil LLM sungguhan.
diterima: list[str] = []


def _bot_palsu(question, role=None):
    diterima.append(role)
    return {"answer": "dummy", "provider": "dummy", "warnings": []}


webhook_server.bot.answer = _bot_palsu
client = TestClient(webhook_server.app)


def _tanya(token: str, body: dict | None = None):
    return client.post(
        "/ask",
        json=body or {"question": "halo"},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_token_dipetakan_ke_role_yang_benar() -> None:
    assert authenticate("token-uji-budi").role == "employee"
    assert authenticate("token-uji-rina-hr").role == "hr"
    assert authenticate("token-uji-legacy").role == "employee"  # token lama = least privilege
    assert authenticate("ngawur") is None
    assert authenticate("") is None
    print("[LULUS] Token -> identitas/role dipetakan benar; token asing = None")


def test_role_dari_body_diabaikan() -> None:
    diterima.clear()
    # Penyerang (token employee) mencoba menyisipkan role=hr di body JSON
    r = _tanya("token-uji-budi", {"question": "gaji?", "role": "hr"})
    assert r.status_code == 200
    assert diterima == ["employee"], f"Role bocor dari body! bot menerima: {diterima}"
    assert r.json()["role"] == "employee"
    print("[LULUS] 'role: hr' di body request diabaikan; bot tetap menerima 'employee'")


def test_token_hr_menghasilkan_role_hr() -> None:
    diterima.clear()
    r = _tanya("token-uji-rina-hr")
    assert r.status_code == 200 and diterima == ["hr"]
    print("[LULUS] Token HR -> bot menerima role 'hr'")


def test_rate_limit_per_user() -> None:
    # Budi menghabiskan jatahnya; Sari (user lain) tidak boleh ikut terblokir.
    for _ in range(webhook_server.RATE_LIMIT_MAX_REQUESTS + 2):
        _tanya("token-uji-budi")
    assert _tanya("token-uji-budi").status_code == 429
    assert _tanya("token-uji-sari").status_code == 200
    print("[LULUS] Rate limit per-user: Budi kena 429, Sari tetap 200")


if __name__ == "__main__":
    test_token_dipetakan_ke_role_yang_benar()
    test_role_dari_body_diabaikan()
    test_token_hr_menghasilkan_role_hr()
    test_rate_limit_per_user()
    print("\nSemua uji identitas/role (prasyarat Fase 4) LULUS.")