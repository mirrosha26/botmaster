from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from unfold.admin import ModelAdmin
from django.utils.translation import gettext_lazy as _
from django.forms import TextInput
from unfold.widgets import (
    UnfoldAdminTextInputWidget,
)
from .models import User
from django.contrib.auth.models import Group

admin.site.unregister(Group)

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = UnfoldAdminTextInputWidget(
            attrs={
                'placeholder': 'Введите имя пользователя'
            }
        )
        self.fields['email'].widget = UnfoldAdminTextInputWidget(
            attrs={
                'placeholder': 'Введите email'
            }
        )
        self.fields['password1'].widget = UnfoldAdminTextInputWidget(
            attrs={
                'type': 'password',
                'placeholder': 'Введите пароль'
            }
        )
        self.fields['password2'].widget = UnfoldAdminTextInputWidget(
            attrs={
                'type': 'password',
                'placeholder': 'Подтвердите пароль'
            }
        )

@admin.register(User)
class CustomUserAdmin(ModelAdmin, UserAdmin):
    """
    Регистрация кастомной модели пользователя в админке с использованием Unfold
    """
    add_form = CustomUserCreationForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    list_display_links = ('username', 'email')
    empty_value_display = '-пусто-'
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    date_hierarchy = 'date_joined'
    
    # Настройки Unfold
    unfold_mobile_scroll = True
    unfold_mobile_basic = False
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True