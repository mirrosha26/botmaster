from operator import attrgetter
from django.conf import settings

def process_inline_buttons(inline_buttons):
    """
    Обработка инлайн-кнопок в удобном формате.
    """
    return [
        {
            "text": button.text,
            **({"url": button.url} if button.url else {"callback_data": button.callback_data}),
        }
        for button in inline_buttons
    ]

def create_text_message(mailing):
    """
    Создает словарь с параметрами текстового сообщения на основе объекта рассылки.
    """
    inline_buttons = mailing.inline_buttons.all()

    message = {
        "type": "text",
        "text": mailing.text,
        "parse_mode": mailing.parse_mode if mailing.parse_mode != 'NONE' else None,
        "disable_web_page_preview": mailing.disable_web_page_preview or None,
        "disable_notification": mailing.disable_notification or None,
        "protect_content": mailing.protect_content or None,
        "delay_after": 0,
    }

    if inline_buttons.exists():
        message["inline_buttons"] = process_inline_buttons(inline_buttons)

    return message



def prepare_media_messages(media_files):
    if not media_files:
        return []
    
    sorted_files = sorted(media_files, key=attrgetter('weight'))
    
    MEDIA_GROUP_TYPES = {'photo', 'video', 'document', 'audio'}
    SINGLE_TYPES = {'voice', 'video_note', 'animation'}
    
    messages = []
    current_group = []
    current_weight = None
    max_group_size = 10  # Максимальный размер медиа группы в Telegram
    
    for media in sorted_files:        
        base_params = {
            "delay_after": 0
        }
        
        if media.media_type in MEDIA_GROUP_TYPES:
            # Проверяем, нужно ли начать новую группу
            start_new_group = (
                # Если группа пустая - начинаем новую
                not current_group or
                # Если вес изменился - начинаем новую
                current_weight != media.weight or
                # Если достигли максимального размера группы - начинаем новую
                len(current_group) >= max_group_size
            )
            
            if start_new_group and current_group:
                messages.append({
                    "type": "media_group",
                    "media": current_group,
                    **base_params
                })
                current_group = []
            
            media_item = {
                "type": media.media_type,
                "media": media.telegram_file_id if media.telegram_file_id else f"{settings.URL}/media/{media.file}"
            }
            if media.caption:
                media_item["caption"] = media.caption
                
            current_group.append(media_item)
            current_weight = media.weight
            
        elif media.media_type in SINGLE_TYPES:
            # Закрываем текущую группу если есть
            if current_group:
                messages.append({
                    "type": "media_group",
                    "media": current_group,
                    **base_params
                })
                current_group = []
                current_weight = None
            
            messages.append({
                "type": media.media_type,
                "media": media.telegram_file_id if media.telegram_file_id else media.file.path,
                **base_params
            })
            
            if media.caption:
                messages.append({
                    "type": "text",
                    "text": media.caption,
                    **base_params
                })
    
    # Не забываем про последнюю группу
    if current_group:
        messages.append({
            "type": "media_group",
            "media": current_group,
            **base_params
        })
    
    # Объединяем одиночные медиа в группы
    final_messages = []
    current_group = []
    
    for message in messages:
        if message["type"] == "media_group":
            # Если текущая группа не пуста и суммарный размер не превысит максимум
            if current_group and len(current_group["media"]) + len(message["media"]) <= max_group_size:
                current_group["media"].extend(message["media"])
            else:
                # Если есть текущая группа, добавляем её в финальный список
                if current_group:
                    final_messages.append(current_group)
                # Начинаем новую группу
                current_group = message
        else:
            # Если встретили не медиа группу, сохраняем текущую группу и добавляем сообщение
            if current_group:
                final_messages.append(current_group)
                current_group = None
            final_messages.append(message)
    

    if current_group:
        final_messages.append(current_group)
    
    return final_messages