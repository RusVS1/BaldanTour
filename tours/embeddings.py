from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def build_tour_embedding_text(row: dict) -> str:
    parts = [
        f"Страна: {row.get('country_slug', '')}",
        f"Город вылета: {row.get('townfrom', '')}",
        f"Даты: {row.get('trip_dates', '')}",
        f"Ночи: {row.get('nights', '')}",
        f"Комната: {row.get('room', '')}",
        f"Питание: {row.get('meal', '')}",
        f"Размещение: {row.get('placement', '')}",
        f"Функции: {row.get('functions', '')}",
        f"Описание: {row.get('description', '')}",
        f"Текст: {row.get('raw_text', '')}",
    ]
    return ' | '.join([p for p in parts if p])


def encode_text(text: str) -> list[float]:
    model = get_embedding_model()
    vec = model.encode(text, normalize_embeddings=True)
    out = vec.tolist()
    if len(out) != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Неверная размерность эмбеддинга: {len(out)}. Ожидалось {settings.EMBEDDING_DIM}."
        )
    return out
