from django.http import JsonResponse
from django.views import View

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