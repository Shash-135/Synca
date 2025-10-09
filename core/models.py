from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('owner', 'Owner'),
    )
    OCCUPATION_CHOICES = (
        ('student', 'Student'),
        ('working', 'Working Professional'),
    )
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('non_binary', 'Non-binary'),
        ('prefer_not_to_say', 'Prefer not to say'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    age = models.PositiveIntegerField(null=True, blank=True)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)

class PG(models.Model):
    PG_TYPE_CHOICES = (
        ('boys', 'Only Boys'),
        ('girls', 'Only Girls'),
        ('coed', 'Co-ed'),
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'owner'}, related_name='pgs')
    pg_name = models.CharField(max_length=255)
    address = models.TextField()
    pg_type = models.CharField(max_length=10, choices=PG_TYPE_CHOICES, default='coed')
    lock_in_period = models.PositiveIntegerField(
        null=True, blank=True, help_text="Lock-in period in months (if applicable)"
    )
    deposit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Deposit amount (if applicable)"
    )
    area = models.CharField(max_length=100)
    amenities = models.TextField(help_text="e.g., WiFi, AC, Food")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='pg_images/', null=True, blank=True)

    def __str__(self):
        return self.pg_name

    @property
    def amenities_list(self):
        if not self.amenities:
            return []
        return [amenity.strip() for amenity in self.amenities.split(',') if amenity.strip()]

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
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='bookings')
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='upcoming')
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        user_email = self.user.email if self.user else "Offline Booking"
        return f"Booking for {self.bed} by {user_email}"

    def mark_active(self):
        today = timezone.now().date()
        self.status = 'active'
        if not self.check_in:
            self.check_in = today
        if not self.check_out:
            self.check_out = self.check_in + timedelta(days=30)
        self.save(update_fields=['status', 'check_in', 'check_out'])

    def mark_cancelled(self):
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'cancelled_at'])

    def refresh_status(self):
        if self.status in {'cancelled'}:
            return
        today = timezone.now().date()
        if self.check_in and self.check_in > today:
            new_status = 'upcoming'
        elif self.check_out and self.check_out < today:
            new_status = 'completed'
        else:
            new_status = 'active'
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    college = models.CharField(max_length=255, blank=True)
    course = models.CharField(max_length=255, blank=True)
    academic_year = models.CharField(max_length=100, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.get_full_name() or self.user.username}"

class Review(models.Model):
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.pg.pg_name} by {self.user.username}"