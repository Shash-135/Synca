# synca_project/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This line sends any request that isn't for '/admin/' to your core app's urls.py
    path('', include('core.urls')),
]