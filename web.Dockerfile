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

# Копируем все файлы приложения
COPY . .

# Делаем startup скрипт исполняемым
RUN chmod +x railway-start.sh

# Указываем порт
EXPOSE 8080

# Startup command через наш скрипт
CMD ["bash", "railway-start.sh"]
