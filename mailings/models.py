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
        COMPLETED = 'completed', 'Отправлено'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменено'

    class ContentType(models.TextChoices):
        TEXT = 'text', 'Текст'
        PHOTO = 'photo', 'Фото'
        VIDEO = 'video', 'Видео'
        DOCUMENT = 'document', 'Документ'
        AUDIO = 'audio', 'Аудио'
        VOICE = 'voice', 'Голосовое сообщение'
        ANIMATION = 'animation', 'Анимация (GIF)'
        VIDEO_NOTE = 'video_note', 'Видео-кружок'
        MEDIA_GROUP = 'media_group', 'Группа медиафайлов'

    class MediaType(models.TextChoices):
        PHOTO = 'photo', 'Фото'
        VIDEO = 'video', 'Видео'
        DOCUMENT = 'document', 'Документ'
        AUDIO = 'audio', 'Аудио'
        VOICE = 'voice', 'Голосовое сообщение'
        ANIMATION = 'animation', 'Анимация (GIF)'
        VIDEO_NOTE = 'video_note', 'Видео-кружок'
        MEDIA_GROUP = 'media_group', 'Группа медиафайлов'

    class ParseMode(models.TextChoices):
        NONE = 'none', 'Без форматирования'
        MARKDOWN = 'markdown', 'Markdown'
        MARKDOWN_V2 = 'markdown_v2', 'Markdown V2'
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

    inline_keyboard = models.JSONField(
        verbose_name='Кнопки',
        blank=True,
        null=True,
        help_text='JSON с конфигурацией кнопок'
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

    def clean(self):
        if self.content_type == self.ContentType.TEXT and not self.text:
            raise ValidationError('Текст сообщения обязателен для текстового контента')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class MailingMedia(models.Model):
    """Модель для хранения медиафайлов рассылки"""
    
    # Определяем допустимые расширения файлов для каждого типа медиа
    MEDIA_TYPE_VALIDATORS = {
        Mailing.ContentType.PHOTO: ['jpg', 'jpeg', 'png', 'webp'],
        Mailing.ContentType.VIDEO: ['mp4', 'avi', 'mov', 'webm'],
        Mailing.ContentType.DOCUMENT: ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'zip', 'rar'],
        Mailing.ContentType.AUDIO: ['mp3', 'wav', 'ogg'],
        Mailing.ContentType.VOICE: ['ogg', 'mp3', 'wav'],
        Mailing.ContentType.ANIMATION: ['gif'],
        Mailing.ContentType.VIDEO_NOTE: ['mp4']
    }

    # Максимальные размеры файлов (в байтах)
    MAX_FILE_SIZES = {
        Mailing.ContentType.PHOTO: 10 * 1024 * 1024,  # 10MB
        Mailing.ContentType.VIDEO: 50 * 1024 * 1024,  # 50MB
        Mailing.ContentType.DOCUMENT: 20 * 1024 * 1024,  # 20MB
        Mailing.ContentType.AUDIO: 20 * 1024 * 1024,  # 20MB
        Mailing.ContentType.VOICE: 10 * 1024 * 1024,  # 10MB
        Mailing.ContentType.ANIMATION: 10 * 1024 * 1024,  # 10MB
        Mailing.ContentType.VIDEO_NOTE: 10 * 1024 * 1024,  # 10MB
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
        verbose_name = 'Медиафайл рассылки'
        verbose_name_plural = 'Медиафайлы рассылки'
        ordering = ['weight']
        unique_together = [('mailing', 'weight')]

    def __str__(self):
        return f"Медиафайл {self.get_media_type_display()} для {self.mailing.title}"

    def clean(self):
        if not self.file:
            raise ValidationError('Необходимо загрузить файл')

        # Проверяем тип медиафайла
        allowed_types = [
            Mailing.ContentType.PHOTO,
            Mailing.ContentType.VIDEO,
            Mailing.ContentType.DOCUMENT,
            Mailing.ContentType.AUDIO,
            Mailing.ContentType.ANIMATION,
            Mailing.ContentType.VOICE,
            Mailing.ContentType.VIDEO_NOTE
        ]
        
        if self.media_type not in allowed_types:
            raise ValidationError(f'Недопустимый тип медиафайла: {self.get_media_type_display()}')

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


class Poll(models.Model):
    """Модель для хранения опросов к рассылке"""
    mailing = models.ForeignKey(
        'Mailing',
        on_delete=models.CASCADE,
        related_name='polls',
        verbose_name='Рассылка'
    )

    text = models.CharField(
        max_length=255,
        verbose_name='Вариант'
    )

    weight = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name='Порядок',
        help_text='Порядок отображения варианта'
    )

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответа в опросе'
        ordering = ['weight']
        unique_together = [('mailing', 'weight')]

    def __str__(self):
        return f"Опрос {self.weight} для {self.mailing.title}"

    def clean(self):
        if not self.text:
            raise ValidationError('Текст варианта обязателен')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)