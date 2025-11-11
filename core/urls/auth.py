"""Authentication-focused API endpoints."""

from django.urls import path

from ..api.views import CurrentUserView

urlpatterns = [
    path('api/auth/me/', CurrentUserView.as_view(), name='auth_me'),
]
