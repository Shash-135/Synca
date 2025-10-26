"""Aggregate URL patterns for the core application."""

from . import booking, owner, public

app_name = "core"

urlpatterns = [
    *public.urlpatterns,
    *booking.urlpatterns,
    *owner.urlpatterns,
]
