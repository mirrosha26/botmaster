from django.core.management.base import BaseCommand
from django.utils import timezone
from mailings.models import Mailing
from mailings.api import get_filtered_users
from mailings.telegram_utils import create_text_message, prepare_media_messages
from django.conf import settings
import time
import threading
import requests


def get_mailing_data(mailing):
    messages = []

    if mailing.media_files.exists():
        media_files = mailing.media_files.all()
        media_messages = prepare_media_messages(media_files)
        messages.extend(media_messages)

    if mailing.text and mailing.text.strip():
        messages.append(create_text_message(mailing))

    data = {
        'messages': messages,
        'user_ids': [],
        'delay_between_users': 0
    }
    return data

def check_mailings_daemon():
    while True:
        try:
            if getattr(settings, 'ENABLE_MAILING_CHECK', False):
                pending_mailings = Mailing.objects.filter(
                    scheduled_at__lte=timezone.now(),
                    status=Mailing.Status.PENDING
                )
                print(f"[{timezone.now()}] Проверка рассылок:")
                print(f"Найдено {pending_mailings.count()} рассылок для отправки")
                
                for mailing in pending_mailings:
                    print(f"[{timezone.now()}] Обработка рассылки: {mailing.title} (ID: {mailing.id})")
                    print(f"Запланировано на: {mailing.scheduled_at}")
                    
                    mailing.status = Mailing.Status.PROCESSING
                    mailing.save()
                    filters = mailing.group_filters or {}
                    
                    page = 1
                    limit = 100
                    total_users = 0
                    
                    mailing_data = get_mailing_data(mailing)
                    
                    total_count = get_filtered_users(filters, page=1, limit=1).get('count', 0)
                    total_batches = (total_count + limit - 1) // limit
                    
                    while True:
                        users_data = get_filtered_users(filters, page=page, limit=limit)
                        users = users_data.get('users', [])
                        
                        if not users:
                            break
                            
                        total_users += len(users)
                        print(f"Получено {len(users)} пользователей (страница {page})")
                        
                        broadcast_data = {
                            'messages': mailing_data['messages'],
                            'user_ids': users,
                            'delay_between_users': 0, 
                            'batch_number': page,
                            'total_batches': total_batches,
                            'broadcast_id': str(mailing.pk)
                        }
                        print(broadcast_data)

                        response = requests.post(f'{settings.BROADCAST_URL}/broadcast', json=broadcast_data)
                        print(f"Отправка batch {page}/{total_batches}, статус: {response.status_code}")
                        page += 1
                    
                    print(f"Всего получено пользователей: {total_users}")
                    
                    if total_users > 0:
                        mailing.status = Mailing.Status.COMPLETED
                        mailing.save()

                print(f"[{timezone.now()}] Проверка завершена")
                print("-" * 50)
            else:
                print(f"[{timezone.now()}] Отслеживание рассылок отключено")

            time.sleep(60)
            
        except Exception as e:
            print(f'[{timezone.now()}] Ошибка: {str(e)}')
            time.sleep(60)

class Command(BaseCommand):
    help = 'Проверяет и обрабатывает рассылки, время отправки которых наступило'

    def handle(self, *args, **kwargs):
        try:
            check_mailings_daemon()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Планировщик остановлен'))