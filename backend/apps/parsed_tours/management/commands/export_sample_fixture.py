from __future__ import annotations

import os
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand
from django.db.models import Min

from apps.parsed_tours.models import ParsedAvailableTour, ParsedCountry


class Command(BaseCommand):
    help = "Export a small JSON fixture (countries + sample tours with embeddings) for shipping in repo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            dest="out",
            default=os.getenv("SAMPLE_FIXTURE_OUT", "/app/seed/sample_parsed_tours.json"),
            help="Output path inside container",
        )
        parser.add_argument("--per-country", dest="per_country", type=int, default=50)

    def handle(self, *args, **options):
        out_path = Path(str(options["out"]))
        per_country = int(options["per_country"])

        if per_country <= 0:
            raise SystemExit("--per-country must be > 0")

        # Ensure output dir exists.
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Build a stable sample set: for each country, take the smallest IDs (deterministic across runs).
        ids: list[int] = []
        for country in ParsedCountry.objects.order_by("slug"):
            qs = ParsedAvailableTour.objects.filter(country=country).order_by("id").values_list("id", flat=True)[:per_country]
            ids.extend(list(qs))

        if not ids:
            raise SystemExit("No tours found in DB to export.")

        self.stdout.write(f"[export] countries={ParsedCountry.objects.count()} tours_sample={len(ids)} out={out_path}")

        countries = list(ParsedCountry.objects.order_by("id"))
        tours = list(ParsedAvailableTour.objects.filter(id__in=sorted(set(ids))).order_by("id"))

        payload = serializers.serialize("json", countries + tours, indent=2)
        out_path.write_text(payload, encoding="utf-8")

        # Basic sanity: show lowest ID exported.
        min_id = ParsedAvailableTour.objects.filter(id__in=ids).aggregate(m=Min("id"))["m"]
        self.stdout.write(self.style.SUCCESS(f"[done] wrote {out_path} min_tour_id={min_id}"))
