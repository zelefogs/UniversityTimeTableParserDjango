import sqlite3
import time

import aiohttp
import asyncio
import pandas as pd
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from pandas.core.frame import DataFrame
from pandas.api.types import CategoricalDtype

pd.options.mode.chained_assignment = None


async def fetch_content(url: str, session: aiohttp.ClientSession) -> tuple[Tag, int]:
	async with session.get(url) as response:
		data = await response.text()
		result = (bs(data, "lxml").table, int(url[36:-1]))
		return result


async def get_all_table() -> list[Tag]:
	tasks = []
	urls = await get_urls('https://www.smtu.ru/ru/listschedule/')
	async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=80)) as session:
		for item in urls:
			task = asyncio.create_task(fetch_content(item, session))
			tasks.append(task)
		result = await asyncio.gather(*tasks)
	return result


async def get_urls(url: str) -> set[str]:
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			result = await asyncio.gather(response.text())
			soup = bs(*result, "lxml")
			tags_a = soup.find_all('a')
		return {f"https://www.smtu.ru{i.get('href')}" for i in tags_a if '/ru/viewschedule/' in i.get('href')}


def reload():
	tables = asyncio.run(get_all_table())
	dataframe = DataFrame()
	for table in tables:
		dataframe = pd.concat([dataframe, parse_rasp(table[0], table[1])], ignore_index=True)
	cat_type_order = CategoricalDtype(
		['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
		ordered=True
	)
	dataframe['day_of_week'] = dataframe['day_of_week'].astype(cat_type_order)
	dataframe = dataframe.sort_values(by=['day_of_week', 'time'], ascending=[True, True])
	conn = sqlite3.connect('../db.sqlite3')
	dataframe.to_sql('Rasp_table', conn, if_exists='replace')


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


def refactor_column(df: DataFrame, gr_num: int) -> DataFrame:
	df.insert(0, "day_of_week", 0)
	df.insert(0, "field_pair", 0)
	df = df.rename(columns={'Время': 'time', '№ пары': 'field_pair', 'День недели': 'day_of_week',
	                        'Аудитория': 'audit', 'Преподаватель': 'teacher', 'Предмет': 'subject'})
	df.insert(0, "num_group", gr_num)
	return df


def format_time_and_number_pairs(df: DataFrame, table: Tag, days) -> DataFrame:
	all_days = get_all_days(table)
	amount_pairs = [len(all_days[index].find_all('tr')) for index, element in enumerate(all_days)]
	for index in range(len(df)):
		df['time'][index] = f"{df['time'][index][:11]} {df['time'][index][11:]}"
	k = 0
	for index in range(len(all_days)):
		for j in range(amount_pairs[index]):
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


def parse_rasp(table: Tag, group_number: int) -> DataFrame:
	all_days = get_all_days(table)
	dataframe = transform_to_dataframe(table)
	amount_lecture = get_amount_days(all_days)
	days = dataframe.columns[0][1:len(dataframe.columns[0])]
	dataframe = delete_extra_column_dataframe(dataframe, amount_lecture)
	dataframe = refactor_column(dataframe, group_number)
	dataframe = format_time_and_number_pairs(dataframe, table, days)
	dataframe = refactor_subject_name(dataframe)
	return dataframe


if __name__ == '__main__':
	start = time.time()
	reload()
	print(f'Время обновления - {time.time()-start} сек')