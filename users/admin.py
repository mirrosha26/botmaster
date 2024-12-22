from django.contrib import admin
from unfold.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(ModelAdmin, UserAdmin):
    """
    Регистрация кастомной модели пользователя в админке с использованием Unfold
    Наследуемся от ModelAdmin для функционала Unfold и UserAdmin для стандартного функционала
    """
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    
    # Unfold специфичные настройки
    ordering = ('-id',)
    date_hierarchy = 'date_joined'
    
    # Добавляем секции для Unfold
    list_display_links = ('username', 'email')
    empty_value_display = '-пусто-'
    
    # Настройки для мобильного отображения
    unfold_mobile_scroll = True
    unfold_mobile_basic = False