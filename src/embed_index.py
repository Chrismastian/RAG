"""
embed_index.py
---------------
Pipeline indexing untuk RAG FAQ Bot:
  1. Baca dokumen sumber (Markdown/teks)
  2. Pecah jadi chunk dengan overlap
  3. Embed tiap chunk secara LOKAL via sentence-transformers (tidak ada
     data yang dikirim keluar di tahap ini)
  4. Simpan ke ChromaDB (in-process, persisten di folder ./chroma_db)

Jalankan: python src/embed_index.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --- Konfigurasi ---
DATA_PATH = Path(__file__).parent.parent / "data" / "kebijakan_kerja_jarak_jauh.md"
CHROMA_DIR = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "faq_kebijakan_kerja"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # mendukung Bahasa Indonesia, jalan di CPU
CHUNK_SIZE_WORDS = 180
CHUNK_OVERLAP_WORDS = 40


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


def build_index() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dokumen sumber tidak ditemukan: {DATA_PATH}")

    print(f"[1/4] Membaca dokumen: {DATA_PATH.name}")
    text = DATA_PATH.read_text(encoding="utf-8")

    print(f"[2/4] Chunking (target ~{CHUNK_SIZE_WORDS} kata/chunk, overlap {CHUNK_OVERLAP_WORDS} kata)...")
    chunks = chunk_text(text)
    print(f"      -> {len(chunks)} chunk dihasilkan")

    print(f"[3/4] Memuat model embedding lokal: {EMBEDDING_MODEL} (sekali unduh, lalu jalan offline)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=True, convert_to_numpy=True)

    print(f"[4/4] Menyimpan ke ChromaDB (persisten di {CHROMA_DIR})...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Hapus koleksi lama kalau ada, supaya index selalu sinkron dengan dokumen terbaru
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"source_file": DATA_PATH.name, "embedding_model": EMBEDDING_MODEL},
    )

    collection.add(
        ids=[f"chunk-{i}" for i in range(len(chunks))],
        embeddings=embeddings.tolist(),
        documents=chunks,
        metadatas=[{"source_file": DATA_PATH.name, "chunk_index": i} for i in range(len(chunks))],
    )

    print(f"\nSelesai. {len(chunks)} chunk ter-index dalam koleksi '{COLLECTION_NAME}'.")
    print("Jalankan 'python src/rag_chat.py' untuk mulai tanya jawab.")


if __name__ == "__main__":
    build_index()
