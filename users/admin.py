from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Регистрация кастомной модели пользователя в админке
    Наследуемся от UserAdmin для сохранения стандартного функционала
    """
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')


