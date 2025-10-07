from django.urls import path
from . import views

urlpatterns = [
    path('', views.splash_view, name='splash'),
    path('home/', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('owner/dashboard/', views.owner_dashboard_view, name='owner_dashboard'),
]
