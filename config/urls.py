from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from mailings.views import FeedbackView 

urlpatterns = [
    path('test-api/users/', include('test_present_api.urls')),
    path('', admin.site.urls),
]