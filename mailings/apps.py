from django.apps import AppConfig
import threading


class MailingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailings'
    verbose_name = 'Сообщения'

    def ready(self):
        from mailings.management.commands.check_mailings import check_mailings_daemon
        
        # Запускаем проверку рассылок в отдельном потоке
        mailing_thread = threading.Thread(target=check_mailings_daemon, daemon=True)
        mailing_thread.start()
