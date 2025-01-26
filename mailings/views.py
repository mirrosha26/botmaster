from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import MailingBatch, Mailing
from django.shortcuts import get_object_or_404

class BroadcastStatusView(APIView):
    def post(self, request):
        # Проверяем токен из заголовка
        token = request.headers.get('Authorization')
        if not token or token != settings.BROADCAST_TOKEN:
            raise AuthenticationFailed('Неверный токен авторизации')
            
        batch_number = request.data.get('batch_number')
        broadcast_id = request.data.get('broadcast_id')
        successful_users = request.data.get('successful_users', 0)
        failed_users = request.data.get('failed_users', 0)
        error_details = request.data.get('error_details', [])

        try:
            mailing = Mailing.objects.get(pk=broadcast_id)
        except Mailing.DoesNotExist:
            return Response(
                {'error': 'Рассылка не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        batch, created = MailingBatch.objects.update_or_create(
            mailing=mailing,
            batch_number=batch_number,
            defaults={
                'successful_users': successful_users,
                'failed_users': failed_users,
                'error_details': error_details
            }
        )
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)