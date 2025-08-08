#!/bin/bash
# railway-start.sh - скрипт запуска для Railway

echo "🚀 Railway deployment starting..."

# Показываем информацию о среде
echo "Python version: $(python --version)"
echo "PORT: $PORT"
echo "DATABASE_URL set: $(if [ -n "$DATABASE_URL" ]; then echo "Yes"; else echo "No"; fi)"

# Запускаем приложение
if [ -n "$PORT" ]; then
    echo "Starting with gunicorn on port $PORT"
    exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile - web_app:app
else
    echo "PORT not set, using default 8080"
    exec python web_app.py
fi
