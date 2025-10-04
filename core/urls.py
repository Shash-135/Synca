# core/urls.py

from django.urls import path
from . import views

# This is where you will map your URLs to your view functions
urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    # TODO: Add paths for login, logout, register, etc.
    # path('login/', views.login_view, name='login'),
]