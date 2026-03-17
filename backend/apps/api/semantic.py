from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from apps.parsed_tours.models import ParsedAvailableTour


DEFAULT_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _cache_path() -> Path:
    # Can be bind-mounted from host to speed up semantic search.
    return Path(os.getenv("EMBEDDINGS_CACHE_PATH", "/app/embeddings/parsed_tours_embeddings.npz"))


def _cuda_if_available() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def get_embedding_model(model_id: str = DEFAULT_MODEL_ID) -> SentenceTransformer:
    device = _cuda_if_available()
    return SentenceTransformer(model_id, device=device)


def embed_text(text: str, model_id: str = DEFAULT_MODEL_ID) -> np.ndarray:
    model = get_embedding_model(model_id)
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)[0]
    return vec.astype(np.float32, copy=False)


@dataclass(frozen=True)
class EmbeddingIndex:
    model_id: str
    ids: np.ndarray  # shape (n,)
    vectors: np.ndarray  # shape (n, dim), float32 normalized

    @property
    def dim(self) -> int:
        return int(self.vectors.shape[1])

    @staticmethod
    def _build_from_db(model_id: str) -> "EmbeddingIndex":
        # Load embeddings into a dense matrix once; used for cosine similarity via dot-product.
        qs = (
            ParsedAvailableTour.objects.exclude(embedding=None)
            .filter(embedding_version=model_id)
            .order_by("id")
            .values_list("id", "embedding")
        )
        total = qs.count()
        if total == 0:
            raise RuntimeError("No embeddings found in DB for model_id=%s" % model_id)

        # Get dimension from first row
        first_id, first_vec = qs.first()
        dim = len(first_vec or [])
        if dim <= 0:
            raise RuntimeError("Invalid embedding dim=%s for id=%s" % (dim, first_id))

        ids = np.empty((total,), dtype=np.int32)
        vectors = np.empty((total, dim), dtype=np.float32)

        i = 0
        for tour_id, vec in qs.iterator(chunk_size=2000):
            ids[i] = int(tour_id)
            vectors[i, :] = np.asarray(vec, dtype=np.float32)
            i += 1

        if i != total:
            ids = ids[:i]
            vectors = vectors[:i, :]

        return EmbeddingIndex(model_id=model_id, ids=ids, vectors=vectors)

    @classmethod
    def load(cls, model_id: str) -> "EmbeddingIndex":
        path = _cache_path()
        if path.exists():
            data = np.load(path, allow_pickle=False)
            ids = data["ids"].astype(np.int32, copy=False)
            vectors = data["vectors"].astype(np.float32, copy=False)
            return EmbeddingIndex(model_id=model_id, ids=ids, vectors=vectors)

        return cls._build_from_db(model_id=model_id)


@lru_cache(maxsize=1)
def get_index(model_id: str = DEFAULT_MODEL_ID) -> EmbeddingIndex:
    return EmbeddingIndex.load(model_id=model_id)


def semantic_search_ids(
    query_vec: np.ndarray,
    *,
    limit: int,
    model_id: str = DEFAULT_MODEL_ID,
    oversample: int = 50,
) -> list[tuple[int, float]]:
    """
    Returns list of (tour_id, score) sorted by score desc.
    Assumes vectors are normalized, so cosine similarity == dot product.
    """
    index = get_index(model_id=model_id)
    if query_vec.shape != (index.dim,):
        raise ValueError("query_vec has dim %s, expected %s" % (query_vec.shape, (index.dim,)))

    k = max(1, min(5000, int(limit) * int(oversample)))
    sims = index.vectors @ query_vec  # (n,)

    if k >= sims.shape[0]:
        idx = np.argsort(-sims)
    else:
        idx = np.argpartition(-sims, kth=k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]

    out: list[tuple[int, float]] = []
    for j in idx:
        out.append((int(index.ids[j]), float(sims[j])))
    return out


def semantic_search_country_ids(
    query_vec: np.ndarray,
    *,
    country_slug: str,
    limit: int,
    model_id: str = DEFAULT_MODEL_ID,
) -> list[tuple[int, float]]:
    """
    Faster + correct filtering for a single country: computes similarity only for tours in that country.
    """
    country_slug = (country_slug or "").strip()
    if not country_slug:
        raise ValueError("country_slug is required")

    index = get_index(model_id=model_id)
    if query_vec.shape != (index.dim,):
        raise ValueError("query_vec has dim %s, expected %s" % (query_vec.shape, (index.dim,)))

    # Pull IDs for the selected country from DB (IDs are primary keys, so list is stable).
    ids_subset = list(
        ParsedAvailableTour.objects.filter(country__slug=country_slug)
        .order_by("id")
        .values_list("id", flat=True)
    )
    if not ids_subset:
        return []

    # ids and index.ids are sorted; use binary search mapping.
    subset_ids = np.asarray(ids_subset, dtype=np.int32)
    pos = np.searchsorted(index.ids, subset_ids)
    # Guard: if cache and DB are out of sync, drop invalid positions.
    valid = (pos >= 0) & (pos < index.ids.shape[0]) & (index.ids[pos] == subset_ids)
    if not np.any(valid):
        return []

    pos = pos[valid]
    sims = index.vectors[pos] @ query_vec  # (m,)

    k = min(int(limit), sims.shape[0])
    if k <= 0:
        return []

    if k == sims.shape[0]:
        idx = np.argsort(-sims)
    else:
        idx = np.argpartition(-sims, kth=k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]

    out: list[tuple[int, float]] = []
    for j in idx:
        out.append((int(index.ids[pos[j]]), float(sims[j])))
    return out
