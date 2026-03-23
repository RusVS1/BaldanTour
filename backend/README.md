# Tour Aggregator (Django + DRF + PostgreSQL)

Backend для агрегатора туров: поиск туров с фильтрами, избранное, регистрация/авторизация (session auth), Swagger/OpenAPI.

## Запуск (Docker, dev)

1) Создать `.env` (можно по примеру):
- `copy .env.example .env`

2) Поднять сервисы:
- `docker compose -p touragg up -d --build`

Ссылки:
- Backend: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/` (YAML) и `http://127.0.0.1:8000/api/schema/?format=json`

## Запуск (Docker, prod-режим + init.sql)

В прод-режиме подключён `docker/db/init.sql` (создаёт расширения `pg_trgm`, `unaccent`, `citext`).

Важно: init-скрипты Postgres выполняются **только** при первом старте на пустом volume.

- Запуск: `docker compose -p touragg -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- Переинициализировать БД (удалит данные): `docker compose -p touragg down -v`

## Импорт туров из CSV

Основной файл примера данных: `progon_merged.csv` (лежит в корне проекта).

Импорт внутри контейнера backend (с очисткой таблиц):
- `docker exec touragg-backend-1 python manage.py import_tours_csv --csv-file /app/progon_merged.csv --truncate --batch-size 2000`

Smoke-test (импорт ограниченного числа строк):
- `docker exec touragg-backend-1 python manage.py import_tours_csv --csv-file /app/progon_merged.csv --truncate --limit 2000`

## Аутентификация

Используется session auth (JWT/Token нет).

Эндпоинты:
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `GET /api/auth/status/`

## Tours API (основное)

Поиск туров:
- `GET /api/tours/`

Обязательные query-параметры:
- `townfrom`, `country_slug`, `departure_from`, `departure_to`, `nights_min`, `nights_max`, `child`, `adult`

Необязательные:
- `rest_type`, `hotel_type`, `hotel_category`, `meal`, `sort`, `page`, `page_size`

Сортировка (по умолчанию): `sort=price_asc` (самые дешёвые).

Фильтры (уникальные значения из БД):
- `GET /api/filters/rest-type/`
- `GET /api/filters/hotel-category/`
- `GET /api/filters/hotel-type/`
- `GET /api/filters/meal/`
- `GET /api/filters/townfrom/` (отдаёт русские названия)
- `GET /api/filters/country/` (отдаёт русские названия)

## Favorites API

Требует авторизацию (session).

- `GET /api/favorites/{user_id}/` — все избранные туры пользователя
- `POST /api/favorites/{user_id}/` — добавить тур в избранное (`{"tour_id": 123}`)
- `DELETE /api/favorites/{user_id}/{tour_id}/` — удалить тур из избранного

## Курс валют

- `GET /api/fx/rub/` — курс RUB к USD/EUR (онлайн-источник)

## AI поиск (pgvector)

- `POST /api/ai/search/` — семантический поиск по турам (эмбеддинги + pgvector)

Переменные окружения:
- `EMBEDDINGS_PROVIDER` — `openai` или `dummy` (по умолчанию `openai`, если задан `OPENAI_API_KEY`, иначе `dummy`)
- `OPENAI_API_KEY` — ключ для генерации эмбеддингов (multilingual модель)
- `OPENAI_EMBEDDING_MODEL` — по умолчанию `text-embedding-3-small`
- `EMBEDDING_DIM` — размерность вектора (по умолчанию `1536`, должна совпадать с моделью)

## Дамп/восстановление PostgreSQL

Рекомендованный способ, чтобы не повредить бинарный архив:

1) Сделать дамп внутри контейнера БД и забрать файлом:
- `docker exec -it touragg-db-1 sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/db.dump'`
- `docker cp touragg-db-1:/tmp/db.dump ./db.dump`

2) Восстановить у другого человека:
- `docker cp ./db.dump touragg-db-1:/dump.dump`
- `docker exec -it touragg-db-1 pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" /dump.dump`
