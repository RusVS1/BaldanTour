# AnexTour Django Backend

Готовый backend для загрузки туров из `anextour_available_tours_abkhazia_example.csv` в PostgreSQL (с `pgvector`), генерации русскоязычных эмбеддингов и выдачи данных через REST API.

## Что реализовано

- `POST /api/auth/register/` - регистрация пользователя.
- `GET /api/tours/` - список туров с фильтрами.
- `GET /api/tours/<id>/` - получение тура по ID.
- `GET /api/tours/search/?query=...` - семантический поиск по эмбеддингам (`pgvector`, cosine).
- Команда импорта CSV + создание эмбеддингов: `python manage.py import_tours_csv --csv ...`.

## Стек

- Django 5 + DRF
- PostgreSQL + `pgvector`
- `sentence-transformers` (русская модель: `ai-forever/sbert_large_nlu_ru`)

## 1) Поднять БД

```bash
docker compose up -d
```

## 2) Установить зависимости

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## 3) Настроить .env

```bash
copy .env.example .env
```

При необходимости поправить переменные в `.env`:

- `DATABASE_*`
- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_DIM`
- `CSV_PATH`

## 4) Применить миграции

```bash
python manage.py migrate
```

## 5) Импортировать CSV и создать эмбеддинги

```bash
python manage.py import_tours_csv --csv D:/asoiu/anextour_available_tours_abkhazia_example.csv
```

Опционально тестовый лимит:

```bash
python manage.py import_tours_csv --csv D:/asoiu/anextour_available_tours_abkhazia_example.csv --limit 100
```

## 6) Запустить сервер

```bash
python manage.py runserver 0.0.0.0:8000
```

## API примеры

### Регистрация

`POST /api/auth/register/`

```json
{
  "username": "test_user",
  "email": "test@example.com",
  "password": "StrongPass123",
  "first_name": "Ivan",
  "last_name": "Petrov"
}
```

### Список туров с фильтрами

`GET /api/tours/?country_slug=abkhazia&townfrom=moskva&adult=2&child=0&min_price=50000&max_price=200000&page=1`

Поддерживаемые query-параметры:

- `country_slug`
- `townfrom`
- `meal`
- `room`
- `adult`
- `child`
- `checkin_beg`
- `min_price`
- `max_price`
- `night_from`
- `night_to`
- `q` (обычный текстовый поиск)

### Семантический поиск

`GET /api/tours/search/?query=семейный отель с wifi и кондиционером&limit=20`

## Важно

- Перед импортом убедитесь, что PostgreSQL доступен и расширение `vector` может быть создано.
- Модель `ai-forever/sbert_large_nlu_ru` тяжелая; для слабой машины можно заменить модель и `EMBEDDING_DIM` в `.env`.

## Структура

- `config/` - настройки проекта Django
- `accounts/` - API регистрации
- `tours/` - модель тура, API фильтров/поиска, импорт CSV
- `docker-compose.yml` - PostgreSQL + pgvector
