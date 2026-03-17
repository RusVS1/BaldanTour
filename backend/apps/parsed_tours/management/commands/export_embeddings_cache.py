from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand

from apps.parsed_tours.models import ParsedAvailableTour


class Command(BaseCommand):
    help = "Export parsed tour embeddings from DB into a compressed .npz cache for fast semantic search."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            dest="out",
            default=os.getenv("EMBEDDINGS_CACHE_PATH", "/app/embeddings/parsed_tours_embeddings.npz"),
            help="Output path inside container (consider bind-mounting to host)",
        )
        parser.add_argument(
            "--model",
            dest="model",
            default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            help="Only export rows with this embedding_version",
        )

    def handle(self, *args, **options):
        out_path = Path(str(options["out"]))
        model_id = str(options["model"])

        qs = (
            ParsedAvailableTour.objects.exclude(embedding=None)
            .filter(embedding_version=model_id)
            .order_by("id")
            .values_list("id", "embedding")
        )
        total = qs.count()
        if total == 0:
            raise SystemExit(f"No embeddings to export for model_id={model_id}")

        first_id, first_vec = qs.first()
        dim = len(first_vec or [])
        if dim <= 0:
            raise SystemExit(f"Invalid embedding dim={dim} for id={first_id}")

        ids = np.empty((total,), dtype=np.int32)
        vectors = np.empty((total, dim), dtype=np.float32)

        self.stdout.write(f"[export] rows={total} dim={dim} out={out_path}")

        i = 0
        for tour_id, vec in qs.iterator(chunk_size=2000):
            ids[i] = int(tour_id)
            vectors[i, :] = np.asarray(vec, dtype=np.float32)
            i += 1

        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, ids=ids, vectors=vectors)
        self.stdout.write(self.style.SUCCESS(f"[done] wrote {out_path}"))

