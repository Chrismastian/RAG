# Changelog

Setiap fase pengembangan sistem ini dicatat sebagai satu entri di sini, sesuai `roadmap-ai-automation-rag-security.md`. Setelah tiap entri di-push, buat git tag yang sesuai (lihat format di bawah) supaya histori progres skill terlihat jelas di repo.

## [v0.1-rag-foundation] — Fase 1: Fondasi RAG — 2026-11-13

### Ditambahkan
- `src/embed_index.py` — chunking dokumen (per paragraf, 180 kata/chunk, overlap 40 kata) + embedding lokal (`sentence-transformers`, model `paraphrase-multilingual-MiniLM-L12-v2`) + indexing ke ChromaDB persistent
- `src/llm_fallback.py` — modul reusable pemanggil LLM dengan fallback otomatis: Groq → Cerebras → OpenRouter → Mistral. Akan dipakai ulang tanpa modifikasi struktural di fase-fase berikutnya.
- `src/rag_chat.py` — chatbot CLI: sanitasi input dasar, retrieval top-k dari ChromaDB, prompt grounding (jawab hanya dari konteks dokumen)
- `src/security_test.py` — 3 skenario uji prompt injection (instruction override, role manipulation, system prompt extraction), reuse `RagChatBot` dari `rag_chat.py`
- Dokumen sumber: kebijakan kerja jarak jauh & fasilitas karyawan (`data/kebijakan_kerja_jarak_jauh.md`)

### Skill yang dikuasai di fase ini
- **RAG:** chunking dengan overlap, embedding lokal, retrieval top-k berbasis cosine similarity, prompt grounding untuk anti-halusinasi
- **Security:** API key via environment variable (bukan hardcode), sanitasi input dasar, uji prompt injection manual, memahami batasan heuristik keyword-matching

### Diperbaiki
- Model default Groq awalnya `llama-3.3-70b-versatile` — ternyata sudah di-deprecate provider (shutdown 16 Agustus 2026), diganti ke `openai/gpt-oss-120b`
- Model default Cerebras awalnya `llama-3.3-70b` — ternyata Llama sudah dihapus total dari lineup Cerebras, diganti ke `qwen-3.8-27b`

### Catatan
- Hasil uji prompt injection lengkap: `logs/security_test_results.json` (di-gitignore secara default — commit manual kalau ingin dijadikan bukti portofolio)
- Heuristik otomatis di `security_test.py` sempat salah menandai skenario role-manipulation sebagai "kemungkinan bypass" padahal bot menjawab dengan benar — lihat README bagian Security Considerations untuk detail

---

<!--
Template entri untuk fase berikutnya:

## [v0.X-nama-fase] — Fase X: <Nama Fase> — <tanggal>

### Ditambahkan
- file baru apa, untuk apa

### Dimodifikasi
- file lama apa yang diperluas, bagian mana

### Skill yang dikuasai di fase ini
-

### Catatan
-
-->
