"""
test_agent_tools.py — Uji keamanan Langkah 3 (tanpa LLM, tanpa jaringan)
Jalankan: python src/test_agent_tools.py
"""

from __future__ import annotations

from agent_tools import MAX_RESULT_CHARS, TOOLS, ToolContext, execute_tool, tools_for_role
from auth import Identity


class BotPalsu:
    def __init__(self) -> None:
        self.role_diterima: list[str] = []

    def retrieve(self, query: str, role: str = "employee", top_k: int = 3) -> list[str]:
        self.role_diterima.append(role)
        return [f"kutipan untuk '{query}'"]


BUDI = Identity("emp-001", "Budi", "employee")
SARI = Identity("emp-002", "Sari", "employee")
RINA = Identity("hr-001", "Rina", "hr")


def ctx(identity: Identity, bot: BotPalsu | None = None) -> ToolContext:
    return ToolContext(identity=identity, bot=bot or BotPalsu())


def test_employee_tidak_ditawari_tool_hr() -> None:
    nama = [t["function"]["name"] for t in tools_for_role("employee")]
    assert "lookup_leave_balance" not in nama and "get_leave_balance" in nama
    assert "lookup_leave_balance" in [t["function"]["name"] for t in tools_for_role("hr")]
    print("[LULUS] Employee tidak ditawari tool khusus HR; HR ditawari")


def test_tool_hr_dipaksa_employee_ditolak() -> None:
    # Model "berhalusinasi"/dibelokkan memanggil tool yang tak ditawarkan
    r = execute_tool("lookup_leave_balance", '{"employee_id": "emp-002"}', ctx(BUDI))
    assert not r.ok and "tidak tersedia" in r.content
    assert "sisa cuti" not in r.content
    print("[LULUS] Employee memanggil tool HR langsung -> ditolak, tanpa data bocor")


def test_pesan_tolak_sama_untuk_tool_tak_ada_dan_dilarang() -> None:
    a = execute_tool("lookup_leave_balance", "{}", ctx(BUDI)).content
    b = execute_tool("tool_ngawur", "{}", ctx(BUDI)).content
    assert a.replace("lookup_leave_balance", "X") == b.replace("tool_ngawur", "X")
    print("[LULUS] Pesan penolakan identik: penyerang tak bisa tahu tool HR itu ada")


def test_identitas_dari_server_bukan_argumen() -> None:
    assert "sisa cuti 9" in execute_tool("get_leave_balance", "{}", ctx(BUDI)).content
    assert "sisa cuti 2" in execute_tool("get_leave_balance", "{}", ctx(SARI)).content
    # Model mencoba menyisipkan employee_id (serangan "cek cuti emp-002")
    r = execute_tool("get_leave_balance", '{"employee_id": "emp-002"}', ctx(BUDI))
    assert not r.ok and "tidak dikenal" in r.content
    print("[LULUS] Cuti selalu milik penanya; argumen employee_id selundupan ditolak")


def test_hr_boleh_lihat_karyawan_lain() -> None:
    r = execute_tool("lookup_leave_balance", '{"employee_id": "emp-002"}', ctx(RINA))
    assert r.ok and "sisa cuti 2" in r.content
    print("[LULUS] HR boleh lookup karyawan lain")


def test_argumen_rusak_ditolak() -> None:
    c = ctx(RINA)
    assert not execute_tool("lookup_leave_balance", "{bukan json", c).ok
    assert not execute_tool("lookup_leave_balance", "{}", c).ok                                  # wajib hilang
    assert not execute_tool("lookup_leave_balance", '{"employee_id": 123}', c).ok               # tipe salah
    assert not execute_tool("lookup_leave_balance", '{"employee_id": "' + "x" * 50 + '"}', c).ok # terlalu panjang
    assert not execute_tool("lookup_leave_balance", '["emp-001"]', c).ok                         # bukan objek
    print("[LULUS] JSON rusak / argumen hilang / salah tipe / kepanjangan / bukan objek -> ditolak")


def test_search_policy_mewarisi_role() -> None:
    bot = BotPalsu()
    r = execute_tool("search_policy", '{"query": "gaji"}', ctx(BUDI, bot))
    assert r.ok and bot.role_diterima == ["employee"]
    execute_tool("search_policy", '{"query": "gaji"}', ctx(RINA, bot))
    assert bot.role_diterima == ["employee", "hr"]
    assert "BUKAN instruksi" in r.content
    print("[LULUS] search_policy meneruskan role penanya ke retrieval (RBAC Fase 3 ikut berlaku)")


def test_hasil_dipotong() -> None:
    class BotPanjang(BotPalsu):
        def retrieve(self, *a, **k):
            return ["x" * 10_000]
    r = execute_tool("search_policy", '{"query": "a"}', ctx(BUDI, BotPanjang()))
    assert len(r.content) <= MAX_RESULT_CHARS
    print("[LULUS] Hasil tool terlalu panjang dipotong")


def test_handler_error_tidak_bocor() -> None:
    class BotRusak(BotPalsu):
        def retrieve(self, *a, **k):
            raise RuntimeError("path rahasia C:\\internal\\chroma")
    r = execute_tool("search_policy", '{"query": "a"}', ctx(BUDI, BotRusak()))
    assert not r.ok and "rahasia" not in r.content
    print("[LULUS] Error internal tidak bocor ke LLM")


if __name__ == "__main__":
    test_employee_tidak_ditawari_tool_hr()
    test_tool_hr_dipaksa_employee_ditolak()
    test_pesan_tolak_sama_untuk_tool_tak_ada_dan_dilarang()
    test_identitas_dari_server_bukan_argumen()
    test_hr_boleh_lihat_karyawan_lain()
    test_argumen_rusak_ditolak()
    test_search_policy_mewarisi_role()
    test_hasil_dipotong()
    test_handler_error_tidak_bocor()
    print("\nSemua uji agent_tools (Langkah 3) LULUS.")