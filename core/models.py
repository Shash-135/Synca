# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    USER_TYPE_CHOICES = (('student', 'Student'), ('owner', 'Owner'))
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')

class PG(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'owner'}, related_name='pgs')
    pg_name = models.CharField(max_length=255)
    address = models.TextField()
    area = models.CharField(max_length=100)
    amenities = models.TextField(help_text="e.g., WiFi, AC, Food")

    def __str__(self):
        return self.pg_name

class Room(models.Model):
    ROOM_TYPE_CHOICES = (('1-sharing', '1-Sharing'), ('2-sharing', '2-Sharing'), ('3-sharing', '3-Sharing'))
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    price_per_bed = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.pg.pg_name} - Room {self.room_number}"

class Bed(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    bed_identifier = models.CharField(max_length=20, help_text="e.g., A, B, Lower")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        status = "Available" if self.is_available else "Occupied"
        return f"{self.room} - Bed {self.bed_identifier} ({status})"

class Booking(models.Model):
    BOOKING_TYPE_CHOICES = (('Online', 'Online'), ('Offline', 'Offline'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='bookings')
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES)
    booking_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_email = self.user.email if self.user else "Offline Booking"
        return f"Booking for {self.bed} by {user_email}"

class Review(models.Model):
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.pg.pg_name} by {self.user.username}"