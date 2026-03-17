from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.parsed_tours.models import ParsedAvailableTour


class Command(BaseCommand):
    help = "Compute real text embeddings on GPU for parsed tours and store them in DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            dest="model",
            default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            help="HuggingFace / sentence-transformers model id",
        )
        parser.add_argument("--batch-size", dest="batch_size", type=int, default=128)
        parser.add_argument("--limit", dest="limit", type=int, default=0)
        parser.add_argument(
            "--only-missing",
            dest="only_missing",
            action="store_true",
            help="Only embed rows whose embedding_version != model id",
        )

    def handle(self, *args, **options):
        model_id = str(options["model"])
        batch_size = int(options["batch_size"])
        limit = int(options["limit"]) if int(options["limit"]) > 0 else None
        only_missing = bool(options["only_missing"])

        # Import lazily so backend can run without GPU deps unless this command is used.
        from sentence_transformers import SentenceTransformer  # noqa: WPS433
        import torch  # noqa: WPS433

        if not torch.cuda.is_available():
            raise SystemExit("CUDA is not available in this container. Ensure docker compose service has `gpus: all`.")

        device = "cuda"
        self.stdout.write(f"[gpu] loading model={model_id} device={device}")
        model = SentenceTransformer(model_id, device=device)

        base_qs = ParsedAvailableTour.objects.all()
        if only_missing:
            base_qs = base_qs.exclude(embedding_version=model_id)
        base_qs = base_qs.order_by("id")

        total = base_qs.count() if limit is None else limit
        self.stdout.write(f"[gpu] rows={total} batch_size={batch_size}")

        last_id = 0
        updated_total = 0

        while True:
            qs = base_qs.filter(id__gt=last_id)
            if limit is not None:
                remaining = limit - updated_total
                if remaining <= 0:
                    break
                take = min(batch_size, remaining)
            else:
                take = batch_size

            batch = list(qs[:take])
            if not batch:
                break

            texts = [
                " ".join(
                    [
                        (t.description or "").strip(),
                        (t.raw_text or "").strip(),
                        (t.booking_link or "").strip(),
                    ]
                ).strip()
                for t in batch
            ]

            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            for tour, vec in zip(batch, embeddings, strict=True):
                tour.embedding = vec.astype("float32").tolist()
                tour.embedding_version = model_id

            with transaction.atomic():
                ParsedAvailableTour.objects.bulk_update(batch, ["embedding", "embedding_version"], batch_size=batch_size)

            updated_total += len(batch)
            last_id = batch[-1].id

            if updated_total % (batch_size * 10) == 0 or updated_total == total:
                self.stdout.write(f"[gpu] updated={updated_total}/{total}")

        self.stdout.write(self.style.SUCCESS(f"[done] updated={updated_total} model={model_id}"))
