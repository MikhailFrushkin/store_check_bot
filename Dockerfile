FROM python:3.11-slim

WORKDIR /src

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код (папка src из проекта прямо в /src)
COPY src/ ./

# Создаем папки для данных и логов
RUN mkdir -p /src/data /src/logs

# Добавляем /src в PYTHONPATH
ENV PYTHONPATH=/src

# Команда запуска (теперь путь правильный)
CMD ["python", "-m", "store_check_bot.main"]