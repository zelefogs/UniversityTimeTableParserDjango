from django.db import models


class Table(models.Model):
	index = models.IntegerField(primary_key=True)
	field_pair = models.IntegerField(verbose_name='№ пары', blank=True,
	                                 null=True)
	day_of_week = models.TextField(verbose_name='День недели', blank=True,
	                               null=True)
	time = models.TextField(verbose_name='Время', blank=True, null=True)
	audit = models.TextField(verbose_name='Аудитория', blank=True, null=True)
	subject = models.TextField(verbose_name='Предмет', blank=True, null=True)
	num_group = models.IntegerField(verbose_name='Номер группы', blank=True, null=True)
	teacher = models.TextField(verbose_name='Преподаватель', blank=True, null=True)

	def __str__(self):
		return self.subject

	class Meta:
		verbose_name = 'Пара'
		verbose_name_plural = 'Пары'
