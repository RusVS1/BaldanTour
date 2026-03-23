from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_DIM = 1536


def _get_dim() -> int:
    try:
        return int(os.environ.get("EMBEDDING_DIM") or DEFAULT_DIM)
    except ValueError:
        return DEFAULT_DIM


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@dataclass(frozen=True)
class Embedder:
    provider: str
    dim: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "openai":
            return _openai_embed(texts, self.dim)
        if self.provider == "dummy":
            return [_dummy_embed(t, self.dim) for t in texts]
        raise RuntimeError(f"Unknown EMBEDDINGS_PROVIDER: {self.provider}")


def get_embedder() -> Embedder:
    provider = (os.environ.get("EMBEDDINGS_PROVIDER") or "").strip().lower()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not provider:
        provider = "openai" if api_key else "dummy"
    return Embedder(provider=provider, dim=_get_dim())


def _dummy_embed(text: str, dim: int) -> list[float]:
    seed = hashlib.sha256((text or "").encode("utf-8")).digest()
    out: list[float] = []
    i = 0
    while len(out) < dim:
        h = hashlib.sha256(seed + bytes([i])).digest()
        for b in h:
            out.append((b - 128) / 128.0)
            if len(out) >= dim:
                break
        i = (i + 1) % 256
    return _normalize(out)


def _openai_embed(texts: list[str], expected_dim: int) -> list[list[float]]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for EMBEDDINGS_PROVIDER=openai")

    model = (os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small").strip()
    url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/") + "/embeddings"

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    vectors = [item["embedding"] for item in data.get("data", [])]

    if len(vectors) != len(texts):
        raise RuntimeError("Embeddings response size mismatch.")

    for v in vectors:
        if expected_dim and len(v) != expected_dim:
            raise RuntimeError(
                f"Embedding dim mismatch: expected {expected_dim}, got {len(v)}. "
                "Set EMBEDDING_DIM to match the selected model."
            )

    return [_normalize([float(x) for x in v]) for v in vectors]

