import os
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orders.settings")

celery_app = Celery("orders")
celery_app.config_from_object("django.conf:settings")
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.autodiscover_tasks()
