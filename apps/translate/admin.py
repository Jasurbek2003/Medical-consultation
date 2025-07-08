from django.contrib import admin

from .models import Translate, Language

@admin.register(Translate)
class TranslateAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'lang')
    list_filter = ('lang__name',)
    search_fields = ('key', 'value')


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

