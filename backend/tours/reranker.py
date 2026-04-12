from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence, TypeVar


T = TypeVar("T")

DEFAULT_RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


@dataclass(frozen=True)
class RerankResult:
    item: T
    score: float


class OpenReranker:
    """
    Multilingual open-source neural reranker for the final AI-search stage.

    It is intentionally separate from embeddings: pgvector retrieves a small
    candidate set quickly, then this model reorders those candidates by direct
    query-tour relevance.
    """

    provider = "sentence_transformers_cross_encoder"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        items: Sequence[T],
        text_builder: Callable[[T], str],
    ) -> list[RerankResult[T]]:
        if not items:
            return []
        pairs = [(query, text_builder(item)) for item in items]
        raw_scores: Iterable[float] = self._get_model().predict(pairs)
        ranked = [
            RerankResult(item=item, score=float(score))
            for item, score in zip(items, raw_scores, strict=False)
        ]
        ranked.sort(key=lambda row: row.score, reverse=True)
        return ranked


_RERANKER: OpenReranker | None = None


def get_reranker() -> OpenReranker | None:
    enabled = os.environ.get("AI_RERANKER_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return None

    global _RERANKER
    if _RERANKER is not None:
        return _RERANKER

    model_name = (
        os.environ.get("AI_LLM_RERANKER_MODEL")
        or os.environ.get("AI_RERANKER_MODEL")
        or DEFAULT_RERANKER_MODEL
    ).strip()
    _RERANKER = OpenReranker(model_name=model_name)
    return _RERANKER
