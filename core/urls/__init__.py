"""Aggregate URL patterns for the core application."""

from . import auth, booking, owner, public

urlpatterns = [
    *public.urlpatterns,
    *booking.urlpatterns,
    *owner.urlpatterns,
    *auth.urlpatterns,
]
