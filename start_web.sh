#!/bin/bash

# start_web.sh - Скрипт для запуска веб-интерфейса локально

echo "🚀 Запуск веб-интерфейса Evgenich Bot Admin..."

# Проверяем наличие зависимостей
if ! pip show Flask > /dev/null 2>&1; then
    echo "📦 Устанавливаем Flask..."
    pip install Flask Werkzeug
fi

# Устанавливаем переменную окружения для разработки
export FLASK_ENV=development
export FLASK_DEBUG=1

# Запускаем веб-приложение
echo "🌐 Веб-интерфейс будет доступен по адресу: http://localhost:8080"
echo "📊 Нажмите Ctrl+C для остановки"
echo ""

python web_app.py
