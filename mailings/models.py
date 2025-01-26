from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.validators import FileExtensionValidator
import os


def mailing_media_path(instance, filename):
    """
    Генерирует путь для сохранения медиафайла:
    media/mailings/{mailing_id}/{media_type}/{filename}
    """
    return f'mailings/{instance.mailing.id}/{instance.media_type}/{filename}'


class Mailing(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает отправки'
        PROCESSING = 'processing', 'В процессе'
        COMPLETED = 'completed', 'Передано в бот'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменено'

    class MediaType(models.TextChoices):
        PHOTO = 'photo', 'Фото'                    # send_photo
        VIDEO = 'video', 'Видео'                   # send_video
        DOCUMENT = 'document', 'Документ'          # send_document
        AUDIO = 'audio', 'Аудио'                   # send_audio
        VOICE = 'voice', 'Голосовое сообщение'     # send_voice
        ANIMATION = 'animation', 'Анимация'        # send_animation
        VIDEO_NOTE = 'video_note', 'Видео-кружок'  # send_video_note

    class ParseMode(models.TextChoices):
        NONE = 'NONE', 'Без форматирования'
        HTML = 'HTML', 'HTML'  
        MARKDOWNV2 = 'MarkdownV2', 'Markdown V2'

    title = models.CharField(
        max_length=255,
        verbose_name='Название рассылки'
    )

    text = models.TextField(
        verbose_name='Текст сообщения',
        blank=True
    )

    parse_mode = models.CharField(
        max_length=12,
        choices=ParseMode.choices,
        default=ParseMode.NONE,
        verbose_name='Форматирование'
    )

    disable_web_page_preview = models.BooleanField(
        default=False,
        verbose_name='Отключить превью ссылок'
    )

    disable_notification = models.BooleanField(
        default=False,
        verbose_name='Отключить уведомление'
    )

    protect_content = models.BooleanField(
        default=False,
        verbose_name='Защитить от пересылки'
    )

    group_filters = models.JSONField(
        verbose_name='Фильтры для пользователей',
        blank=True,
        null=True,
        help_text='Выбранные значения фильтров для отбора пользователей',
        default=dict
    )

    reply_markup = models.JSONField(
        verbose_name='Клавиатура',
        blank=True,
        null=True,
        help_text='JSON с конфигурацией клавиатуры (inline/reply/remove)'
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

    @property
    def total_successful_users(self):
        return sum(batch.successful_users for batch in self.batches.all())

    @property 
    def total_failed_users(self):
        return sum(batch.failed_users for batch in self.batches.all())

    def clean(self):
        # Проверяем, сохранен ли объект
        if not self.pk:
            return  # Если объект не сохранен, пропускаем валидацию кнопок

        # Получаем все кнопки, которые не помечены на удаление
        if hasattr(self, 'inline_buttons'):
            active_buttons = [
                button for button in self.inline_buttons.all()
                if not (hasattr(button, 'DELETE') and button.DELETE)
            ]
            
            # Проверяем наличие текста, только если есть активные кнопки
            if active_buttons and not self.text:
                raise ValidationError('Текст сообщения обязателен при наличии кнопок')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.batches.all().delete()


class MailingMedia(models.Model):
    """Модель для хранения медиафайлов рассылки"""
    
    # Определяем допустимые расширения файлов для каждого типа медиа
    MEDIA_TYPE_VALIDATORS = {
        Mailing.MediaType.PHOTO: ['jpg', 'jpeg', 'png', 'webp'],
        Mailing.MediaType.VIDEO: ['mp4', 'avi', 'mov', 'webm'],
        Mailing.MediaType.DOCUMENT: [
            'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'zip', 'rar',
            'jpg', 'jpeg', 'png', 'webp', 'mp4', 'avi', 'mov', 'webm'
        ],
        Mailing.MediaType.AUDIO: ['mp3', 'wav', 'ogg'],
        Mailing.MediaType.VOICE: ['ogg', 'mp3', 'wav'],
        Mailing.MediaType.ANIMATION: ['gif'],
        Mailing.MediaType.VIDEO_NOTE: ['mp4']
    }

    # Максимальные размеры файлов (в байтах)
    MAX_FILE_SIZES = {
        Mailing.MediaType.PHOTO: 10 * 1024 * 1024,      # 10MB
        Mailing.MediaType.VIDEO: 50 * 1024 * 1024,      # 50MB
        Mailing.MediaType.DOCUMENT: 20 * 1024 * 1024,   # 20MB
        Mailing.MediaType.AUDIO: 20 * 1024 * 1024,      # 20MB
        Mailing.MediaType.VOICE: 10 * 1024 * 1024,      # 10MB
        Mailing.MediaType.ANIMATION: 10 * 1024 * 1024,  # 10MB
        Mailing.MediaType.VIDEO_NOTE: 10 * 1024 * 1024, # 10MB
    }
    
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name='media_files',
        verbose_name='Рассылка'
    )

    media_type = models.CharField(
        max_length=20,
        choices=Mailing.MediaType.choices,
        verbose_name='Тип медиафайла'
    )

    file = models.FileField(
        upload_to=mailing_media_path,
        verbose_name='Файл',
        help_text='Загрузите медиафайл'
    )

    caption = models.CharField(
        max_length=1024,
        verbose_name='Подпись к медиа',
        blank=True,
        null=True
    )

    weight = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name='Порядок',
        help_text='Порядок отображения в группе медиафайлов'
    )

    class Meta:
        verbose_name = 'Медиафайл '
        verbose_name_plural = 'Медиафайлы'
        ordering = ['weight']
        unique_together = [('mailing', 'weight')]

    def __str__(self):
        return f"Медиафайл {self.get_media_type_display()} для {self.mailing.title}"

    def clean(self):
        if not self.file:
            raise ValidationError('Необходимо загрузить файл')

        # Проверяем тип медиафайла
        allowed_types = [
            Mailing.MediaType.PHOTO,
            Mailing.MediaType.VIDEO,
            Mailing.MediaType.DOCUMENT,
            Mailing.MediaType.AUDIO,
            Mailing.MediaType.ANIMATION,
            Mailing.MediaType.VOICE,
            Mailing.MediaType.VIDEO_NOTE
        ]
        
        if self.media_type not in allowed_types:
            raise ValidationError(
                f'Недопустимый тип медиафайла: {self.get_media_type_display()}'
            )

        # Проверяем расширение файла
        ext = os.path.splitext(self.file.name)[1][1:].lower()
        allowed_extensions = self.MEDIA_TYPE_VALIDATORS.get(self.media_type, [])
        if ext not in allowed_extensions:
            raise ValidationError(
                f'Недопустимое расширение файла для типа {self.get_media_type_display()}. '
                f'Разрешены: {", ".join(allowed_extensions)}'
            )

        # Проверяем размер файла
        max_size = self.MAX_FILE_SIZES.get(self.media_type)
        if max_size and self.file.size > max_size:
            raise ValidationError(
                f'Размер файла превышает максимально допустимый ({max_size // (1024*1024)}MB) '
                f'для типа {self.get_media_type_display()}'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        

    def delete(self, *args, **kwargs):
        # Удаляем файл при удалении записи
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class MailingInlineButton(models.Model):
    mailing = models.ForeignKey(
        'Mailing',
        on_delete=models.CASCADE,
        related_name='inline_buttons',
        verbose_name='Рассылка'
    )

    text = models.CharField(
        max_length=255,
        verbose_name='Текст кнопки'
    )

    url = models.URLField(
        verbose_name='URL ссылки',
        blank=True,
        null=True,
        help_text='Ссылка для кнопки (если это кнопка-ссылка)'
    )

    callback_data = models.CharField(
        max_length=64,
        verbose_name='Callback data',
        blank=True,
        null=True,
        help_text='Данные для callback-кнопки'
    )

    weight = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name='Порядок',
        help_text='Порядок отображения кнопки'
    )

    class Meta:
        verbose_name = 'Кнопка рассылки'
        verbose_name_plural = 'Кнопки рассылки'
        ordering = ['weight']
        unique_together = [('mailing', 'weight')]

    def __str__(self):
        return f"Кнопка '{self.text}' для {self.mailing.title}"

    def clean(self):
        if not self.url and not self.callback_data:
            raise ValidationError('Необходимо заполнить либо URL, либо callback data')
        
        if self.url and self.callback_data:
            raise ValidationError('Нельзя одновременно использовать URL и callback data')
        
        if not self.text:
            raise ValidationError('Текст кнопки обязателен')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class MailingBatch(models.Model):
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name='Рассылка'
    )

    batch_number = models.PositiveIntegerField(
        verbose_name='Номер пакета'
    )

    successful_users = models.PositiveIntegerField(
        verbose_name='Успешно отправлено',
        default=0
    )

    failed_users = models.PositiveIntegerField(
        verbose_name='Ошибки отправки',
        default=0
    )

    error_details = models.JSONField(
        verbose_name='Детали ошибок',
        null=True,
        blank=True,
        help_text='Список ошибок при отправке'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время создания'
    )

    class Meta:
        verbose_name = 'Пакет'
        verbose_name_plural = 'Пакеты'
        ordering = ['mailing', 'batch_number']
        unique_together = [('mailing', 'batch_number')]

    def __str__(self):
        return f"Пакет {self.batch_number} рассылки {self.mailing.title}"