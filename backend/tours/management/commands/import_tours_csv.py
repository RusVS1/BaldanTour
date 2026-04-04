import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from tours.importers import TourRowImporter


class Command(BaseCommand):
    help = "Import tours from CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default=None,
            help="Path to a single CSV file to import (overrides --csv-dir).",
        )
        parser.add_argument(
            "--csv-dir",
            default=None,
            help="Path to folder with CSVs (default: ./Распаршенные страны).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after importing N rows total (for smoke tests).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Bulk insert batch size.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing tours/amenities/favorites before import.",
        )

    def handle(self, *args, **options):
        csv_file = options.get("csv_file")
        if csv_file:
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise SystemExit(f"CSV file not found: {csv_path}")
            csv_files = [csv_path]
            base_dir = None
        else:
            if options["csv_dir"]:
                base_dir = Path(options["csv_dir"])
            else:
                cwd = Path.cwd()
                if list(cwd.glob("anextour_available_tours_*.csv")):
                    base_dir = cwd
                elif (cwd / "parsed_country").exists():
                    base_dir = cwd / "parsed_country"
                else:
                    base_dir = cwd / "Распаршенные страны"

        limit = options["limit"]
        batch_size = options["batch_size"]
        truncate = bool(options.get("truncate"))
        importer = TourRowImporter(batch_size=batch_size, log=self.stderr.write)

        if truncate:
            self.stdout.write("Truncating existing tours data...")
            importer.truncate_all()

        if base_dir is not None:
            if not base_dir.exists():
                raise SystemExit(f"CSV dir not found: {base_dir}")

            csv_files = sorted(base_dir.glob("anextour_available_tours_*.csv"))
            if not csv_files:
                csv_files = sorted(base_dir.glob("*.csv"))
            if not csv_files:
                raise SystemExit(f"No CSV files found in: {base_dir}")

        total = 0
        for csv_path in csv_files:
            self.stdout.write(f"Importing: {csv_path.name}")
            total = self._import_one(csv_path, importer=importer, total=total, limit=limit)
            if limit is not None and total >= limit:
                break

        self.stdout.write(self.style.SUCCESS(f"Done. Imported (or skipped duplicates) up to {total} rows."))

    def _import_one(self, csv_path: Path, *, importer: TourRowImporter, total: int, limit: int | None) -> int:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            for row in reader:
                importer.add_row(row)
                total += 1
                if limit is not None and total >= limit:
                    importer.finalize()
                    return total

        importer.finalize()
        return total
