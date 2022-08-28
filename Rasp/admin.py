from django.contrib import admin
from .models import Table


class TableAdmin(admin.ModelAdmin):
	list_display = ['field_pair', 'day_of_week', 'time', 'audit', 'subject', 'teacher']


admin.site.register(Table, TableAdmin)
