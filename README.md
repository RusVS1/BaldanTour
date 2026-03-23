# Запуск проекта

## Для локального тестирования

В корне проекта создайте файл `.env` со следующим содержимым:

```env
POSTGRES_DB=tour_aggregator
POSTGRES_USER=tour_aggregator
POSTGRES_PASSWORD=tour_aggregator
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

ANEXTOUR_PARSER_ROOT=/app/data/inputs
ANEXTOUR_PARSER_PATH=/app/anextour_available_tours_example.py
ANEXTOUR_HEADLESS=1
ANEXTOUR_TOWNFROM=moskva
ANEXTOUR_COUNTRY_SLUG=
ANEXTOUR_COUNTRY_SLUGS=
ANEXTOUR_ADULT_MAX=10
ANEXTOUR_CHILD_MAX=10
ANEXTOUR_STOP_FLAG=/app/STOP_PARSING.flag
ANEXTOUR_COMMIT_EVERY=50
```

---

## Сборка и запуск проекта

```bash
docker-compose up -d --build
```

---

## Доступ к сервисам

- Основной сайт:  
  http://localhost

- Swagger-документация API:  
  http://localhost/api/docs
