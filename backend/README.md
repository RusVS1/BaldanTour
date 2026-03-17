# Бэкенд BaldanTour (Django)

Папка содержит бэкенд-API для фронтенда, Postgres и Swagger-документацию.

## Запуск

Из папки `backend`:

```powershell
docker compose up -d --build
```

После старта:
- Swagger UI: `http://localhost:18000/api/docs/`
- OpenAPI схема (YAML): `http://localhost:18000/api/schema/`

Порты в `docker-compose.yml`:
- API: `18000 -> 8000`
- Postgres: `15432 -> 5432`

## Данные (сид и слепок)

В репозиторий не кладется полный дамп Postgres (слишком большой). Вместо этого есть:
- `seed/sample_parsed_tours.json`: фиксированные тестовые данные (страны + туры) с эмбеддингами
- `db/snapshot_random_300_tours.json`: рандомный слепок 300 туров со всеми полями, включая `embedding`
- `embeddings/parsed_tours_embeddings.npz`: кэш эмбеддингов (ускоряет семантический поиск)

## Авторизация (login + password)

Эндпоинты:
- `POST /api/auth/register`
- `POST /api/auth/login`

Тестовый пользователь создается автоматически при старте контейнера:
- login: `db_test_user`
- password: `db_test_password_123`

## Личный кабинет

JWT обязателен (заголовок `Authorization: Bearer <token>`).

- `GET /api/me` возвращает:
  - `user` (id/login/created_at)
  - `favorites_count`

## Избранное

JWT обязателен.

- `GET /api/favorites/` список избранного
- `POST /api/favorites/add` body:
  ```json
  { "tour_id": 165077 }
  ```
- `DELETE /api/favorites/{tour_id}` удалить тур из избранного

## Туры

- `GET /api/health`
- `GET /api/countries`
- `GET /api/tours` (фильтры + пагинация `limit/offset`)
- `GET /api/tours/{id}`
- `POST /api/tours/semantic-search` семантический поиск:
  ```json
  { "text": "хочу тур в Испанию", "country": "spain", "limit": 5 }
  ```

Все параметры/поля запросов и ответов удобно смотреть и проверять в Swagger:
`http://localhost:18000/api/docs/`.

