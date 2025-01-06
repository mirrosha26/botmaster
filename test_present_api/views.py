from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import BadRequest
from mailings.models import Mailing
from .utils import create_text_message, prepare_media_messages

class AvailableFiltersView(View):
    def get(self, request, *args, **kwargs):
        filters = [
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

        return JsonResponse({"data": filters})


def get_mailing_message(request):
    mailing_id = request.GET.get('id')
    
    if not mailing_id:
        return JsonResponse({"messages": []})

    try:
        mailing_id = int(mailing_id)
    except ValueError:
        raise BadRequest('Invalid id parameter: must be an integer')

    mailing = get_object_or_404(Mailing, id=mailing_id)
    messages = []

    if mailing.media_files.exists():
        media_files = mailing.media_files.all()
        media_messages = prepare_media_messages(media_files)
        messages.extend(media_messages)

    # Проверяем наличие текста
    if mailing.text and mailing.text.strip():
        messages.append(create_text_message(mailing))

    data = {
        'messages': messages,
        "user_ids": [123456789, 987654321],
        "delay_between_users": 0
    }
    return JsonResponse(data)