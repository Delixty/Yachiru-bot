# Образ для контейнерного хостинга (например, BotHost / Railway / Fly.io)
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости и ставим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Переменная окружения TOKEN задаётся на стороне хостинга
CMD ["python", "bot.py"]
