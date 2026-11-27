"""
approvals.py — Fase 4: approval gate untuk aksi berisiko
--------------------------------------------------------
Agent hanya boleh MENGAJUKAN aksi berisiko. Aksi baru jalan setelah manusia
yang berwenang menyetujuinya lewat jalur yang TIDAK bisa dipanggil oleh model.

Siklus status (satu arah, tidak bisa mundur):
    pending ──approve──▶ approved ──▶ executed | failed
        └─────reject───▶ rejected
Penyimpanan: file JSON di logs/ (cukup untuk portofolio single-instance).
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from access_control import can_approve
from auth import Identity

STORE_FILE = Path(__file__).parent.parent / "logs" / "approvals.json"
MAX_PENDING_PER_USER = 5   # cegah agent/penanya membanjiri antrean approver

_LOCK = threading.Lock()   # endpoint FastAPI berjalan di banyak thread


class ApprovalError(Exception):
    """Aksi approval ditolak oleh aturan (bukan bug)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict:
    if not STORE_FILE.exists():
        return {}
    with open(STORE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_pending(requester: Identity, tool: str, args: dict) -> dict:
    """Catat permintaan. Identitas pemohon diambil dari SERVER (Identity), bukan dari argumen."""
    with _LOCK:
        data = _load()
        jumlah_pending = sum(
            1 for r in data.values()
            if r["requester_id"] == requester.user_id and r["status"] == "pending"
        )
        if jumlah_pending >= MAX_PENDING_PER_USER:
            raise ApprovalError("Terlalu banyak permintaan yang masih menunggu persetujuan.")

        approval_id = "apr-" + secrets.token_hex(4)
        data[approval_id] = {
            "id": approval_id,
            "status": "pending",
            "tool": tool,
            "args": args,                       # DIBEKUKAN: yang disetujui = yang dieksekusi
            "requester_id": requester.user_id,
            "requester_name": requester.name,
            "requester_role": requester.role,
            "created_at": _now(),
            "decided_by": None,
            "decided_at": None,
            "result": None,
        }
        _save(data)
        return dict(data[approval_id])


def get(approval_id: str) -> dict | None:
    with _LOCK:
        return _load().get(approval_id)


def decide(approval_id: str, approver: Identity, approve: bool) -> dict:
    """Setujui/tolak. Aturan di sini -- BUKAN di prompt, BUKAN di model."""
    with _LOCK:
        data = _load()
        rec = data.get(approval_id)
        if rec is None:
            raise ApprovalError("Permintaan tidak ditemukan.")
        if not can_approve(approver.role):
            raise ApprovalError("Role Anda tidak berwenang menyetujui.")
        if approver.user_id == rec["requester_id"]:
            raise ApprovalError("Tidak boleh menyetujui permintaan sendiri.")
        if rec["status"] != "pending":
            raise ApprovalError(f"Permintaan sudah berstatus '{rec['status']}'.")   # cegah replay

        rec["status"] = "approved" if approve else "rejected"
        rec["decided_by"] = approver.user_id
        rec["decided_at"] = _now()
        _save(data)
        return dict(rec)


def finish(approval_id: str, ok: bool, result: str) -> dict:
    with _LOCK:
        data = _load()
        rec = data[approval_id]
        rec["status"] = "executed" if ok else "failed"
        rec["result"] = result
        _save(data)
        return dict(rec)