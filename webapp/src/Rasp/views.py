from django.shortcuts import render
from .models import Table
import re
import logging
logger = logging.getLogger('main')


def index(request):
	if request.method == "POST":
		name = request.POST.get("name").upper()
		logger.info(f'Пользователь запросил кабинет "{name[:6]}" ')
		if re.match('[А-Я]\s?[0-9]?[0-9]?[0-9]?$', name):
			table = Table.objects.filter(audit__regex=name)
			if table:
				context = {'table': table, 'title': 'Расписание занятий', 'audit': name}
				return render(request, 'rasp/cabinet.html', context)
			else:
				context = {'title': 'Расписание занятий', 'audit': name, 'not_found': 'Кабинет не найден'}
				return render(request, 'rasp/cabinet.html', context)
		else:
			con = {'error': 'Неправильно введен кабинет', 'inp': name}
			return render(request, 'rasp/index.html', con)
	else:
		context = {'title': 'Расписание занятий'}
		return render(request, 'rasp/index.html', context)