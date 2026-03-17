from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.parsed_tours.models import ParsedAvailableTour


class Command(BaseCommand):
    help = "Fill missing tour descriptions from raw_text (and basic fallbacks) to ensure every row has a description."

    def add_arguments(self, parser):
        parser.add_argument("--chunk-size", dest="chunk_size", type=int, default=2000)
        parser.add_argument("--limit", dest="limit", type=int, default=0)

    def handle(self, *args, **options):
        chunk_size = int(options["chunk_size"])
        limit = int(options["limit"]) if int(options["limit"]) > 0 else None

        qs = ParsedAvailableTour.objects.filter(description="").order_by("id")
        total = qs.count() if limit is None else min(limit, qs.count())
        self.stdout.write(f"[fill] rows={total} chunk_size={chunk_size}")

        updated = 0
        last_id = 0

        while True:
            batch_qs = qs.filter(id__gt=last_id)
            take = chunk_size
            if limit is not None:
                remaining = limit - updated
                if remaining <= 0:
                    break
                take = min(take, remaining)

            batch = list(batch_qs[:take])
            if not batch:
                break

            for t in batch:
                candidate = (t.raw_text or "").strip()
                if not candidate:
                    candidate = (t.request_url or "").strip() or f"tour:{t.country.slug}"
                t.description = candidate

            with transaction.atomic():
                ParsedAvailableTour.objects.bulk_update(batch, ["description"], batch_size=len(batch))

            updated += len(batch)
            last_id = batch[-1].id

            if updated % (chunk_size * 10) == 0 or updated == total:
                self.stdout.write(f"[fill] updated={updated}/{total}")

        self.stdout.write(self.style.SUCCESS(f"[done] updated={updated}"))

