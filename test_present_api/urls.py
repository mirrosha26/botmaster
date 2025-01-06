from django.urls import path
from .views import AvailableFiltersView, get_mailing_message

urlpatterns = [
    path('users/available-filters/', AvailableFiltersView.as_view(), name='available-filters'),
    path('get_mailing_message/', get_mailing_message, name='get_mailing_message'),
]
