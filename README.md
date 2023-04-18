# Дипломная работа к профессии Python-разработчик «API Сервис заказа товаров для розничных сетей».

Запуск проекта:

1. docker-compose up --build
2. docker-compose run --rm diploma sh -c "python manage.py makemigrations"
3. docker-compose run --rm diploma sh -c "python manage.py migrate"
4. docker-compose run --rm diploma sh -c "python manage.py createsuperuser"