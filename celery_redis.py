from celery import Celery

# Создание экземпляра Celery
celery = Celery('myapp', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Загрузка конфигурации из файла celeryconfig.py
celery.config_from_object('celeryconfig')

# Создание задачи
@celery.task
def add(x, y):
    return x + y
