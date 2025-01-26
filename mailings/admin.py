import requests
from django import forms
from django.forms.models import ModelForm, ModelFormMetaclass, BaseInlineFormSet
from django.contrib import admin
from .api import get_filtered_users
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
from .models import Mailing, MailingMedia, MailingInlineButton, MailingBatch
from datetime import datetime, date
from django.utils.html import format_html
from .api import get_available_filters
from django.db.models import Sum

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
            choices = [(choice['value'], choice['name']) for choice in field_data.get('choices', [])]
            return forms.ChoiceField(
                choices=[('', '---------')] + choices,
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
            return forms.ChoiceField(
                choices=[
                    (None, '---------'),
                    ('true', 'Да'),
                    ('false', 'Нет')
                ],
                widget=UnfoldAdminSelectWidget,
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
            choices = [(choice['value'], choice['name']) for choice in field_data.get('choices', [])]
            return forms.MultipleChoiceField(
                choices=choices,
                widget=UnfoldAdminSelectMultipleWidget(attrs={'style': 'height: 100%;'}),
                **base_attrs
            )
        return forms.CharField(
            widget=UnfoldAdminTextInputWidget,
            **base_attrs
        )


def create_dynamic_form():
    json_data = get_available_filters()
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
                        elif isinstance(self.fields[field_name], forms.ChoiceField) and value in [True, False]:
                            value = str(value).lower()
                        self.fields[field_name].initial = value

    return ModelFormMetaclass('MailingAdminForm', (MailingAdminForm,), {**{'Meta': MailingAdminForm.Meta}, **json_fields})


@admin.register(Mailing)
class MailingAdmin(ModelAdmin):
    form = create_dynamic_form()
    inlines = [MailingInlineButtonInline, MailingMediaInline]

    list_display = ('title', 'scheduled_at', 'status', 'created_by', 'created_at', 'delivery_stats', 'expected_users')
    list_filter = ('status', 'scheduled_at', 'created_at')
    search_fields = ('title', 'text')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'error_message')

    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True
    list_fullwidth = True
    list_filter_sheet = True

    def delivery_stats(self, obj):
        total_successful = obj.total_successful_users
        total_failed = obj.total_failed_users
        total = total_successful + total_failed
        if total == 0:
            return '-'
        return f"{total_successful}/{total}"
    delivery_stats.short_description = 'Доставка'

    def expected_users(self, obj):
        if obj.status != 'pending':
            return '-'
        try:
            response = get_filtered_users(obj.group_filters, page=1, limit=1)
            return response.get('count', 0)
        except Exception as e:
            return 0
    expected_users.short_description = 'Кол-во'

    def get_fieldsets(self, request, obj=None):
        json_data = get_available_filters()

        base_fieldsets = [
            ('Основное', {
                'fields': (
                    'title', 
                    'parse_mode',
                    'text',
                    'disable_web_page_preview',
                    'disable_notification',
                    'protect_content',
                    'scheduled_at',
                    'status',
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
                    'error_message',
                    'group_filters'
                ),
                'classes': ('collapse',)
            })
        )
        return base_fieldsets

    def save_model(self, request, obj, form, change):
        try:
            json_data = get_available_filters()
            available_filter_names = []
            for group in json_data['data']:
                available_filter_names.extend(field['name'] for field in group['fields'])

            dynamic_fields = {}
            for field_name, value in form.cleaned_data.items():
                if field_name in available_filter_names and value not in [None, '', [], {}]:
                    if isinstance(value, (datetime, date)):
                        dynamic_fields[field_name] = value.isoformat()
                    elif isinstance(value, bool):
                        dynamic_fields[field_name] = str(value).lower()
                    elif isinstance(value, (list, tuple)):
                        dynamic_fields[field_name] = value
                    else:
                        dynamic_fields[field_name] = str(value)

            obj.group_filters = dynamic_fields
            obj.created_by = request.user
            super().save_model(request, obj, form, change)

        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            print(f"Error in save_model: {str(e)}")
            raise


@admin.register(MailingMedia)
class MailingMediaAdmin(ModelAdmin):
    list_display = ['mailing', 'media_type', 'file_preview_small', 'caption', 'weight']
    list_filter = ['media_type', 'mailing']
    search_fields = ['mailing__title', 'caption']
    readonly_fields = ['file_preview']
    raw_id_fields = ['mailing']

    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True
    list_fullwidth = True
    list_filter_sheet = True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'caption' in form.base_fields:
            form.base_fields['caption'].widget = UnfoldAdminTextareaWidget(
                attrs={'rows': 3, 'placeholder': 'Подпись к медиафайлу'}
            )
        return form

    def file_preview(self, obj):
        if not obj.file:
            return '-'
        
        if obj.media_type == Mailing.MediaType.PHOTO:
            return format_html(
                '<div class="unfold-image-preview">'
                '<img src="{}" style="max-height: 200px; border-radius: 8px;" />'
                '</div>', 
                obj.file.url
            )
        elif obj.media_type in [Mailing.MediaType.VIDEO, Mailing.MediaType.VIDEO_NOTE]:
            return format_html(
                '<div class="unfold-video-preview">'
                '<video width="320" controls class="rounded-lg">'
                '<source src="{}" type="video/mp4">'
                '</video>'
                '</div>', 
                obj.file.url
            )
        elif obj.media_type == Mailing.MediaType.ANIMATION:
            return format_html(
                '<div class="unfold-image-preview">'
                '<img src="{}" style="max-height: 200px; border-radius: 8px;" />'
                '</div>', 
                obj.file.url
            )
        else:
            return format_html(
                '<div class="unfold-file-preview">'
                '<a href="{}" target="_blank" '
                'class="unfold-button unfold-button-primary">'
                'Просмотреть файл'
                '</a>'
                '</div>', 
                obj.file.url
            )

    def file_preview_small(self, obj):
        if not obj.file:
            return '-'
        
        preview_styles = 'class="unfold-preview-link" target="_blank"'
        
        if obj.media_type == Mailing.MediaType.PHOTO:
            return format_html(
                '<img src="{}" class="unfold-thumbnail" '
                'style="max-height: 50px; border-radius: 4px;" />', 
                obj.file.url
            )
        elif obj.media_type in [Mailing.MediaType.VIDEO, Mailing.MediaType.VIDEO_NOTE]:
            return format_html(
                '📹 <a href="{}" {}>'
                'Просмотреть видео</a>', 
                obj.file.url, preview_styles
            )
        elif obj.media_type == Mailing.MediaType.ANIMATION:
            return format_html(
                '<img src="{}" class="unfold-thumbnail" '
                'style="max-height: 50px; border-radius: 4px;" />', 
                obj.file.url
            )
        elif obj.media_type == Mailing.MediaType.AUDIO:
            return format_html(
                '🎵 <a href="{}" {}>'
                'Прослушать</a>', 
                obj.file.url, preview_styles
            )
        elif obj.media_type == Mailing.MediaType.VOICE:
            return format_html(
                '🎤 <a href="{}" {}>'
                'Прослушать</a>', 
                obj.file.url, preview_styles
            )
        else:
            return format_html(
                '📄 <a href="{}" {}>'
                'Открыть</a>', 
                obj.file.url, preview_styles
            )

    file_preview.short_description = 'Предпросмотр'
    file_preview_small.short_description = 'Файл'

    class Media:
        css = {
            'all': ['admin/css/unfold-media-preview.css']
        }
@admin.register(MailingBatch)
class MailingBatchAdmin(ModelAdmin):
    list_display = ['mailing', 'batch_number', 'successful_users', 'failed_users', 'created_at']
    list_filter = ['mailing', 'created_at']
    search_fields = ['mailing__title']
    readonly_fields = ['mailing', 'batch_number', 'successful_users', 'failed_users', 'error_details', 'created_at']
