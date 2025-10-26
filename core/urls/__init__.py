"""Aggregate URL patterns for the core application."""

from . import booking, owner, public

urlpatterns = [
    *public.urlpatterns,
    *booking.urlpatterns,
    *owner.urlpatterns,
]
