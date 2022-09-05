import sqlite3
import time

import numpy as np
import pandas as pd
import requests
import re
from requests.exceptions import RequestException
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from pandas.core.frame import DataFrame

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


start_time = time.time()


def take_table(url: str) -> Tag:
	return bs(requests.get(url, timeout=0.01).text, "lxml").table


def transform_to_dataframe(table: Tag) -> DataFrame:
	return pd.read_html(str(table))[0]


def get_all_days(table: Tag) -> list[Tag]:
	return table.find_all('tbody')[1:]


def get_amount_days(all_days: list[Tag]) -> list[int]:
	amount_days = [len(day.find_all('tr')) for day in all_days]
	return amount_days


def delete_extra_column_dataframe(df: DataFrame, num_of_days: list[int]) -> DataFrame:
	match len(num_of_days):
		case 5:
			for i in range(1, 3):
				df.columns = df.columns.droplevel(i)
				df.columns = df.columns.droplevel(i)
			df.columns = df.columns.droplevel(1)
		case 6:
			for i in range(1, 3):
				df.columns = df.columns.droplevel(i)
				df.columns = df.columns.droplevel(i)
			df.columns = df.columns.droplevel(1)
			df.columns = df.columns.droplevel(1)
		case 4:
			for i in range(1, 5):
				df.columns = df.columns.droplevel(1)
		case 3:
			for i in range(1, 4):
				df.columns = df.columns.droplevel(1)
		case 2:
			for i in range(1, 3):
				df.columns = df.columns.droplevel(1)
	return df


def refactor_column(df: DataFrame) -> DataFrame:
	df.insert(0, "day_of_week", 0)
	df.insert(0, "field_pair", 0)
	df = df.rename(columns={'Время': 'time', '№ пары': 'field_pair', 'День недели': 'day_of_week',
	                        'Аудитория': 'audit', 'Преподаватель': 'teacher', 'Предмет': 'subject'})
	return df


def format_time_and_number_pairs(df: DataFrame, table: Tag, days) -> DataFrame:
	all_days = get_all_days(table)
	amount_pairs = [len(all_days[index].find_all('tr')) for index, element in enumerate(all_days)]
	for index, element in enumerate(df):
		df['time'][index] = f"{df['time'][index][:11]} {df['time'][index][11:]}"
	k = 0
	for index, element in enumerate(all_days):
		for j, el in enumerate(amount_pairs):
			df['field_pair'][k] = j + 1
			k += 1
	n = 0
	for index in range(len(df) - 1):
		df['day_of_week'][index] = days[n]
		if df['field_pair'][index] > df['field_pair'][index + 1]:
			n += 1
	df['day_of_week'][-1:] = days[-1]
	return df


def refactor_subject_name(df: DataFrame) -> DataFrame:
	for index in range(len(df)):
		lab = re.search(r'Лабораторное', df['subject'][index])
		prac = re.search(r'Практическое', df['subject'][index])
		lek = re.search(r'Лекция', df['subject'][index])
		if lab:
			df['subject'][index] = f"{df['subject'][index][:lab.start()]} {df['subject'][index][lab.start():]}"
		elif prac:
			df['subject'][index] = f"{df['subject'][index][:prac.start()]} {df['subject'][index][prac.start():]}"
		elif lek:
			df['subject'][index] = f"{df['subject'][index][:lek.start()]} {df['subject'][index][lek.start():]}"
	return df


def parse_rasp(url):
	table = take_table(url)
	all_days = get_all_days(table)
	dataframe = transform_to_dataframe(table)
	amount_lecture = get_amount_days(all_days)
	days = dataframe.columns[0][1:len(dataframe.columns[0])]
	dataframe = delete_extra_column_dataframe(dataframe, amount_lecture)
	dataframe = refactor_column(dataframe)
	dataframe = format_time_and_number_pairs(dataframe, table, days)
	dataframe = refactor_subject_name(dataframe)
	return dataframe


if __name__ == '__main__':
	print(parse_rasp('https://www.smtu.ru/ru/viewschedule/2141/')['subject'])
