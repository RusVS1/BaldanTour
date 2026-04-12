from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_DIM = 768


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
        if self.provider in ("st", "sentence_transformers", "sentence-transformers"):
            return _st_embed(texts, expected_dim=self.dim)
        if self.provider == "dummy":
            return [_dummy_embed(t, self.dim) for t in texts]
        raise RuntimeError(f"Unknown EMBEDDINGS_PROVIDER: {self.provider}")


def get_embedder() -> Embedder:
    provider = (os.environ.get("EMBEDDINGS_PROVIDER") or "").strip().lower()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    dim = _get_dim()

    if not provider:
        # Prefer a local open-source multilingual model if available.
        if _can_use_sentence_transformers():
            provider = "sentence_transformers"
        elif api_key:
            provider = "openai"
        else:
            raise RuntimeError(
                "No real embeddings provider is available. Install sentence-transformers, "
                "set OPENAI_API_KEY, or explicitly set EMBEDDINGS_PROVIDER=dummy for local tests."
            )

    if provider in ("st", "sentence_transformers", "sentence-transformers"):
        # Use the real model dimension to avoid silent mismatches.
        model_dim = _st_model_dim()
        if dim and model_dim and dim != model_dim:
            raise RuntimeError(
                f"EMBEDDING_DIM={dim} but sentence-transformers model dim is {model_dim}. "
                "Set EMBEDDING_DIM to match the model (or unset it)."
            )
        dim = model_dim or dim

    return Embedder(provider=provider, dim=dim)


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


_ST_MODEL = None


def _can_use_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    return True


def _get_st_model():
    global _ST_MODEL
    if _ST_MODEL is not None:
        return _ST_MODEL

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers is not installed. Add it to requirements.txt "
            "or set EMBEDDINGS_PROVIDER=dummy/openai."
        ) from e

    # Open multilingual text embedding model with 768-dim output and Russian support.
    model_name = (
        os.environ.get("ST_EMBEDDING_MODEL")
        or os.environ.get("HF_EMBEDDING_MODEL")
        or "intfloat/multilingual-e5-base"
    ).strip()

    _ST_MODEL = SentenceTransformer(model_name)
    return _ST_MODEL


def _st_model_dim() -> int:
    model = _get_st_model()
    try:
        return int(model.get_sentence_embedding_dimension())
    except Exception:
        # Fallback: infer from a single encode.
        vec = model.encode(["dim_probe"], normalize_embeddings=True)
        return int(len(vec[0]))


def _st_embed(texts: list[str], *, expected_dim: int) -> list[list[float]]:
    model = _get_st_model()
    model_name = str(
        os.environ.get("ST_EMBEDDING_MODEL")
        or os.environ.get("HF_EMBEDDING_MODEL")
        or "intfloat/multilingual-e5-base"
    ).strip().lower()

    prepared = texts
    # E5 models are trained with task prefixes; for our similarity/search usage
    # we use the recommended "query: " prefix consistently.
    if "multilingual-e5" in model_name or model_name.endswith("/e5-base"):
        prepared = [f"query: {text or ''}" for text in texts]

    vectors = model.encode(prepared, normalize_embeddings=True)

    out: list[list[float]] = []
    for v in vectors:
        row = [float(x) for x in v]
        if expected_dim and len(row) != expected_dim:
            raise RuntimeError(f"Embedding dim mismatch: expected {expected_dim}, got {len(row)}.")
        out.append(row)
    return out
