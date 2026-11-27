"""
audit.py — Fase 4: jejak audit append-only (satu baris JSON per kejadian)
-------------------------------------------------------------------------
Tujuan: setelah kejadian, kamu bisa menjawab "siapa meminta apa, tool apa yang
dipanggil, apa yang ditolak, apa yang disetujui" -- tanpa menyimpan token/rahasia.
Gagal menulis log TIDAK menjatuhkan request (dicatat ke logger); di produksi
sungguhan, pertimbangkan fail-closed untuk aksi berisiko.
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("audit")

AUDIT_FILE = Path(__file__).parent.parent / "logs" / "agent_audit.jsonl"
_LOCK = threading.Lock()


def new_request_id() -> str:
    return "req-" + secrets.token_hex(4)


def clip(text: object, limit: int = 300) -> str:
    """Potong teks panjang supaya log tidak membengkak / tidak jadi tempat sampah data."""
    s = str(text)
    return s if len(s) <= limit else s[:limit] + f"...[+{len(s) - limit} karakter]"


def log_event(event: str, request_id: str, **fields) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "request_id": request_id,
        **fields,
    }
    try:
        with _LOCK:
            AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("Gagal menulis audit log")