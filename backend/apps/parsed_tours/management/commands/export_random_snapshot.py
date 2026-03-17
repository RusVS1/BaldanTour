from __future__ import annotations

import os
import random
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand

from apps.parsed_tours.models import ParsedAvailableTour, ParsedCountry


class Command(BaseCommand):
    help = "Export a random snapshot of parsed tours (including embeddings) as a JSON fixture-like file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            dest="out",
            default=os.getenv("SNAPSHOT_OUT", "/app/db/snapshot_random_300_tours.json"),
            help="Output path inside container (consider bind-mounting /app/db)",
        )
        parser.add_argument("--count", dest="count", type=int, default=300)
        parser.add_argument("--seed", dest="seed", type=int, default=42)

    def handle(self, *args, **options):
        out_path = Path(str(options["out"]))
        count = int(options["count"])
        seed = int(options["seed"])

        if count <= 0:
            raise SystemExit("--count must be > 0")

        ids = list(ParsedAvailableTour.objects.order_by("id").values_list("id", flat=True))
        if not ids:
            raise SystemExit("No tours found in DB.")

        rnd = random.Random(seed)
        take = min(count, len(ids))
        chosen = sorted(rnd.sample(ids, take))

        tours = list(ParsedAvailableTour.objects.filter(id__in=chosen).select_related("country").order_by("id"))
        country_ids = sorted({t.country_id for t in tours})
        countries = list(ParsedCountry.objects.filter(id__in=country_ids).order_by("id"))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = serializers.serialize("json", countries + tours, indent=2)
        out_path.write_text(payload, encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"[done] wrote {out_path} tours={len(tours)} countries={len(countries)}"))

