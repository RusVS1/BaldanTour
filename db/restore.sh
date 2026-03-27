#!/bin/bash
set -e

DUMP_FILE="/docker-entrypoint-initdb.d/data.dump"

echo "--- Скрипт восстановления запущен ---"

if [ -f "$DUMP_FILE" ]; then
    echo "Файл дампа найден: $DUMP_FILE"
    echo "Загрузка базы данных '$POSTGRES_DB'..."
    
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --exit-on-error \
        --clean \
        --if-exists \
        "$DUMP_FILE"
    
    echo "Загрузка завершена успешно."
else
    echo "Файл дампа не найден. Пропускаем загрузку."
fi