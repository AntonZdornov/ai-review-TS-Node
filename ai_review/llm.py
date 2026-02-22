from __future__ import annotations
import os
from openai import OpenAI


def make_client(provider: str, base_url: str | None) -> OpenAI:
    provider = provider.lower().strip()
    if provider not in {"openai", "local"}:
        raise ValueError("provider must be 'openai' or 'local'")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAI(api_key=api_key)

    # local
    # Многие локальные сервера игнорируют ключ, но SDK требует строку
    api_key = os.getenv("LOCAL_LLM_API_KEY", "ollama")
    base = base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    return OpenAI(api_key=api_key, base_url=base)