"""
llm_fallback.py
----------------
Modul reusable untuk memanggil LLM API gratis dengan strategi fallback.

Urutan coba: Groq -> Cerebras -> OpenRouter -> Mistral
Begitu satu provider berhasil, hasilnya langsung dikembalikan. Kalau satu
provider gagal (rate limit, error jaringan, key kosong), otomatis lanjut ke
provider berikutnya dalam daftar.

Semua provider ini punya endpoint yang kompatibel dengan format OpenAI
Chat Completions, jadi cukup satu fungsi generik `_call_openai_compatible()`
yang dipakai ulang untuk semuanya — hanya base_url, model, dan env var
API key yang berbeda.

Desain modul ini sengaja dibuat reusable karena akan dipakai lagi di
Proyek 2-7 pada roadmap (secure webhook agent, multi-source RAG, dst).
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger("llm_fallback")


class AllProvidersFailedError(Exception):
    """Dilempar saat seluruh provider di daftar fallback gagal dipanggil."""


@dataclass
class ProviderConfig:
    name: str
    env_key: str
    base_url: str
    model: str


# Urutan di list ini = urutan prioritas fallback.
# Model dipilih yang masuk tier gratis per provider (per roadmap).
PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        name="groq",
        env_key="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1/chat/completions",
        # Catatan: "llama-3.3-70b-versatile" sudah di-deprecate Groq (shutdown 16 Agt 2026).
        # "openai/gpt-oss-120b" adalah pengganti resmi yang direkomendasikan dan masih
        # masuk free tier (30 req/menit, 1.000 req/hari per dokumentasi Groq terkini).
        model="openai/gpt-oss-120b",
    ),
    ProviderConfig(
        name="cerebras",
        env_key="CEREBRAS_API_KEY",
        base_url="https://api.cerebras.ai/v1/chat/completions",
        # Catatan: per dokumentasi resmi Cerebras (inference-docs.cerebras.ai/models/overview),
        # Llama SUDAH TIDAK ADA lagi di lineup Shared Inference mereka. Model free-tier yang
        # tersisa hanya "gpt-oss-120b" dan "qwen-3.8-27b". Dipilih qwen-3.8-27b karena rate
        # limit free trial-nya jauh lebih longgar (300 req/menit vs gpt-oss-120b yang cuma 5).
        model="qwen-3.8-27b",
    ),
    ProviderConfig(
        name="openrouter",
        env_key="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        # Dikonfirmasi masih aktif & gratis di openrouter.ai per pengecekan terakhir.
        model="meta-llama/llama-3.3-70b-instruct:free",
    ),
    ProviderConfig(
        name="mistral",
        env_key="MISTRAL_API_KEY",
        base_url="https://api.mistral.ai/v1/chat/completions",
        # Alias "-latest" ini resmi didukung Mistral dan otomatis mengikuti versi terbaru
        # (saat ini mengarah ke keluarga Mistral Small generasi terkini). Catatan privasi:
        # di paket gratis "Experiment", request BOLEH dipakai Mistral untuk training model
        # mereka -- relevan untuk bagian Security Considerations kalau dokumen sumbernya
        # sensitif, jangan pakai paket gratis Mistral untuk data rahasia.
        model="mistral-small-latest",
    ),
]

# Status code yang dianggap "coba provider lain", bukan error fatal.
RETRYABLE_STATUS = {401, 403, 404, 408, 409, 429, 500, 502, 503, 504}


def _call_openai_compatible(
    provider: ProviderConfig,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        provider.base_url, headers=headers, json=payload, timeout=timeout
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"{provider.name} -> HTTP {response.status_code}: {response.text[:300]}"
        )

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"{provider.name} -> format respons tak terduga: {data}") from exc


def generate_answer(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 600,
    timeout: int = 30,
    max_retries_per_provider: int = 1,
) -> tuple[str, str]:
    """
    Panggil LLM dengan fallback otomatis antar provider.

    Mengembalikan tuple (jawaban, nama_provider_yang_berhasil).
    Melempar AllProvidersFailedError kalau semua provider gagal.
    """
    errors: list[str] = []

    for provider in PROVIDERS:
        api_key = os.environ.get(provider.env_key, "").strip()
        if not api_key:
            logger.info("Lewati %s: %s belum diisi di .env", provider.name, provider.env_key)
            continue

        for attempt in range(1, max_retries_per_provider + 1):
            try:
                logger.info("Mencoba provider: %s (percobaan %d)", provider.name, attempt)
                answer = _call_openai_compatible(
                    provider, api_key, system_prompt, user_prompt,
                    temperature, max_tokens, timeout,
                )
                return answer, provider.name
            except Exception as exc:  # noqa: BLE001 - sengaja lebar, lalu lanjut fallback
                msg = str(exc)
                errors.append(msg)
                logger.warning("Provider %s gagal: %s", provider.name, msg)
                # Jeda singkat sebelum retry provider yang sama (bukan rate limit permanen)
                if attempt < max_retries_per_provider:
                    time.sleep(1.5)
                break  # lanjut ke provider berikutnya

    raise AllProvidersFailedError(
        "Semua provider gagal atau API key kosong.\n" + "\n".join(errors)
    )


if __name__ == "__main__":
    # Uji cepat manual: python src/llm_fallback.py
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    try:
        jawaban, provider = generate_answer(
            system_prompt="Kamu asisten yang menjawab singkat dan jelas dalam Bahasa Indonesia.",
            user_prompt="Sebutkan satu fakta menarik tentang Indonesia dalam satu kalimat.",
        )
        print(f"\n[Berhasil via {provider}]\n{jawaban}")
    except AllProvidersFailedError as e:
        print(f"\n[Gagal total]\n{e}")
