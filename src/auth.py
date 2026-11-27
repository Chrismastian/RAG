"""
auth.py — Fase 4 (prasyarat): token -> identitas terotentikasi
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from access_control import normalize_role

USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"


@dataclass(frozen=True)  # frozen = tidak bisa diubah setelah dibuat
class Identity:
    user_id: str
    name: str
    role: str


def _load_users() -> list[dict]:
    with open(USERS_FILE, encoding="utf-8") as f:
        return json.load(f)["users"]


def _same(a: str, b: str) -> bool:
    # Diubah ke bytes: compare_digest versi str error (TypeError) kalau ada karakter non-ASCII.
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def authenticate(token: str) -> Identity | None:
    """Kembalikan Identity kalau token dikenal, None kalau tidak."""
    if not token:
        return None

    found: Identity | None = None

    # Sengaja memeriksa SEMUA kandidat tanpa berhenti di yang pertama cocok,
    # supaya waktu respons tidak membocorkan "token ini milik user urutan ke berapa".
    for user in _load_users():
        expected = os.environ.get(user["token_env"], "").strip()
        if expected and _same(token, expected):
            found = Identity(
                user_id=user["user_id"],
                name=user["name"],
                role=normalize_role(user["role"]),  # typo di users.json -> jatuh ke employee
            )

    # Token lama Fase 2 tetap diterima, tapi dipetakan ke role PALING RENDAH.
    legacy = os.environ.get("WEBHOOK_API_TOKEN", "").strip()
    if legacy and _same(token, legacy):
        found = found or Identity("n8n-legacy", "n8n (token lama Fase 2)", "employee")

    return found