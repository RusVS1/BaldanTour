from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from tours.embeddings import build_tour_embedding_text, encode_text
from tours.models import Tour


# Large fields (raw_text/details) can exceed default csv limits.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(10_000_000)


def normalize_space(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def parse_price_value(value: str) -> int | None:
    cleaned = re.sub(r'[^0-9]', '', value or '')
    return int(cleaned) if cleaned else None


def make_unique_key(row: dict[str, str]) -> str:
    parts = [
        row.get('country_slug', ''),
        row.get('request_url', ''),
        row.get('townfrom', ''),
        row.get('adult', ''),
        row.get('child', ''),
        row.get('night_min', ''),
        row.get('night_max', ''),
        row.get('checkin_beg', ''),
        row.get('checkin_end', ''),
        row.get('booking_link', ''),
        row.get('price', ''),
        row.get('room', ''),
        row.get('meal', ''),
        row.get('placement', ''),
    ]
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()


class Command(BaseCommand):
    help = 'Импорт туров из CSV в PostgreSQL + pgvector с генерацией эмбеддингов.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', dest='csv_path', default=settings.CSV_PATH)
        parser.add_argument('--limit', type=int, default=0, help='Ограничить количество строк (0 = все)')

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        limit = int(options['limit'])

        if not csv_path.exists():
            raise CommandError(f'CSV не найден: {csv_path}')

        with connection.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')

        created = 0
        updated = 0

        with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                if limit > 0 and idx > limit:
                    break

                clean_row = {k: normalize_space(v) for k, v in row.items()}
                unique_key = make_unique_key(clean_row)

                text_for_embedding = build_tour_embedding_text(clean_row)
                embedding = encode_text(text_for_embedding)

                defaults = {
                    'country_slug': clean_row.get('country_slug', ''),
                    'base_link': clean_row.get('base_link', ''),
                    'request_url': clean_row.get('request_url', ''),
                    'townfrom': clean_row.get('townfrom', ''),
                    'adult': int(clean_row.get('adult') or 0),
                    'child': int(clean_row.get('child') or 0),
                    'night_min': int(clean_row.get('night_min') or 0),
                    'night_max': int(clean_row.get('night_max') or 0),
                    'checkin_beg': clean_row.get('checkin_beg', ''),
                    'checkin_end': clean_row.get('checkin_end', ''),
                    'description': clean_row.get('description', ''),
                    'functions': clean_row.get('functions', ''),
                    'trip_dates': clean_row.get('trip_dates', ''),
                    'nights': clean_row.get('nights', ''),
                    'room': clean_row.get('room', ''),
                    'meal': clean_row.get('meal', ''),
                    'placement': clean_row.get('placement', ''),
                    'price': clean_row.get('price', ''),
                    'price_value': parse_price_value(clean_row.get('price', '')),
                    'booking_link': clean_row.get('booking_link', ''),
                    'raw_text': clean_row.get('raw_text', ''),
                    'embedding': embedding,
                }

                with transaction.atomic():
                    obj, was_created = Tour.objects.update_or_create(unique_key=unique_key, defaults=defaults)
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                if idx % 100 == 0:
                    self.stdout.write(f'Обработано: {idx} (created={created}, updated={updated})')

        self.stdout.write(self.style.SUCCESS(f'Импорт завершен. created={created}, updated={updated}'))
