import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Rasp_smtu.settings")

app = Celery("Rasp_smtu")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()