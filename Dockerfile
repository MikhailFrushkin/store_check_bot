FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/

# Создаем папки для данных и логов
RUN mkdir -p /app/data /app/logs

# Добавляем /app в PYTHONPATH
ENV PYTHONPATH=/app

# Устанавливаем рабочую директорию
WORKDIR /app

# Команда запуска
CMD ["python", "-m", "app.src.store_check_bot.main"]