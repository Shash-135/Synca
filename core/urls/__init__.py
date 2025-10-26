"""Aggregate URL patterns for the core application."""

from . import booking, owner, public

<<<<<<< HEAD
=======
app_name = "core"

>>>>>>> 302367afdaf4f58d43b2fa3059b039e751452676
urlpatterns = [
    *public.urlpatterns,
    *booking.urlpatterns,
    *owner.urlpatterns,
]
