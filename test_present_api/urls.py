from django.urls import path
from .views import AvailableFiltersView

urlpatterns = [
    path('available-filters/', AvailableFiltersView.as_view(), name='available-filters'),
]
