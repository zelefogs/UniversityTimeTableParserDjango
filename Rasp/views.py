from django.shortcuts import render
from .models import Table
import re


def index(request):
	if request.method == "POST":
		name = request.POST.get("name")
		if re.match('[А-Я]\s?[0-9]?[0-9]?[0-9]?$', name):
			table = Table.objects.all()
			context = {'table': table, 'title': 'Расписание занятий', 'audit': name}
			return render(request, 'rasp/cabinet.html', context)
		else:
			con = {'error': 'Неправильно введен кабинет', 'inp': name}
			return render(request, 'rasp/index.html', con)
	else:
		table = Table.objects.all()
		context = {'table': table, 'title': 'Расписание занятий'}
		return render(request, 'rasp/index.html', context)


def cab(request):
	table = Table.objects.all()
	context = {'table': table, 'title': 'Расписание занятий'}
	return render(request, 'rasp/cabinet.html', context)
