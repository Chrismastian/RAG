"""
access_control.py
-----------------
Satu-satunya sumber kebenaran soal "siapa boleh melihat dokumen apa".
Semua modul lain (embed_index, rag_chat, nanti webhook & agent) harus
bertanya ke sini, bukan menulis aturan akses sendiri.

Dua konsep yang JANGAN tertukar:
  - TAG DOKUMEN  : label pada dokumen ("all", "hr_only") -- dari sources_manifest.json
  - ROLE PENANYA : siapa yang bertanya ("employee", "hr")

ROLE_VISIBILITY menerjemahkan role penanya -> tag dokumen yang boleh dibaca.

Jalankan untuk demo: python src/access_control.py
"""

from __future__ import annotations

# Prinsip least privilege: kalau role tidak diketahui / tidak diberikan,
# jatuh ke role PALING RENDAH, bukan yang paling tinggi.
DEFAULT_ROLE = "employee"

ROLE_VISIBILITY: dict[str, list[str]] = {
    "employee": ["all"],
    "hr": ["all", "hr_only"],
}


def normalize_role(role: str | None) -> str:
    """Role kosong atau tidak dikenal -> DEFAULT_ROLE (paling rendah)."""
    if role is None:
        return DEFAULT_ROLE
    cleaned = role.strip().lower()
    return cleaned if cleaned in ROLE_VISIBILITY else DEFAULT_ROLE


def get_visible_roles(role: str | None) -> list[str]:
    """Daftar tag dokumen yang boleh dilihat oleh role ini."""
    return list(ROLE_VISIBILITY[normalize_role(role)])


if __name__ == "__main__":
    for r in ["employee", "hr", None, "admin-palsu", "  HR  "]:
        print(f"role={r!r} -> boleh melihat tag: {get_visible_roles(r)}")