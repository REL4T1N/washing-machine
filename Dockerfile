FROM python:3.12-slim

# Переменные для Python:
# PYTHONDONTWRITEBYTECODE - не создавать .pyc файлы (мусор в контейнере)
# PYTHONUNBUFFERED - чтобы логи сразу шли в консоль Docker, а не буферизировались
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Пользователь
RUN useradd -m -u 1000 appuser 
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Запуск
CMD ["python", "main.py"]