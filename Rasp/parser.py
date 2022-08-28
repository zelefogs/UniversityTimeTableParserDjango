import sqlite3
import threading

import numpy as np
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup as bs

pd.options.mode.chained_assignment = None

"""
В функции find_cab происходит поиск всех строк в которых в столбце 'Аудитория' номер кабинета содержит в себе передаваемый параметр
Входные данные: cab - Шаблон по которому происходит поиск пар
Выходные данные: found_sorted - Таблица с найденными парами в конкретном кабинете
"""


def find_cab(cab):
	days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
	try:
		df = pd.read_pickle('database.pkl')
		df.reset_index()
		filter_par = df[df['audit'].str.contains(cab, case=False) == True]
		found_class = filter_par
		category_day = pd.api.types.CategoricalDtype(categories=days, ordered=True)
		found_class['day_of_week'] = found_class['day_of_week'].astype(category_day)
		found_class['day_of_week'] = found_class['day_of_week'].astype('category').cat.set_categories(days)
		found_sorted = found_class.sort_values(by=['day_of_week', 'time'], ascending=[True, True])
		found_sorted['field_pair'] = found_sorted['field_pair'].map(lambda x: x + 1)
		'''found_sorted.to_excel('gotovo.xlsx', index=False, encoding='utf-8-sig')
		xfile = openpyxl.load_workbook('gotovo.xlsx')
		sheet = xfile.get_sheet_by_name('Sheet1')
		sheet.column_dimensions['A'].width = 7
		sheet.column_dimensions['B'].width = 13
		sheet.column_dimensions['C'].width = 25
		sheet.column_dimensions['D'].width = 25
		sheet.column_dimensions['E'].width = 100
		sheet.column_dimensions['F'].width = 43
		xfile.save('gotovo.xlsx')'''
		if not list(found_sorted.index.values):
			return False
		return found_sorted
	except FileNotFoundError:
		return "Нет файла"


def reload_database(URL="https://www.smtu.ru/ru/listschedule/"):
	try:
		r = requests.get(URL)
		soup = bs(r.text, "html.parser")
		test = soup.find_all(class_="gr")
		if not test:
			return 'Ошибка сервера, проверьте работоспособность расписания'
		urls = []
		k = 0
		for item in test:
			urls.append("https://www.smtu.ru" + item.a['href'])
		df = pd.DataFrame(
			{'field_pair': [], 'day_of_week': [], 'time': [], 'audit': [], 'subject': [], 'teacher': []})
		df = parse_rasp(urls[0])
		for i in range(1, len(urls)):
			print(df)
			df = pd.concat([df, parse_rasp(urls[i])], ignore_index=True)

		days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
		found_class = df
		category_day = pd.api.types.CategoricalDtype(categories=days, ordered=True)
		found_class['day_of_week'] = found_class['day_of_week'].astype(category_day)
		found_class['day_of_week'] = found_class['day_of_week'].astype('category').cat.set_categories(days)
		found_sorted = found_class.sort_values(by=['day_of_week', 'time'], ascending=[True, True])
		found_sorted = found_sorted.astype({'field_pair': np.int64})
		conn = sqlite3.connect('../db.sqlite3')
		found_sorted['id'] = 5
		for i in range(len(found_sorted)):
			found_sorted['id'][i] = i + 1
		found_sorted = found_sorted.set_index('id')
		found_sorted['day_of_week'] = found_sorted['day_of_week'].astype('str')
		found_sorted.to_sql('Rasp_table', conn, if_exists='replace')

		return 'База успешно обновлена'
	except requests.exceptions.ConnectionError:
		return 'Отсутствует интернет'


def parse_rasp(url):
	n = 0
	r = requests.get(url)
	soup = bs(r.text, "lxml")
	table = soup.find('table')
	try:
		df = pd.read_html(str(table))
	except ValueError:
		return "Проблемы с сервером"
	df = df[0]
	if not list(df.index.values):
		return

	dni = df.columns[0][1:len(df.columns[0])]
	school_day = table.find_all('tbody')[1:]
	kol_par = []
	for i in range(len(school_day)):
		kol_par.append(len(school_day[i].find_all('tr')))
	if len(dni) == 5:
		for i in range(1, 3):
			df.columns = df.columns.droplevel(i)
			df.columns = df.columns.droplevel(i)
		df.columns = df.columns.droplevel(1)
	elif len(dni) == 6:
		for i in range(1, 3):
			df.columns = df.columns.droplevel(i)
			df.columns = df.columns.droplevel(i)
		df.columns = df.columns.droplevel(1)
		df.columns = df.columns.droplevel(1)
	elif len(dni) == 4:
		for i in range(1, 5):
			df.columns = df.columns.droplevel(1)
	elif len(dni) == 3:
		for i in range(1, 4):
			df.columns = df.columns.droplevel(1)
	elif len(dni) == 2:
		for i in range(1, 3):
			df.columns = df.columns.droplevel(1)

	df.insert(0, "day_of_week", 5)
	df.insert(0, "field_pair", 0)
	time_par = ['08:30', '10:10', '11:50', '14:00', '15:40', '17:20', '19:00']
	df = df.rename(columns={'Время': 'time', '№ пары': 'field_pair', 'День недели': 'day_of_week',
	                        'Аудитория': 'audit', 'Преподаватель': 'teacher', 'Предмет': 'subject'})
	# Форматируется время и заполняются номера пар
	for i in range(0, len(df) - 1):
		input = df['time'][i]
		a = df['time'][i][:11] + " " + df['time'][i][11:]
		df = df.replace({'time': {input: a}})

	k = 0
	for i in range(len(school_day)):
		for j in range(kol_par[i]):
			df['field_pair'][k] = int(j)
			k += 1

	# Заполняются дни недели
	for i in range(0, (len(df) - 1)):
		df['day_of_week'][i] = dni[n]
		if df['field_pair'][i] > df['field_pair'][i + 1]:
			n += 1

	for i in range(0, len(df) - 1):
		lab = re.search(r'Лабораторное', df['subject'][i])
		prac = re.search(r'Практическое', df['subject'][i])
		lek = re.search(r'Лекция', df['subject'][i])
		if lab is not None:
			df['subject'][i] = df['subject'][i][:lab.start()] + " " + df['subject'][i][lab.start():]
		elif prac is not None:
			df['subject'][i] = df['subject'][i][:prac.start()] + " " + df['subject'][i][prac.start():]
		elif lek is not None:
			df['subject'][i] = df['subject'][i][:lek.start()] + " " + df['subject'][i][lek.start():]

	df['day_of_week'][len(df) - 1] = dni[-1]
	input_data = df['time'][len(df) - 1]
	a = df['time'][j][:11] + " " + df['time'][j][11:]
	df = df.replace({'time': {input: a}})
	lab = re.search(r'Лабораторное', df['subject'][len(df) - 1])
	prac = re.search(r'Практическое', df['subject'][len(df) - 1])
	lek = re.search(r'Лекция', df['subject'][len(df) - 1])
	if lab is not None:
		df['subject'][len(df) - 1] = df['subject'][len(df) - 1][:lab.start()] + " " + df['subject'][len(df) - 1][
		                                                                              lab.start():]
	elif prac is not None:
		df['subject'][len(df) - 1] = df['subject'][len(df) - 1][:prac.start()] + " " + df['subject'][len(df) - 1][
		                                                                               prac.start():]
	elif lek is not None:
		df['subject'][len(df) - 1] = df['subject'][len(df) - 1][:lek.start()] + " " + df['subject'][len(df) - 1][
		                                                                              lek.start():]
	return df


#reload_database()
