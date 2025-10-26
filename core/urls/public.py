"""Public-facing URL patterns."""

from django.urls import path

from ..views import public

urlpatterns = [
    path("", public.SplashView.as_view(), name="splash"),
    path("home/", public.HomeView.as_view(), name="home"),
    path("about/", public.AboutView.as_view(), name="about"),
    path("contact/", public.ContactView.as_view(), name="contact"),
    path("login/", public.LoginView.as_view(), name="login"),
    path("logout/", public.LogoutView.as_view(), name="logout"),
    path("register/", public.RegisterView.as_view(), name="register"),
    path("pg/<int:pk>/", public.PGDetailView.as_view(), name="pg_detail"),
]
