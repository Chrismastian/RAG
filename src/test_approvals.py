"""
test_approvals.py — Uji keamanan Langkah 4: approval gate (tanpa LLM, tanpa jaringan)
Jalankan: python src/test_approvals.py
"""

from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

import agent_tools
import approvals
from agent_tools import TOOLS, ToolContext, execute_tool, resolve_approval, tools_for_role
from approvals import ApprovalError
from auth import Identity

BUDI = Identity("emp-001", "Budi", "employee")
SARI = Identity("emp-002", "Sari", "employee")
RINA = Identity("hr-001", "Rina", "hr")

# Semua file tulis diarahkan ke folder sementara: tes tidak mengotori logs/ aslimu.
_tmp = Path(tempfile.mkdtemp())


def reset() -> None:
    approvals.STORE_FILE = _tmp / "approvals.json"
    agent_tools.LEAVE_REQUESTS_FILE = _tmp / "leave_requests.jsonl"
    for f in (approvals.STORE_FILE, agent_tools.LEAVE_REQUESTS_FILE):
        f.unlink(missing_ok=True)


def efek_nyata() -> list[dict]:
    """Isi 'efek nyata' aksi: baris yang ditulis HANYA oleh handler setelah approval."""
    f = agent_tools.LEAVE_REQUESTS_FILE
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []


def ajukan(identity: Identity, mulai_dalam_hari: int = 10, lama: int = 3):
    mulai = date.today() + timedelta(days=mulai_dalam_hari)
    selesai = mulai + timedelta(days=lama - 1)
    args = {"start_date": mulai.isoformat(), "end_date": selesai.isoformat(), "reason": "liburan keluarga"}
    return execute_tool("submit_leave_request", json.dumps(args), ToolContext(identity, bot=None))


def test_aksi_tertahan_sebelum_disetujui() -> None:
    reset()
    r = ajukan(BUDI)
    assert r.ok and r.pending_approval_id and "BELUM dijalankan" in r.content
    assert efek_nyata() == [], "Handler berjalan sebelum approval!"
    assert approvals.get(r.pending_approval_id)["status"] == "pending"
    print("[LULUS] Pengajuan cuti tertahan: status pending, efek nyata belum terjadi")


def test_validasi_bisnis_sebelum_antrean() -> None:
    reset()
    c = ToolContext(BUDI, bot=None)
    hari = lambda n: (date.today() + timedelta(days=n)).isoformat()
    kasus = {
        "format salah": {"start_date": "12/12/2026", "end_date": "14/12/2026", "reason": "x"},
        "akhir < mulai": {"start_date": hari(12), "end_date": hari(10), "reason": "x"},
        "terlalu lama": {"start_date": hari(10), "end_date": hari(40), "reason": "x"},
        "kurang dari H-3": {"start_date": hari(1), "end_date": hari(2), "reason": "x"},
        "tanggal lampau": {"start_date": "2020-01-01", "end_date": "2020-01-02", "reason": "x"},
    }
    for nama, args in kasus.items():
        r = execute_tool("submit_leave_request", json.dumps(args), c)
        assert not r.ok and r.pending_approval_id is None, f"Kasus '{nama}' lolos!"
    assert approvals._load() == {}, "Ada sampah masuk antrean"
    print("[LULUS] Format/urutan/durasi/H-3 divalidasi sebelum masuk antrean")


def test_employee_tidak_bisa_menyetujui() -> None:
    reset()
    apr = ajukan(BUDI).pending_approval_id
    try:
        resolve_approval(apr, SARI, True)
        raise AssertionError("Employee berhasil menyetujui!")
    except ApprovalError:
        pass
    assert approvals.get(apr)["status"] == "pending" and efek_nyata() == []
    print("[LULUS] Role employee tidak bisa menyetujui")


def test_tidak_boleh_menyetujui_sendiri() -> None:
    reset()
    apr = ajukan(RINA).pending_approval_id   # HR mengajukan cutinya sendiri
    try:
        resolve_approval(apr, RINA, True)
        raise AssertionError("HR menyetujui permintaannya sendiri!")
    except ApprovalError:
        pass
    assert efek_nyata() == []
    print("[LULUS] Self-approval ditolak, bahkan untuk HR")


def test_hr_menyetujui_dan_eksekusi_atas_nama_pemohon() -> None:
    reset()
    r = ajukan(BUDI)
    rec = resolve_approval(r.pending_approval_id, RINA, True)
    assert rec["status"] == "executed" and rec["decided_by"] == "hr-001"
    efek = efek_nyata()
    assert len(efek) == 1 and efek[0]["requester"] == "emp-001"   # pemohon asli, bukan HR
    assert efek[0]["reason"] == "liburan keluarga"                 # argumen yang dibekukan
    print("[LULUS] HR menyetujui -> dieksekusi 1x atas nama pemohon, argumen sama dengan pengajuan")


def test_replay_ditolak() -> None:
    reset()
    apr = ajukan(BUDI).pending_approval_id
    resolve_approval(apr, RINA, True)
    for percobaan in (True, False):
        try:
            resolve_approval(apr, RINA, percobaan)
            raise AssertionError("Approval kedua lolos (replay)!")
        except ApprovalError:
            pass
    assert len(efek_nyata()) == 1
    print("[LULUS] Menyetujui/menolak ulang permintaan yang sudah diputuskan -> ditolak")


def test_penolakan_tidak_mengeksekusi() -> None:
    reset()
    apr = ajukan(BUDI).pending_approval_id
    rec = resolve_approval(apr, RINA, False)
    assert rec["status"] == "rejected" and efek_nyata() == []
    print("[LULUS] Permintaan ditolak HR -> tidak ada efek nyata")


def test_batas_antrean_per_user() -> None:
    reset()
    for _ in range(approvals.MAX_PENDING_PER_USER):
        assert ajukan(BUDI).ok
    r = ajukan(BUDI)
    assert not r.ok and "Terlalu banyak" in r.content
    assert ajukan(SARI).ok   # user lain tidak terdampak
    print("[LULUS] Antrean pending dibatasi per user; user lain tak terdampak")


def test_model_tidak_punya_jalur_approve() -> None:
    nama_semua = set(TOOLS)
    assert not any("approv" in n or "decide" in n or "resolve" in n for n in nama_semua)
    for role in ("employee", "hr"):
        assert not any("approv" in t["function"]["name"] for t in tools_for_role(role))
    r = execute_tool("approve_request", '{"id": "apr-123"}', ToolContext(RINA, bot=None))
    assert not r.ok
    print("[LULUS] Tidak ada tool untuk menyetujui: persetujuan hanya lewat jalur manusia")


if __name__ == "__main__":
    test_aksi_tertahan_sebelum_disetujui()
    test_validasi_bisnis_sebelum_antrean()
    test_employee_tidak_bisa_menyetujui()
    test_tidak_boleh_menyetujui_sendiri()
    test_hr_menyetujui_dan_eksekusi_atas_nama_pemohon()
    test_replay_ditolak()
    test_penolakan_tidak_mengeksekusi()
    test_batas_antrean_per_user()
    test_model_tidak_punya_jalur_approve()
    print("\nSemua uji approval gate (Langkah 4) LULUS.")