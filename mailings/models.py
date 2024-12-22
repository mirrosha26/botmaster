from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Mailing(models.Model):
   class Status(models.TextChoices):
       PENDING = 'pending', 'Ожидает отправки'
       PROCESSING = 'processing', 'В процессе'
       COMPLETED = 'completed', 'Отправлено' 
       FAILED = 'failed', 'Ошибка'

   class ContentType(models.TextChoices):
       TEXT = 'text', 'Текст'
       PHOTO = 'photo', 'Фото'
       VIDEO = 'video', 'Видео'
       DOCUMENT = 'document', 'Документ'
       AUDIO = 'audio', 'Аудио'

   class ParseMode(models.TextChoices):
       NONE = 'none', 'Без форматирования'
       MARKDOWN = 'markdown', 'Markdown'
       HTML = 'html', 'HTML'

   title = models.CharField(
       max_length=255,
       verbose_name='Название рассылки'
   )
   
   content_type = models.CharField(
       max_length=20,
       choices=ContentType.choices,
       default=ContentType.TEXT,
       verbose_name='Тип контента'
   )

   text = models.TextField(
       verbose_name='Текст сообщения',
       blank=True
   )

   parse_mode = models.CharField(
       max_length=10,
       choices=ParseMode.choices,
       default=ParseMode.NONE,
       verbose_name='Форматирование'
   )

   disable_web_page_preview = models.BooleanField(
       default=False,
       verbose_name='Отключить превью ссылок'
   )

   media_url = models.URLField(
       verbose_name='URL медиа',
       blank=True,
       help_text='URL для фото/видео/документа/аудио'
   )

   media_caption = models.TextField(
       verbose_name='Подпись к медиа',
       blank=True,
       help_text='Подпись для фото/видео/документа/аудио'
   )

   group_filters = models.JSONField(
       verbose_name='Фильтры для пользователей',
       blank=True,
       null=True,
       help_text='Выбранные значения фильтров для отбора пользователей',
       default=dict
   )

   inline_keyboard = models.JSONField(
       verbose_name='Кнопки',
       blank=True,
       null=True,
       help_text='JSON с конфигурацией кнопок'
   )

   scheduled_at = models.DateTimeField(
       verbose_name='Время отправки'
   )
   
   created_at = models.DateTimeField(
       auto_now_add=True,
       verbose_name='Время создания'
   )
   
   updated_at = models.DateTimeField(
       auto_now=True,
       verbose_name='Время обновления'
   )
   
   status = models.CharField(
       max_length=20,
       choices=Status.choices,
       default=Status.PENDING,
       verbose_name='Статус'
   )
   
   created_by = models.ForeignKey(
       settings.AUTH_USER_MODEL,
       on_delete=models.CASCADE,
       related_name='mailings',
       verbose_name='Создатель'
   )

   error_message = models.TextField(
       blank=True,
       null=True,
       verbose_name='Сообщение об ошибке'
   )

   class Meta:
       verbose_name = 'Рассылка'
       verbose_name_plural = 'Рассылки'
       ordering = ['-scheduled_at']

   def __str__(self):
       return f"{self.title} ({self.get_status_display()})"

   def clean(self):
       if self.content_type != self.ContentType.TEXT:
           if not self.media_url:
               raise ValidationError(
                   f'URL медиа обязателен для типа контента {self.get_content_type_display()}'
               )
       else:
           if not self.text:
               raise ValidationError('Текст сообщения обязателен для текстового контента')

   def save(self, *args, **kwargs):
       self.clean()
       super().save(*args, **kwargs)


