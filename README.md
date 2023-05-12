# Дипломная работа к профессии Python-разработчик «API Сервис заказа товаров для розничных сетей».

  Реализован API Сервис заказа товаров для розничных сетей. Подключена база данных, реализованы основные методы по получению данных, 
регистрация и управление пользователями, возможность регистрации с помощью социальных сетей. Проработанны API endpoints. 
Выведены медленные методы в Celery. Докерезирован проект.

Запуск проекта:

1. docker-compose up --build
2. docker-compose run --rm diploma sh -c "python manage.py makemigrations"
3. docker-compose run --rm diploma sh -c "python manage.py migrate"
4. docker-compose run --rm diploma sh -c "python manage.py createsuperuser"
