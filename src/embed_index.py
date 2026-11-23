"""
embed_index.py  (Fase 3: multi-dokumen + metadata role)
-------------------------------------------------------
Pipeline indexing:
  1. Baca data/sources_manifest.json (daftar dokumen + tag role masing-masing)
  2. Untuk tiap dokumen terdaftar: pecah jadi chunk dengan overlap
  3. Embed semua chunk secara LOKAL via sentence-transformers
  4. Simpan ke ChromaDB, tiap chunk membawa metadata {"role": <tag dokumen>}

Dokumen di folder data/ yang TIDAK terdaftar di manifest sengaja dilewati
(fail-closed): file tanpa label tidak boleh masuk ke sistem.

Jalankan: python src/embed_index.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from access_control import ROLE_VISIBILITY

# --- Konfigurasi ---
DATA_DIR = Path(__file__).parent.parent / "data"
MANIFEST_PATH = DATA_DIR / "sources_manifest.json"
CHROMA_DIR = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "faq_kebijakan_kerja"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # mendukung Bahasa Indonesia, jalan di CPU
CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 40

# Semua tag dokumen yang sah = gabungan tag yang muncul di ROLE_VISIBILITY.
# Tag di manifest yang tidak ada di sini = salah ketik -> kita tolak, bukan diam-diam diterima.
VALID_TAGS = {tag for tags in ROLE_VISIBILITY.values() for tag in tags}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """
    Chunking sederhana berbasis jumlah kata dengan overlap, tapi tidak
    memotong di tengah paragraf kalau paragraf itu lebih pendek dari
    chunk_size — supaya tiap chunk tetap punya konteks yang utuh
    (penting untuk dokumen kebijakan yang terstruktur per section).
    """
    # Pisah per paragraf dulu (baris kosong sebagai pemisah)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()

        # Kalau menambah paragraf ini akan melebihi batas, tutup chunk saat ini dulu
        if current_words and len(current_words) + len(para_words) > chunk_size:
            chunks.append(" ".join(current_words))
            # overlap: ambil sisa kata terakhir dari chunk sebelumnya
            current_words = current_words[-overlap:] if overlap else []

        current_words.extend(para_words)

        # Kalau satu paragraf saja sudah melebihi batas, potong langsung
        while len(current_words) > chunk_size:
            chunks.append(" ".join(current_words[:chunk_size]))
            current_words = current_words[chunk_size - overlap:]

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def load_manifest() -> dict[str, str]:
    """Baca manifest -> {nama_file: tag_role}. Tag tidak dikenal = error keras."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest tidak ditemukan: {MANIFEST_PATH}")

    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest: dict[str, str] = {}
    for filename, info in raw.items():
        tag = info.get("role") if isinstance(info, dict) else None
        if tag not in VALID_TAGS:
            raise ValueError(
                f"Tag role '{tag}' pada '{filename}' tidak dikenal. "
                f"Tag yang valid (dari access_control.py): {sorted(VALID_TAGS)}"
            )
        manifest[filename] = tag
    return manifest


def build_index() -> None:
    manifest = load_manifest()

    print(f"[1/3] Membaca & chunking {len(manifest)} dokumen sesuai manifest...")
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for filename, tag in manifest.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Dokumen di manifest tidak ditemukan: {path}")

        chunks = chunk_text(path.read_text(encoding="utf-8"))
        print(f"      - {filename}  [role={tag}]  -> {len(chunks)} chunk")

        for i, chunk in enumerate(chunks):
            ids.append(f"{path.stem}-chunk-{i}")   # id unik lintas dokumen
            documents.append(chunk)
            metadatas.append({"source_file": filename, "chunk_index": i, "role": tag})

    # Fail-closed: file .md di data/ yang tidak berlabel TIDAK di-index
    for p in sorted(DATA_DIR.glob("*.md")):
        if p.name not in manifest:
            print(f"      [PERINGATAN] {p.name} tidak ada di manifest -> DILEWATI (tidak di-index)")

    print(f"[2/3] Memuat model embedding lokal: {EMBEDDING_MODEL} (sekali unduh, lalu jalan offline)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)

    print(f"[3/3] Menyimpan ke ChromaDB (persisten di {CHROMA_DIR})...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Hapus koleksi lama, supaya index selalu sinkron dengan manifest terbaru
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"source_files": ", ".join(manifest), "embedding_model": EMBEDDING_MODEL},
    )

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas,
    )

    print(f"\nSelesai. {len(documents)} chunk dari {len(manifest)} dokumen ter-index dalam koleksi '{COLLECTION_NAME}'.")
    print("Jalankan 'python src/rag_chat.py' untuk mulai tanya jawab.")


if __name__ == "__main__":
    build_index()