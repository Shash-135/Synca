"""Owner-focused URL patterns."""

from django.urls import path

from ..views import owner

urlpatterns = [
    path("owner/dashboard/", owner.OwnerDashboardView.as_view(), name="owner_dashboard"),
    path(
        "owner/bookings/offline/",
        owner.OwnerOfflineBookingView.as_view(),
        name="owner_add_offline_booking",
    ),
    path(
        "owner/bookings/<int:booking_id>/decision/",
        owner.OwnerBookingDecisionView.as_view(),
        name="owner_booking_decision",
    ),
    path("owner/pg/<int:pg_id>/rooms/add/", owner.OwnerRoomCreateView.as_view(), name="owner_add_room"),
    path("owner/pg/<int:pg_id>/beds/add/", owner.OwnerBedCreateView.as_view(), name="owner_add_bed"),
    path("owner/pg/<int:pg_id>/edit/", owner.OwnerPropertyUpdateView.as_view(), name="owner_edit_property"),
    path("owner/add-property/", owner.OwnerPropertyCreateView.as_view(), name="add_property"),
]
