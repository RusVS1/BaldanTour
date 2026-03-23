# Tour Aggregator (Django)

## Production: init.sql for PostgreSQL

Для продакшн-запуска подключён явный `docker/db/init.sql` (создаёт расширения `pg_trgm`, `unaccent`, `citext`).

Важно: init-скрипты Postgres выполняются **только** при первом запуске на пустом volume.

- Запуск: `docker compose -p touragg -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- Переинициализировать БД (удалит данные): `docker compose -p touragg down -v`

## Быстрый старт (PostgreSQL)

### Вариант A: запуск в Docker (backend + PostgreSQL)

1) Скопируйте переменные окружения:

- `copy .env.example .env`

2) Запустите всё:

- `docker compose -p touragg up --build`

Backend будет доступен на `http://127.0.0.1:8000/`, Swagger — `http://127.0.0.1:8000/api/docs/`.

### Вариант B: локально (PostgreSQL в Docker, backend локально)

1) `copy .env.example .env`
2) `docker compose -p touragg up -d db`
3) `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
4) `.\.venv\Scripts\python.exe manage.py migrate`
5) `.\.venv\Scripts\python.exe manage.py runserver`

## Импорт туров из CSV

- Smoke-test на 2000 строк:
  - `.\.venv\Scripts\python.exe manage.py import_tours_csv --limit 2000`

CSV по умолчанию берутся из папки `Распаршенные страны`.

## API

- `GET /api/tours/` — поиск (по умолчанию сортировка от дешёвых)
- `GET /api/tours/{id}/`
- `GET /api/favorites/` — избранное пользователя (нужна сессия)
- `POST /api/favorites/{tour_id}/`
- `DELETE /api/favorites/{tour_id}/`
