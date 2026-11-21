# Roadmap Portofolio: AI Automation + Agent/RAG Developer (Security-First)

Fokus: membangun **satu sistem AI yang terus bertumbuh** — cepat (automation), cerdas (agent/RAG), dan aman (security) — bukan tujuh proyek terpisah yang tidak saling berhubungan.

> **Catatan revisi:** Versi roadmap ini mengganti pendekatan "7 repo terpisah" dengan **1 repo yang berkembang bertahap**. Alasannya: skill yang saling menumpuk (compounding) di satu sistem nyata lebih kuat untuk portofolio dan lebih dekat dengan cara sistem production sungguhan dibangun, dibanding 7 proyek kecil yang tidak saling terhubung. Histori commit/tag Git di repo ini justru jadi bukti progres skill yang bisa ditunjukkan langsung ke klien atau recruiter.

---

## Status Proyek Saat Ini

> Bagian ini sengaja ditaruh di paling atas supaya kalau percakapan ini dimulai ulang dari chat baru (misal di sesi lain), cukup lampirkan file ini untuk memberi konteks penuh tanpa perlu mengulang histori chat.

**Nama folder/repo:** `project-01-rag-faq-bot` (nama masih bisa diganti kapan saja lewat GitHub Settings, belum diputuskan final)

**Fase 1 — Fondasi RAG:** ✅ Selesai dibangun, diuji (3 skenario prompt injection, hasil tercatat), dan pemahamannya sudah diverifikasi lewat kuis mandiri (8 soal, semua konsep inti terjawab).

**Fase 2 — Secure Webhook Agent:** ✅ Kode sudah dibangun lengkap (`webhook_server.py` + `test_webhook_security.py`), logikanya sudah diverifikasi lewat uji terisolasi. **Belum** dijalankan end-to-end oleh user dengan n8n/ngrok sungguhan — itu langkah praktik yang masih perlu dilakukan sebelum fase ini benar-benar ditutup (push + git tag `v0.2-webhook-agent`).

**Fase 3–7:** Belum dimulai.

**File yang sudah ada di repo saat ini:**
```
project-01-rag-faq-bot/
├── README.md, CHANGELOG.md, roadmap-ai-automation-rag-security.md (file ini)
├── .env.example, .gitignore, requirements.txt
├── data/kebijakan_kerja_jarak_jauh.md
└── src/
    ├── embed_index.py, llm_fallback.py, rag_chat.py, security_test.py   (Fase 1)
    └── webhook_server.py, test_webhook_security.py                      (Fase 2)
```

**Keputusan teknis penting yang sudah diambil** (supaya tidak perlu diulang kalau ditanyakan lagi):
- Model LLM default: Groq → `openai/gpt-oss-120b`, Cerebras → `qwen-3.8-27b` (keduanya sudah diverifikasi ke dokumentasi resmi masing-masing per November 2026, menggantikan model lama yang ternyata sudah deprecated)
- Token webhook divalidasi dengan `secrets.compare_digest()`, bukan `==` (tahan timing attack)
- Rate limit webhook: in-memory sliding window, 10 request/60 detik, per-token (saat ini praktis global karena baru 1 token)
- **Belum pernah benar-benar di-`git push`** ke GitHub oleh user — repo masih lokal

**Yang belum diputuskan / masih jadi pertanyaan terbuka:**
- Nama final repo (tetap `project-01-rag-faq-bot` atau rename)
- Kapan mulai setup akun n8n Cloud + ngrok untuk uji Fase 2 end-to-end

---

## Setup Awal (Tanpa Docker — Cocok untuk Laptop Low-End)

Docker memang berat untuk laptop spek rendah. Kabar baiknya: untuk stack yang kita pakai, Docker **tidak wajib**. Setup ini dipakai dari Fase 1 sampai Fase 7 — tidak berubah sepanjang roadmap.

**Untuk n8n (automation):**
- **Opsi terbaik: n8n Cloud (free tier)** — jalan di server mereka, laptop kamu tidak menanggung beban apa pun, cukup browser. Paling disarankan untuk laptop low-end.
- **Alternatif lokal tanpa Docker:** `npx n8n` (jalankan langsung lewat Node.js, tanpa image container) — jauh lebih ringan dari Docker meski tetap memakai resource laptop saat dijalankan.
- Kalau suatu saat tetap butuh container tapi Docker terlalu berat: **Podman** adalah alternatif yang lebih ringan dan kompatibel dengan perintah Docker, tapi untuk tahap ini belum perlu dipikirkan.

**Untuk RAG/vector database:**
- **ChromaDB berjalan in-process** lewat `pip install chromadb` — tidak butuh server terpisah apalagi Docker.
- **Embedding: `sentence-transformers` (lokal, gratis)** — model `paraphrase-multilingual-MiniLM-L12-v2` jalan di CPU, mendukung Bahasa Indonesia, dan tidak perlu API key sama sekali untuk tahap retrieval. Ini juga berarti data tidak pernah dikirim ke pihak ketiga saat proses embedding.
- Python virtual environment (`venv`) cukup untuk semua eksperimen RAG/agent di tahap awal.

**Untuk LLM (generation/jawaban) — gratis, dengan strategi rotasi:**
Embedding bisa 100% lokal, tapi tahap "menjawab" tetap butuh LLM API. Supaya seluruh roadmap bisa dikerjakan tanpa biaya, pakai kombinasi beberapa provider gratis dan rotasi otomatis saat satu provider kena limit:

| Provider | Model Gratis (per pengecekan terakhir) | Limit (perkiraan, cek ulang berkala) |
|---|---|---|
| **Groq** | `openai/gpt-oss-120b` | ~30 req/menit, ~1.000 req/hari |
| **Cerebras** | `qwen-3.8-27b` | ~300 req/menit (free trial) |
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct:free` + 20+ model gratis lain | ~20 req/menit, 50–1.000 req/hari |
| **Mistral** (La Plateforme) | `mistral-small-latest` | Paket "Experiment" gratis — catatan: request boleh dipakai Mistral untuk training, jangan pakai untuk data rahasia |
| **Google AI Studio (Gemini)** | Gemini Flash-Lite | ~500 req/hari (cadangan — kuota Gemini sempat dipotong signifikan) |

> ⚠️ **Pelajaran dari pengalaman nyata:** provider LLM gratis **rutin mengubah atau men-deprecate nama model**. Begitu satu provider tiba-tiba error (termasuk error yang tidak jelas seperti 404), langkah pertama selalu cek halaman deprecations/model resmi provider itu — jangan asumsikan kode yang salah. Ini akan terjadi lagi di masa depan, jadi ini masuk skill yang perlu dikuasai, bukan cuma insiden sekali jalan.

Groq, Cerebras, OpenRouter, dan Mistral semuanya punya endpoint kompatibel format OpenAI, jadi bisa dipakai bergantian lewat satu fungsi kode dengan logika fallback (coba provider A → kalau kena rate limit atau model deprecated, otomatis pindah ke provider B, dst). Modul ini (`src/llm_fallback.py`) dibangun sekali di Fase 1 dan dipakai ulang **tanpa diubah strukturnya** di seluruh fase berikutnya — ini contoh nyata compounding: satu komponen dibangun kuat sekali, lalu dipakai berkali-kali.

**Kesimpulan:** Kamu bisa mengerjakan seluruh roadmap di bawah ini tanpa Docker **dan** tanpa biaya API — pakai n8n Cloud + Python venv + ChromaDB lokal + sentence-transformers (embedding) + rotasi LLM API gratis (Groq/Cerebras/OpenRouter/Mistral).

---

## Struktur Repo Tunggal (Bukan 7 Repo Terpisah)

```
github.com/username/<nama-repo-tunggal>/
├── README.md               ← diupdate tiap fase, selalu mencerminkan kemampuan TERKINI sistem
├── CHANGELOG.md            ← baru: log tiap fase (apa ditambahkan, skill apa, risiko apa)
├── .env.example
├── .gitignore
├── requirements.txt
├── data/                   ← dokumen sumber, bertambah mulai Fase 3 (multi-source)
├── src/
│   ├── llm_fallback.py     ← Fase 1 — dipakai ulang di semua fase berikutnya, tidak ditulis ulang
│   ├── embed_index.py      ← Fase 1 — diperluas di Fase 3 (multi-dokumen + metadata role)
│   ├── rag_chat.py         ← Fase 1 — jadi "otak" yang di-reuse oleh webhook (Fase 2) dan agent (Fase 4)
│   ├── security_test.py    ← Fase 1 — daftar skenario ujinya terus bertambah tiap fase
│   ├── webhook_server.py   ← ditambahkan di Fase 2
│   ├── access_control.py  ← ditambahkan di Fase 3
│   ├── agent_tools.py      ← ditambahkan di Fase 4
│   └── multi_agent.py      ← ditambahkan di Fase 5
├── logs/
└── docs/
    └── security-audit-report.md   ← ditambahkan di Fase 6
```

**Soal nama repo:** kalau repo `project-01-rag-faq-bot` sudah lanjut dipakai, tidak masalah tetap dipakai sebagai nama — atau bisa di-rename kapan saja lewat GitHub Settings → Repository name (GitHub otomatis redirect URL lama, jadi link yang sudah dibagikan tidak rusak). Yang penting isi README-nya selalu menjelaskan sistem secara utuh sesuai fase terkini, bukan hanya "RAG FAQ Bot".

**Git tag per fase** — ini pengganti "7 repo terpisah" sebagai bukti progres. Setelah tiap fase selesai dan di-push, buat tag:
```bash
git tag -a v0.1-rag-foundation -m "Fase 1: Fondasi RAG dengan grounding + fallback LLM"
git push origin v0.1-rag-foundation
```
Nanti histori tag ini (`v0.1-rag-foundation`, `v0.2-webhook-agent`, dst) bisa langsung ditunjukkan ke klien/recruiter sebagai bukti "begini cara saya membangun sistem AI dari fondasi sampai production-ready", yang jauh lebih meyakinkan dibanding 7 repo kecil yang tidak nyambung satu sama lain.

Setiap fase **wajib** meng-update `README.md` (bagian Arsitektur dan Security Considerations harus mencerminkan kemampuan terbaru, bukan dibiarkan basi) dan menambah satu entri baru di `CHANGELOG.md`.

---

## Fase 1 — Fondasi RAG ✅ (Sudah Selesai)
**Tujuan:** Fondasi RAG — sistem menjawab pertanyaan dari satu dokumen.

- **Skill RAG:** chunking dokumen, embedding lokal (sentence-transformers), retrieval, prompt grounding
- **Skill Security:** API key di environment variable, sanitasi input dasar, 3 uji prompt injection dasar
- **File inti yang dihasilkan:** `src/embed_index.py`, `src/llm_fallback.py`, `src/rag_chat.py`, `src/security_test.py`
- **Status:** kode sudah dibangun, diuji (termasuk 3 skenario prompt injection — hasil tercatat di README & `CHANGELOG.md`), dan pemahaman sudah diverifikasi lewat kuis mandiri. Siap dipakai sebagai fondasi Fase 2.

## Fase 2 — + Secure Webhook Agent
**Tujuan:** Menghubungkan automation (n8n) ke bot RAG yang **sudah ada**, bukan membangun bot baru. `RagChatBot` dari Fase 1 cuma dibungkus endpoint HTTP — logika RAG-nya sendiri tidak disentuh.

### Arsitektur Fase 2

```
┌──────────────┐      HTTPS POST       ┌───────────────────────┐
│  n8n Cloud   │  (header: token)      │  webhook_server.py     │
│  (webhook    │──────────────────────▶│  1. validasi token     │
│   trigger)   │                       │  2. cek rate limit     │
│              │◀──────────────────────│  3. panggil            │
└──────────────┘      JSON response    │     RagChatBot.answer()│──┐
                                        └───────────────────────┘  │
                                                                    ▼
                                                         (logika Fase 1: sanitasi →
                                                          retrieval → grounding →
                                                          llm_fallback, TIDAK berubah)
```

### File yang Ditambahkan/Diubah
- **Baru:** `src/webhook_server.py` — server HTTP kecil (FastAPI), satu endpoint `POST /ask`
- **Diubah:** `.env.example` — tambah `WEBHOOK_API_TOKEN=` (token yang dipakai n8n untuk otentikasi)
- **Diubah:** `requirements.txt` — tambah `fastapi` dan `uvicorn`
- **Tidak diubah sama sekali:** `rag_chat.py`, `llm_fallback.py`, `embed_index.py` — ini pembuktian nyata prinsip reuse

### Rincian Skill

**Automation (n8n):**
1. Daftar n8n Cloud (gratis), buat workflow baru
2. Tambah node **Webhook** (trigger) — catat URL yang dihasilkan
3. Tambah node **HTTP Request** yang memanggil `webhook_server.py` kamu, kirim header `Authorization: Bearer <WEBHOOK_API_TOKEN>`
4. **Kendala yang wajib diantisipasi:** n8n Cloud berjalan di server mereka, jadi **tidak bisa menjangkau `localhost` di laptop kamu**. Dua opsi:
   - **Untuk belajar/testing cepat:** `ngrok http 8000` (gratis, instan) — bikin URL publik sementara yang meneruskan ke server lokal
   - **Untuk deliverable yang lebih tahan lama:** deploy `webhook_server.py` ke free tier Render.com atau Railway.app (keduanya punya paket gratis untuk API kecil)

**RAG (reuse, bukan tulis ulang):**
```python
# src/webhook_server.py (kerangka)
from fastapi import FastAPI, Header, HTTPException
from rag_chat import RagChatBot   # import langsung, tidak ada duplikasi logika

app = FastAPI()
bot = RagChatBot()   # dibuat sekali saat server start, dipakai ulang tiap request
```

**Security — dua konsep baru yang perlu dikuasai di fase ini:**
- **Token validation yang aman dari timing attack:** jangan bandingkan token dengan `token == expected_token` biasa (operator `==` Python bisa dieksploitasi lewat *timing attack* karena berhenti di karakter pertama yang beda). Pakai `secrets.compare_digest(token, expected_token)` yang waktu eksekusinya konstan tidak peduli di mana perbedaannya.
- **Rate limiting sederhana:** dictionary in-memory `{token: [timestamp_request]}`, tolak kalau jumlah request dalam N detik terakhir melebihi batas. **Batasan yang jujur diakui (gaya README Fase 1):** in-memory berarti counter reset kalau server restart, dan tidak sinkron kalau nanti dijalankan multi-instance — cukup untuk portofolio single-instance, bukan untuk production skala besar (itu butuh Redis, di luar cakupan fase ini).

### Uji Keamanan Tambahan di Fase Ini
Perluas `security_test.py` dengan 2 skenario baru khusus webhook:
1. Request tanpa token / token salah → harus ditolak dengan HTTP 401, bukan diproses
2. Request melebihi rate limit → harus ditolak dengan HTTP 429

### Deliverable
Workflow n8n yang menerima pertanyaan via webhook, diproses oleh `RagChatBot` Fase 1 yang **sama persis** (bisa dibuktikan dengan diff: `rag_chat.py` tidak berubah), dibalas dengan autentikasi token — plus entri baru di `CHANGELOG.md` (`v0.2-webhook-agent`) dan README yang diupdate.

## Fase 3 — + Multi-Source RAG dengan Role-Based Access
**Tujuan:** Memperluas retrieval dari satu dokumen jadi banyak dokumen dengan kontrol akses bertingkat — modifikasi langsung ke `embed_index.py` dan `rag_chat.py` yang sudah ada, bukan sistem baru.

- **Skill RAG:** metadata filtering, retrieval dari banyak dokumen/sumber, re-ranking hasil
- **Skill Security:** `src/access_control.py` memastikan agent hanya mengambil data yang diizinkan untuk "role" tertentu (misal: data HR tidak bocor ke user biasa) — simulasi masalah data leakage nyata di perusahaan
- **Tools:** ChromaDB dengan metadata (sudah dipakai sejak Fase 1), LangChain retriever filtering
- **Deliverable:** Sistem yang sama dari Fase 1–2, sekarang bisa menjawab dari multi-dokumen dengan role-based filtering, dibuktikan lewat 2 role user berbeda

## Fase 4 — + AI Agent dengan Tool/Function Calling
**Tujuan:** Bot yang sudah bisa menjawab sekarang bisa **bertindak** — dibangun di atas `llm_fallback.py` Fase 1 (ditambah dukungan tool-calling, bukan ditulis ulang dari nol).

- **Skill Automation + RAG gabung:** agent memanggil tools (kirim email, cek database, buat entry kalender) lewat `src/agent_tools.py`
- **Skill Security:** sandboxing eksekusi tool (agent tidak bisa menjalankan aksi di luar daftar tools yang diizinkan), **approval gate** untuk aksi berisiko
- **Tools:** provider gratis yang mendukung tool calling (Groq/Mistral), n8n sebagai eksekutor aksi
- **Deliverable:** Agent yang sama, sekarang menangani 1 alur kerja nyata dengan log setiap aksi yang diambil

## Fase 5 — + Multi-Agent Workflow
**Tujuan:** Orchestration — beberapa agent bekerja sama, dibangun di atas `agent_tools.py` Fase 4.

- **Skill Automation + RAG:** agent "peneliti" mengambil data (reuse retrieval Fase 1/3), agent "penulis" menyusun output, agent "reviewer" mengecek kualitas — di `src/multi_agent.py`
- **Skill Security:** trust boundary antar agent (reviewer tidak boleh otomatis percaya output penulis tanpa validasi), audit trail lengkap
- **Tools:** LangGraph / CrewAI, logging terstruktur
- **Deliverable:** Sistem yang sama + orchestration 3-agent, terdokumentasi dengan diagram alur dan log audit

## Fase 6 — Red-Team Security Audit (Diferensiasi Utama)
**Tujuan:** Mengaudit **sistem nyata yang sudah dibangun di Fase 1–5**, bukan sistem simulasi terpisah — ini yang membedakan dari 95% automation freelancer lain.

- **Skill Security murni:** uji sistematis terhadap checklist **OWASP Top 10 for LLM Applications** (prompt injection, insecure output handling, data leakage, excessive agency, dll) terhadap keseluruhan sistem gabungan Fase 1–5
- **Tools:** garak (LLM vulnerability scanner) atau pengujian manual terstruktur, memperluas `security_test.py` yang sudah ada sejak Fase 1
- **Deliverable:** `docs/security-audit-report.md` — format mirip laporan konsultan profesional terhadap sistem yang benar-benar berjalan, bukan sistem mainan. Ini bisa langsung jadi **sample deliverable** untuk ditawarkan ke klien sungguhan.

## Fase 7 — Capstone: Narasi "AI Employee" End-to-End
**Tujuan:** Bukan membangun fitur baru — merangkum seluruh evolusi sistem (Fase 1–6) jadi satu studi kasus bisnis utuh.

- Update final `README.md` + `CHANGELOG.md` lengkap, diagram arsitektur final yang menunjukkan seluruh kemampuan terakumulasi
- Narasi bisnis: "masalah klien X → solusi Y (yang berkembang bertahap) → hasil Z", didukung histori tag Git sebagai bukti proses
- **Deliverable:** 1 repo matang dengan histori commit/tag yang bercerita, dipakai sebagai pitch utama ke calon klien freelance

---

## Cadence yang Disarankan

- 1 fase per 1–2 minggu untuk Fase 1–4 (fondasi, lebih cepat)
- 2–3 minggu untuk Fase 5–7 (lebih kompleks)
- Total: ±3–4 bulan untuk satu sistem matang, sambil mulai submit proposal freelance kecil begitu Fase 2 selesai
- Tiap fase = iterasi baru di repo yang **sama** (branch lalu merge ke `main`, atau langsung di `main` kalau kerja solo), ditutup dengan satu git tag — bukan repo baru
