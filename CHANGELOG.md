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

## [v0.2-webhook-agent] — Fase 2: Secure Webhook Agent — 2026-11-21

### Ditambahkan
- `src/webhook_server.py` — server FastAPI dengan endpoint `POST /ask` (dilindungi token + rate limit) dan `GET /health` (tanpa token). Membungkus `RagChatBot` dari Fase 1, bukan menulis ulang logika RAG.
- `src/test_webhook_security.py` — uji lapisan HTTP (token salah/hilang → 401, rate limit terlampaui → 429) pakai FastAPI TestClient, tidak perlu server benar-benar berjalan

### Dimodifikasi
- `requirements.txt` — tambah `fastapi`, `uvicorn[standard]`
- `.env.example` — tambah `WEBHOOK_API_TOKEN`
- `README.md` — tambah diagram arsitektur Fase 2, baris Security Considerations untuk token validation & rate limiting, langkah menjalankan webhook + setup n8n
- **Tidak diubah sama sekali:** `rag_chat.py`, `llm_fallback.py`, `embed_index.py`, `security_test.py` — bukti nyata prinsip reuse dari Fase 1

### Skill yang dikuasai di fase ini
- **Automation:** webhook trigger & HTTP Request node di n8n, expose server lokal ke internet lewat ngrok (karena n8n Cloud tidak bisa menjangkau `localhost`)
- **Security:** validasi token tahan *timing attack* (`secrets.compare_digest()` vs `==`), rate limiting sliding-window in-memory, menguji lapisan HTTP terpisah dari lapisan RAG

### Catatan
- Rate limit saat ini berlaku global (1 token valid, belum per-user) — jadi relevan dipersempit lagi setelah Fase 3 punya konsep role/multi-user
- `bot = RagChatBot()` dibuat sekali saat proses server start (bukan per-request) — artinya `embed_index.py` **wajib** sudah dijalankan dulu sebelum `webhook_server.py` dinyalakan, kalau belum, server gagal start dengan `RuntimeError` yang jelas

---

## v0.3-multi-source-rbac — Fase 3: Multi-Source RAG dengan Role-Based Access

**Ditambahkan**
- `src/access_control.py`: sumber tunggal aturan akses (role penanya -> tag dokumen yang boleh dilihat)
- `data/sources_manifest.json`: pelabelan tiap dokumen (`all` / `hr_only`)
- `data/info_gaji_karyawan.md`: dokumen sensitif fiktif untuk simulasi
- 4 skenario uji data leakage lintas-role di `security_test.py`

**Diubah**
- `embed_index.py`: indexing multi-dokumen berbasis manifest, metadata `role` per chunk, file tak berlabel dilewati (fail-closed)
- `rag_chat.py`: `retrieve()` dan `answer()` menerima `role`; filter `where` diterapkan di ChromaDB

**Tidak diubah:** `llm_fallback.py`, inti `webhook_server.py`

**Skill:** metadata filtering (RAG), least privilege & fail-closed (security)
**Risiko yang ditangani:** data leakage lintas-role. Data sensitif tidak pernah masuk prompt LLM untuk role yang tidak berhak.
**Batasan yang diakui:** role masih berupa parameter tepercaya; belum ada autentikasi per-pengguna. Webhook belum meneruskan role (default `employee`).

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
