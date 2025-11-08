"""Authentication-focused API endpoints."""

from django.urls import path

from ..api.views import CurrentUserView, UserTokenObtainPairView, UserTokenRefreshView

urlpatterns = [
    path('api/auth/token/', UserTokenObtainPairView.as_view(), name='auth_token_obtain_pair'),
    path('api/auth/token/refresh/', UserTokenRefreshView.as_view(), name='auth_token_refresh'),
    path('api/auth/me/', CurrentUserView.as_view(), name='auth_me'),
]
