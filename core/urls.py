from django.urls import path
from . import views

urlpatterns = [
    path('', views.splash_view, name='splash'),
    path('home/', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.student_profile_view, name='student_profile'),
    path('my-bookings/', views.student_bookings_view, name='student_bookings'),
    path('owner/dashboard/', views.owner_dashboard_view, name='owner_dashboard'),
    path('owner/bookings/offline/', views.owner_add_offline_booking_view, name='owner_add_offline_booking'),
    path('owner/bookings/<int:booking_id>/update/', views.owner_update_booking_view, name='owner_update_booking'),
    path('owner/pg/<int:pg_id>/rooms/add/', views.owner_add_room_view, name='owner_add_room'),
    path('owner/pg/<int:pg_id>/beds/add/', views.owner_add_bed_view, name='owner_add_bed'),
    path('owner/add-property/', views.add_property_view, name='add_property'),
    path('pg/<int:pg_id>/', views.pg_detail_view, name='pg_detail'),
    path('booking/<int:bed_id>/', views.booking_view, name='booking'),
    path('booking/success/<int:booking_id>/', views.booking_success_view, name='booking_success'),
    path('booking/<int:booking_id>/dates/', views.student_booking_update_dates_view, name='student_booking_update_dates'),
    path('booking/<int:booking_id>/cancel/', views.student_booking_cancel_view, name='student_booking_cancel'),
    path('api/beds/<int:bed_id>/toggle/', views.bed_toggle_api_view, name='bed_toggle_api'),
]
