#!/bin/bash
# railway-start.sh - скрипт запуска для Railway

echo "🚀 Railway deployment starting..."

# Показываем информацию о среде
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "PORT: $PORT"
echo "DATABASE_URL set: $(if [ -n "$DATABASE_URL" ]; then echo "Yes"; else echo "No"; fi)"

# Показываем содержимое директории
echo "Files in /app:"
ls -la

# Проверяем, что web_app.py существует
if [ ! -f "web/web_app.py" ]; then
    echo "❌ web/web_app.py not found!"
    exit 1
fi

# Проверяем gunicorn
if ! command -v gunicorn &> /dev/null; then
    echo "❌ gunicorn not found!"
    pip install gunicorn
fi

# Запускаем приложение
if [ -n "$PORT" ]; then
    echo "🌐 Starting with gunicorn on port $PORT"
    exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload --access-logfile - --error-logfile - web.web_app:app
else
    echo "🌐 PORT not set, starting Flask dev server on 8080"
    exec python web/web_app.py
fi
