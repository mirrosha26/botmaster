import requests
from django import forms
from django.forms.models import ModelForm, ModelFormMetaclass
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import (
    UnfoldAdminTextInputWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldBooleanWidget,
    UnfoldAdminDateWidget,
    UnfoldAdminSelectMultipleWidget
)
from .models import Mailing
from datetime import datetime, date


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

    class MailingAdminForm(ModelForm):
        class Meta:
            model = Mailing
            fields = '__all__'

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

    form_class_attrs = {'Meta': MailingAdminForm.Meta}
    form_class_attrs.update(json_fields)

    return ModelFormMetaclass('MailingAdminForm', (MailingAdminForm,), form_class_attrs)


# Create the form class
MailingAdminForm = create_dynamic_form()

@admin.register(Mailing)
class MailingAdmin(ModelAdmin):
    form = MailingAdminForm
    list_display = ('title', 'content_type', 'scheduled_at', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'content_type', 'scheduled_at', 'created_at')
    search_fields = ('title', 'text', 'media_caption')
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
                    'text',
                    'content_type',
                    'scheduled_at',
                    'parse_mode',
                    'disable_web_page_preview',
                )
            }),
            ('Медиа', {
                'fields': (
                    'media_url',
                    'media_caption',
                ),
                'classes': ('collapse',)
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
        
        base_fieldsets.append((
            'Дополнительно',
            {
                'fields': (
                    'inline_keyboard',
                    'group_filters',
                    'created_by'
                ),
                'classes': ('collapse',)
            }
        ))
        
        return base_fieldsets
    
    def save_model(self, request, obj, form, change):
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
