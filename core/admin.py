from django.contrib import admin
from .models import User, PG, Room, Bed, Booking, Review

admin.site.register(User)
admin.site.register(PG)
admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(Booking)
admin.site.register(Review)
