# core/admin.py

from django.contrib import admin
from .models import User, PG, Room, Bed, Booking, Review

# Register your models here to make them accessible in the Django admin.
# This is how you will build the PG Owner's management portal.

admin.site.register(User)
admin.site.register(PG)
admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(Booking)
admin.site.register(Review)