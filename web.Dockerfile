# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt web_requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r web_requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаем директории для данных
RUN mkdir -p data logs

# Экспонируем порт
EXPOSE 8080

# Команда запуска веб-приложения
CMD ["python", "web_app.py"]
