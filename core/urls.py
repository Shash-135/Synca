from django.urls import path
from . import views

urlpatterns = [
    path('', views.SplashView.as_view(), name='splash'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('my-bookings/', views.StudentBookingsView.as_view(), name='student_bookings'),
    path('owner/dashboard/', views.OwnerDashboardView.as_view(), name='owner_dashboard'),
    path('owner/bookings/offline/', views.OwnerOfflineBookingView.as_view(), name='owner_add_offline_booking'),
    path('owner/bookings/<int:booking_id>/decision/', views.OwnerBookingDecisionView.as_view(), name='owner_booking_decision'),
    path('owner/pg/<int:pg_id>/rooms/add/', views.OwnerRoomCreateView.as_view(), name='owner_add_room'),
    path('owner/pg/<int:pg_id>/beds/add/', views.OwnerBedCreateView.as_view(), name='owner_add_bed'),
    path('owner/add-property/', views.OwnerPropertyCreateView.as_view(), name='add_property'),
    path('pg/<int:pk>/', views.PGDetailView.as_view(), name='pg_detail'),
    path('booking/<int:bed_id>/', views.BookingRequestView.as_view(), name='booking'),
    path('booking/success/<int:booking_id>/', views.BookingSuccessView.as_view(), name='booking_success'),
    path('booking/<int:booking_id>/dates/', views.StudentBookingUpdateDatesView.as_view(), name='student_booking_update_dates'),
    path('booking/<int:booking_id>/cancel/', views.StudentBookingCancelView.as_view(), name='student_booking_cancel'),
    path('api/beds/<int:bed_id>/toggle/', views.BedAvailabilityToggleView.as_view(), name='bed_toggle_api'),
]
