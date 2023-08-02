# Используем базовый образ Python
FROM python:3.10.5

# Копируем файлы проекта в рабочую директорию контейнера
WORKDIR /app
COPY . /app

# Устанавливаем зависимости из requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TZ Europe/Moscow

# Опционально - указываем команду для запуска вашего скрипта
CMD ["python", "sync_scheduler.py"]
