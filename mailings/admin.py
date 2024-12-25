import requests
from django import forms
from django.forms.models import ModelForm, ModelFormMetaclass
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import ArrayWidget
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
from .models import Mailing, MailingMedia
from datetime import datetime, date
import json


class MailingMediaInline(TabularInline):
    model = MailingMedia
    extra = 0
    fields = ('media_type', 'file', 'caption', 'order')
    hide_title = True
    min_num = 0  # Allow zero media files
    max_num = 10  # Optional: limit maximum number of media files
    validate_min = False  # Don't enforce minimum number of media files


class DynamicFieldsProcessor:
    @staticmethod
    def create_field_from_json(field_data):
        """Create a form field based on JSON field configuration"""
        field_type = field_data.get('type', 'text')
        field_name = field_data.get('name')
        field_label = field_data.get('label')
        
        if field_type == 'choice':
            return forms.ChoiceField(
                choices=[(choice, choice) for choice in field_data.get('choices', [])],
                widget=UnfoldAdminSelectWidget,
                label=field_label,
                required=False
            )
        elif field_type == 'text':
            return forms.CharField(
                widget=UnfoldAdminTextInputWidget,
                label=field_label,
                required=False
            )
        elif field_type == 'number':
            min_value = field_data.get('min_value')
            max_value = field_data.get('max_value')
            return forms.IntegerField(
                widget=UnfoldAdminIntegerFieldWidget,
                label=field_label,
                required=False,
                min_value=min_value,
                max_value=max_value,
                help_text=f"Допустимый диапазон: {min_value}-{max_value}" if min_value and max_value else None
            )
        elif field_type == 'boolean':
            return forms.BooleanField(
                widget=UnfoldBooleanWidget,
                label=field_label,
                required=False
            )
        elif field_type == 'date':
            min_date = field_data.get('min_date')
            max_date = field_data.get('max_date')
            return forms.DateField(
                widget=UnfoldAdminDateWidget(
                    attrs={
                        'min': min_date,
                        'max': max_date,
                    }
                ),
                label=field_label,
                required=False,
                help_text=f"Период: {min_date} - {max_date}" if min_date and max_date else None
            )
        elif field_type == 'multiple_choice':
            return forms.MultipleChoiceField(
                choices=[(choice, choice) for choice in field_data.get('choices', [])],
                widget=UnfoldAdminSelectMultipleWidget,
                label=field_label,
                required=False
            )
        return forms.CharField(
            widget=UnfoldAdminTextInputWidget,
            label=field_label,
            required=False
        )


def fetch_json_from_api(use_mock_data=True):
    if use_mock_data:
        mock_json = {
            "data": [
                {
                "group_label": "Базовая информация",
                "fields": [
                    {
                        "name": "name",
                        "label": "Имя",
                        "type": "text"
                    },
                    {
                        "name": "age",
                        "label": "Возраст",
                        "type": "number",
                        "min_value": 18,
                        "max_value": 65
                    },
                    {
                        "name": "is_active",
                        "label": "Активный",
                        "type": "boolean"
                    }
                ]
            },
            {
                "group_label": "Рабочая информация",
                "fields": [
                    {
                        "name": "department",
                        "label": "Отдел",
                        "type": "choice",
                        "choices": ["IT", "HR", "Finance", "Marketing"]
                    },
                    {
                        "name": "birth_date",
                        "label": "Дата рождения",
                        "type": "date",
                        "min_date": "1900-01-01",
                        "max_date": "2023-12-31"
                    },
                    {
                        "name": "tags",
                        "label": "Теги",
                        "type": "multiple_choice",
                        "choices": ["Python", "JavaScript", "Go", "Rust"]
                    }
                ]
            }
            ]
        }
        return mock_json
    else:
        api_url = 'http://127.0.0.1:8000/test-api/users/available-filters/'
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"Failed to fetch data from API. Status code: {response.status_code}")
        except requests.RequestException as e:
            raise ValueError(f"Error while connecting to API: {str(e)}")


def create_dynamic_form():
    try:
        json_data = fetch_json_from_api()
    except ValueError as e:
        raise RuntimeError(f"Error fetching dynamic fields: {str(e)}")

    json_fields = {}
    processor = DynamicFieldsProcessor()

    for group in json_data['data']:
        for field_data in group['fields']:
            field_name = field_data['name']
            json_fields[field_name] = processor.create_field_from_json(field_data)

    class CustomArrayWidget(ArrayWidget):
        def format_value(self, value):
            """Customize the display of array values"""
            if value is None:
                return []
            if isinstance(value, str):
                try:
                    import json
                    value = json.loads(value)
                except json.JSONDecodeError:
                    return []
            if isinstance(value, (list, tuple)):
                return [str(v) for v in value if v is not None and str(v).strip()]
            return []

        def value_from_datadict(self, data, files, name):
            value = super().value_from_datadict(data, files, name)
            if isinstance(value, list):
                return json.dumps(value)
            return value

    class MailingAdminForm(ModelForm):
        poll_options = JSONField(
            widget=UnfoldAdminTextareaWidget(
                attrs={
                    'placeholder': '["Вариант 1", "Вариант 2", "Вариант 3"]',
                    'rows': 4
                }
            ),
            required=False,
            help_text='Добавьте варианты ответов для опроса (от 2 до 10 вариантов). Формат: ["Вариант 1", "Вариант 2"]'
        )

        inline_keyboard = JSONField(
            widget=UnfoldAdminTextareaWidget(
                attrs={
                    'placeholder': '[{"text": "Текст кнопки", "url": "https://example.com"}]',
                    'rows': 4
                }
            ),
            required=False,
            help_text='Добавьте кнопки для Inline клавиатуры в формате JSON. Пример: [{"text": "Перейти", "url": "https://example.com"}]'
        )

        class Meta:
            model = Mailing
            fields = '__all__'
            widgets = {
                'text': UnfoldAdminTextareaWidget,
                'media_caption': UnfoldAdminTextareaWidget,
                'group_filters': ArrayWidget,
            }

        def clean_poll_options(self):
            options = self.cleaned_data.get('poll_options', [])
            if self.cleaned_data.get('content_type') == Mailing.ContentType.POLL:
                if not options:
                    raise ValidationError('Для опроса необходимо указать варианты ответов')
                
                if not isinstance(options, list):
                    raise ValidationError('Варианты ответов должны быть в формате списка JSON')
                
                # Filter out empty and None values
                options = [str(opt).strip() for opt in options if opt and str(opt).strip()]
                
                if len(options) < 2:
                    raise ValidationError('Необходимо указать минимум 2 варианта ответа')
                if len(options) > 10:
                    raise ValidationError('Максимальное количество вариантов ответа - 10')
            return options

        def clean_inline_keyboard(self):
            keyboard = self.cleaned_data.get('inline_keyboard', [])
            if keyboard:
                if not isinstance(keyboard, list):
                    raise ValidationError('Keyboard должен быть в формате списка JSON')

                try:
                    # Ensure each button has required fields
                    cleaned_keyboard = []
                    for button in keyboard:
                        if not isinstance(button, dict):
                            raise ValidationError('Каждая кнопка должна быть объектом с полями text и url/callback_data')
                        
                        if 'text' not in button or not button['text'].strip():
                            raise ValidationError('У каждой кнопки должно быть поле text')
                        
                        if 'url' not in button and 'callback_data' not in button:
                            raise ValidationError('У каждой кнопки должно быть поле url или callback_data')
                        
                        cleaned_keyboard.append(button)
                    
                    return cleaned_keyboard
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValidationError(f'Ошибка в формате JSON: {str(e)}')
            return []

        def clean(self):
            cleaned_data = super().clean()
            
            # Handle poll_options
            poll_options = cleaned_data.get('poll_options', [])
            if isinstance(poll_options, str):
                try:
                    poll_options = json.loads(poll_options)
                except json.JSONDecodeError:
                    poll_options = []
            cleaned_data['poll_options'] = [
                str(opt).strip() 
                for opt in poll_options 
                if opt and str(opt).strip()
            ]

            # Handle inline_keyboard
            inline_keyboard = cleaned_data.get('inline_keyboard', [])
            if isinstance(inline_keyboard, str):
                try:
                    inline_keyboard = json.loads(inline_keyboard)
                except json.JSONDecodeError:
                    inline_keyboard = []
            
            if inline_keyboard:
                try:
                    cleaned_keyboard = []
                    for button in inline_keyboard:
                        if not isinstance(button, dict):
                            raise ValidationError('Каждая кнопка должна быть объектом с полями text и url/callback_data')
                        
                        if 'text' not in button or not button['text'].strip():
                            raise ValidationError('У каждой кнопки должно быть поле text')
                        
                        if 'url' not in button and 'callback_data' not in button:
                            raise ValidationError('У каждой кнопки должно быть поле url или callback_data')
                        
                        cleaned_keyboard.append(button)
                    
                    cleaned_data['inline_keyboard'] = cleaned_keyboard
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValidationError(f'Ошибка в формате JSON: {str(e)}')
            else:
                cleaned_data['inline_keyboard'] = []
            
            return cleaned_data

        def __init__(self, *args, **kwargs):
            instance = kwargs.get('instance')
            super().__init__(*args, **kwargs)

            if instance:
                # Handle poll options
                if instance.poll_options:
                    self.initial['poll_options'] = instance.poll_options

                # Handle inline keyboard
                if instance.inline_keyboard:
                    self.initial['inline_keyboard'] = instance.inline_keyboard

                if instance.group_filters:
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

    form_class_attrs = {'Meta': MailingAdminForm.Meta}
    form_class_attrs.update(json_fields)

    return ModelFormMetaclass('MailingAdminForm', (MailingAdminForm,), form_class_attrs)


MailingAdminForm = create_dynamic_form()


@admin.register(Mailing)
class MailingAdmin(ModelAdmin):
    form = MailingAdminForm
    inlines = [MailingMediaInline]
    
    list_display = ('title', 'content_type', 'scheduled_at', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'content_type', 'scheduled_at', 'created_at')
    search_fields = ('title', 'text')
    readonly_fields = ('created_at', 'updated_at', 'status', 'error_message', 'created_by')

    def get_fieldsets(self, request, obj=None):
        try:
            json_data = fetch_json_from_api()
        except ValueError as e:
            raise RuntimeError(f"Error fetching fieldsets: {str(e)}")
        
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
            ('Настройки опроса', {
                'fields': (
                    'poll_question',
                    'poll_options',
                    'poll_type',
                    'correct_option_id',
                ),
                'classes': ('collapse',),
                'description': 'Настройки доступны только для типа контента "Опрос"'
            }),
        ]
        
        for group in json_data['data']:
            group_fields = [field['name'] for field in group['fields']]
            base_fieldsets.append((
                group['group_label'],
                {
                    'fields': tuple(group_fields),
                    'classes': ('wide',)
                }
            ))
        
        base_fieldsets.extend([
            ('Клавиатура', {
                'fields': (
                    'inline_keyboard',
                ),
                'classes': ('collapse',),
                'description': 'Настройка Inline кнопок под сообщением'
            }),
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
        ])
        
        return base_fieldsets
    
    def save_model(self, request, obj, form, change):
        try:
            dynamic_fields = {}
            for field_name, value in form.cleaned_data.items():
                if field_name in form.fields and value not in [None, '', [], {}]:
                    if isinstance(value, (datetime, date)):
                        dynamic_fields[field_name] = value.isoformat()
                    else:
                        dynamic_fields[field_name] = value
            obj.group_filters = dynamic_fields
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            messages.error(request, str(e))


@admin.register(MailingMedia)
class MailingMediaAdmin(ModelAdmin):
    list_display = ('mailing', 'media_type', 'order')
    list_filter = ('media_type', 'mailing')
    search_fields = ('mailing__title', 'caption')
    ordering = ('mailing', 'order')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make all fields optional
        for field_name in form.base_fields:
            form.base_fields[field_name].required = False
        return form