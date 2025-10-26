"""Student booking and profile URL patterns."""

from django.urls import path

from ..views import booking

urlpatterns = [
    path("profile/", booking.StudentProfileView.as_view(), name="student_profile"),
    path("my-bookings/", booking.StudentBookingsView.as_view(), name="student_bookings"),
    path("booking/<int:bed_id>/", booking.BookingRequestView.as_view(), name="booking"),
    path("booking/success/<int:booking_id>/", booking.BookingSuccessView.as_view(), name="booking_success"),
    path(
        "booking/<int:booking_id>/dates/",
        booking.StudentBookingUpdateDatesView.as_view(),
        name="student_booking_update_dates",
    ),
    path(
        "booking/<int:booking_id>/cancel/",
        booking.StudentBookingCancelView.as_view(),
        name="student_booking_cancel",
    ),
    path(
        "api/beds/<int:bed_id>/toggle/",
        booking.BedAvailabilityToggleView.as_view(),
        name="bed_toggle_api",
    ),
]
