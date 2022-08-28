from django.urls import path
from .views import index, cab

urlpatterns = [
	path('', index),
]
