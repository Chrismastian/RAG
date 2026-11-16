# Roadmap Portofolio: AI Automation + Agent/RAG Developer (Security-First)

Fokus: membangun **satu sistem AI yang terus bertumbuh** — cepat (automation), cerdas (agent/RAG), dan aman (security) — bukan tujuh proyek terpisah yang tidak saling berhubungan.

> **Catatan revisi:** Versi roadmap ini mengganti pendekatan "7 repo terpisah" dengan **1 repo yang berkembang bertahap**. Alasannya: skill yang saling menumpuk (compounding) di satu sistem nyata lebih kuat untuk portofolio dan lebih dekat dengan cara sistem production sungguhan dibangun, dibanding 7 proyek kecil yang tidak saling terhubung. Histori commit/tag Git di repo ini justru jadi bukti progres skill yang bisa ditunjukkan langsung ke klien atau recruiter.

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
- **Status:** sudah dibangun, diuji, dan siap/sudah di-push ke GitHub.

## Fase 2 — + Secure Webhook Agent
**Tujuan:** Menghubungkan automation (n8n) ke bot RAG yang **sudah ada**, bukan membangun bot baru.

- **Skill Automation:** webhook trigger, routing, response handling di n8n
- **Skill RAG:** `src/webhook_server.py` **meng-import langsung** `RagChatBot` dari `rag_chat.py` Fase 1 — tidak ada logika RAG yang ditulis ulang
- **Skill Security:** access control dasar (token/API key validation sebelum request diproses), rate limiting sederhana
- **Tools:** n8n Cloud, Python (API server kecil via FastAPI/Flask)
- **Deliverable:** Workflow n8n yang menerima pertanyaan via webhook, diproses oleh bot Fase 1 yang sama persis, dibalas dengan autentikasi token

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
