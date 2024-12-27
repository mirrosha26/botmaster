import requests
from django import forms
from django.forms.models import ModelForm, ModelFormMetaclass, BaseInlineFormSet
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.widgets import (
    UnfoldAdminTextInputWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldBooleanWidget,
    UnfoldAdminDateWidget,
    UnfoldAdminSelectMultipleWidget,
    UnfoldAdminTextareaWidget,
)
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import JSONField
from .models import Mailing, MailingMedia, MailingInlineButton, Poll
from datetime import datetime, date
from typing import List, Union

class MailingInlineButtonFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.order_by('weight')


class MailingInlineButtonInline(TabularInline):
    model = MailingInlineButton
    extra = 0
    min_num = 0
    max_num = 10
    formset = MailingInlineButtonFormSet
    ordering = ('weight',)
    fields = ('text', 'url', 'callback_data', 'weight')
    verbose_name = "элемент"
    verbose_name_plural = "Кнопки"

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'text':
            field.widget = UnfoldAdminTextInputWidget(attrs={'placeholder': 'Текст кнопки'})
        elif db_field.name == 'url':
            field.widget = UnfoldAdminTextInputWidget(attrs={'placeholder': 'https://example.com'})
        elif db_field.name == 'callback_data':
            field.widget = UnfoldAdminTextInputWidget(attrs={'placeholder': 'button_callback_data'})
        return field


class MailingMediaInline(TabularInline):
    model = MailingMedia
    extra = 0
    ordering = ('weight',)
    fields = ('media_type', 'file', 'caption', 'weight')
    verbose_name = "медиафайл"
    verbose_name_plural = "Медиафайлы"


class PollInline(TabularInline):
    model = Poll
    extra = 0
    ordering = ('weight',)
    fields = ('text', 'weight')
    verbose_name = "Опрос"
    verbose_name_plural = "Опросы"

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'text':
            field.widget = UnfoldAdminTextInputWidget(attrs={'placeholder': 'Текст опроса'})
        return field


class DynamicFieldsProcessor:
    @staticmethod
    def create_field_from_json(field_data):
        field_type = field_data.get('type', 'text')
        field_name = field_data.get('name')
        field_label = field_data.get('label')

        base_attrs = {
            'label': field_label,
            'required': False,
        }

        if field_type == 'choice':
            return forms.ChoiceField(
                choices=[(choice, choice) for choice in field_data.get('choices', [])],
                widget=UnfoldAdminSelectWidget,
                **base_attrs
            )
        elif field_type == 'text':
            return forms.CharField(
                widget=UnfoldAdminTextInputWidget,
                **base_attrs
            )
        elif field_type == 'number':
            return forms.IntegerField(
                widget=UnfoldAdminIntegerFieldWidget,
                min_value=field_data.get('min_value'),
                max_value=field_data.get('max_value'),
                help_text=f"Диапазон: {field_data.get('min_value')}-{field_data.get('max_value')}" if field_data.get('min_value') and field_data.get('max_value') else None,
                **base_attrs
            )
        elif field_type == 'boolean':
            return forms.BooleanField(
                widget=UnfoldBooleanWidget,
                **base_attrs
            )
        elif field_type == 'date':
            return forms.DateField(
                widget=UnfoldAdminDateWidget(
                    attrs={
                        'min': field_data.get('min_date'),
                        'max': field_data.get('max_date'),
                    }
                ),
                help_text=f"Период: {field_data.get('min_date')} - {field_data.get('max_date')}" if field_data.get('min_date') and field_data.get('max_date') else None,
                **base_attrs
            )
        elif field_type == 'multiple_choice':
            return forms.MultipleChoiceField(
                choices=[(choice, choice) for choice in field_data.get('choices', [])],
                widget=UnfoldAdminSelectMultipleWidget,
                **base_attrs
            )
        return forms.CharField(
            widget=UnfoldAdminTextInputWidget,
            **base_attrs
        )


def fetch_json_from_api(use_mock_data=True):
    if use_mock_data:
        return {
            "data": [
                {
                    "group_label": "пример из API (1)",
                    "fields": [
                        {"name": "name", "label": "Имя", "type": "text"},
                        {"name": "age", "label": "Возраст", "type": "number", "min_value": 18, "max_value": 65},
                        {"name": "is_active", "label": "Активный", "type": "boolean"}
                    ]
                },
                {
                    "group_label": "пример из API (2)",
                    "fields": [
                        {"name": "department", "label": "Отдел", "type": "choice", "choices": ["IT", "HR", "Finance", "Marketing"]},
                        {"name": "birth_date", "label": "Дата рождения", "type": "date", "min_date": "1900-01-01", "max_date": "2023-12-31"},
                        {"name": "tags", "label": "Теги", "type": "multiple_choice", "choices": ["Python", "JavaScript", "Go", "Rust"]}
                    ]
                }
            ]
        }
    return requests.get('http://127.0.0.1:8000/test-api/users/available-filters/').json()


def create_dynamic_form():
    json_data = fetch_json_from_api()
    json_fields = {
        field_data['name']: DynamicFieldsProcessor.create_field_from_json(field_data)
        for group in json_data['data']
        for field_data in group['fields']
    }

    class MailingAdminForm(ModelForm):
        class Meta:
            model = Mailing
            fields = '__all__'
            widgets = {
                'text': UnfoldAdminTextareaWidget,
                'media_caption': UnfoldAdminTextareaWidget,
            }

        def clean(self):
            cleaned_data = super().clean()
            return cleaned_data

        def __init__(self, *args, **kwargs):
            instance = kwargs.get('instance')
            super().__init__(*args, **kwargs)

            if instance and instance.group_filters:
                for field_name, value in instance.group_filters.items():
                    if field_name in self.fields:
                        if isinstance(self.fields[field_name], forms.DateField) and isinstance(value, str):
                            try:
                                value = datetime.fromisoformat(value).date()
                            except ValueError:
                                pass
                        elif isinstance(self.fields[field_name], forms.DateTimeField) and isinstance(value, str):
                            try:
                                value = datetime.fromisoformat(value)
                            except ValueError:
                                pass
                        self.fields[field_name].initial = value

    return ModelFormMetaclass('MailingAdminForm', (MailingAdminForm,), {**{'Meta': MailingAdminForm.Meta}, **json_fields})


@admin.register(Mailing)
class MailingAdmin(ModelAdmin):
    form = create_dynamic_form()
    inlines = [PollInline, MailingInlineButtonInline, MailingMediaInline]

    list_display = ('title', 'content_type', 'scheduled_at', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'content_type', 'scheduled_at', 'created_at')
    search_fields = ('title', 'text')
    readonly_fields = ('created_at', 'updated_at', 'status', 'error_message', 'created_by')

    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True
    list_fullwidth = True
    list_filter_sheet = True

    def get_fieldsets(self, request, obj=None):
        json_data = fetch_json_from_api()

        base_fieldsets = [
            ('Основное', {
                'fields': (
                    'title', 
                    'content_type',
                    'parse_mode',
                    'text',
                    'disable_web_page_preview',
                    'disable_notification',
                    'protect_content',
                    'scheduled_at',
                )
            }),
        ]

        for group in json_data['data']:
            base_fieldsets.append((
                _(group['group_label']),
                {
                    'fields': tuple(field['name'] for field in group['fields']),
                    'classes': ['tab']
                }
            ))

        base_fieldsets.append(
            ('Системная информация', {
                'fields': (
                    'created_by',
                    'created_at',
                    'updated_at',
                    'status',
                    'error_message',
                ),
                'classes': ('collapse',)
            })
        )

        return base_fieldsets

    def save_model(self, request, obj, form, change):
        try:
            dynamic_fields = {
                field_name: value.isoformat() if isinstance(value, (datetime, date)) else value
                for field_name, value in form.cleaned_data.items()
                if field_name in form.fields and value not in [None, '', [], {}]
            }

            obj.group_filters = dynamic_fields
            obj.created_by = request.user
            super().save_model(request, obj, form, change)

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            print(f"Error in save_model: {str(e)}")
            raise
