from django.urls import path
from . import views

urlpatterns = [
    path('status', views.BroadcastStatusView.as_view(), name='broadcast-status'),
]
