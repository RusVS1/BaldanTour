# Ежедневный запуск парсера -> PostgreSQL (Django)

Эта папка использует PostgreSQL в Docker (`docker-compose.yml`) и Django-команду импорта `import_tours_csv`.

## Что запускается каждый день

1) `bin/run_daily_parse_and_import.ps1` запускает Playwright-парсер на хосте (Windows).
   - CSV/JSON сохраняются в `D:\asoiu\проект\parsed_country\YYYY-MM-DD\`
   - Логи сохраняются в `D:\asoiu\проект\logs\daily_YYYY-MM-DD.log`
2) Затем скрипт запускает `docker compose -p touragg up -d db backend` и выполняет импорт:
   - `python manage.py import_tours_csv --csv-dir /app/parsed_country/YYYY-MM-DD`

Важно: БД физически хранится в Docker volume `pgdata` (это стандартно и надежно). В `проект\db\` у вас лежат дампы/бэкапы, но не сама data-директория Postgres.

## Подготовка (один раз)

1) Убедитесь, что есть входные файлы парсера:
   - `anextour_tours_dynamic.csv` или `anextour_tours_dynamics.csv`
   - `anextour_city_names.txt`

Скрипт сначала ищет их в `D:\asoiu\проект\data\inputs\`, если нет — копирует из `D:\asoiu\`.

2) Playwright браузер (Chromium) должен быть установлен в той среде Python, которой запускаете парсер:
   - `D:\asoiu\проект\.venv\Scripts\python.exe -m playwright install chromium`

3) Docker Desktop должен быть запущен (чтобы импорт в Postgres сработал).

## Ручной запуск

Из PowerShell:

```powershell
Set-Location "D:\asoiu\проект"
.\bin\run_daily_parse_and_import.ps1 -TownFrom moskva -CountrySlug spain -AdultMax 4 -ChildMax 4
```

Параметры:
- `-TownFrom` — город вылета (slug)
- `-CountrySlug` или `-CountrySlugs "spain,belarus,china"` — ограничить страны (для тестов)
- `-AdultMax`, `-ChildMax` — лимиты перебора

## Остановка “безопасно”

Парсер периодически проверяет файл-флаг остановки.

Создать флаг:

```powershell
.\bin\stop_parsing.ps1
```

Файл: `D:\asoiu\проект\STOP_PARSING.flag`

Следующий запуск daily-скрипта этот флаг удаляет, чтобы не зависать в “вечной остановке”.

## Установка ежедневного запуска

```powershell
Set-Location "D:\asoiu\проект"
.\bin\install_daily_task.ps1 -At "03:30"
```

Проверка в Планировщике задач:
- Задача: `AnexTourDailyParse`
- Действие: `powershell.exe ... run_daily_parse_and_import.ps1`

