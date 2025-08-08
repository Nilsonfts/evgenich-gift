# Python web app для Railway
FROM python:3.12-slim

# Обновляем систему и устанавливаем зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements файлы
COPY web_requirements.txt .
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r web_requirements.txt

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 webuser && chown -R webuser:webuser /app
USER webuser

# Копируем приложение
COPY --chown=webuser:webuser . .

# Копируем startup скрипт
COPY --chown=webuser:webuser railway-start.sh /app/

# Указываем порт
EXPOSE 8080

# Startup command через наш скрипт
CMD ["bash", "railway-start.sh"]
