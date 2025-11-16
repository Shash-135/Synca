from __future__ import annotations

from calendar import monthrange
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("student", "Student"),
        ("owner", "Owner"),
    )
    OCCUPATION_CHOICES = (
        ("student", "Student"),
        ("working", "Working Professional"),
    )
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("non_binary", "Non-binary"),
        ("prefer_not_to_say", "Prefer not to say"),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default="student")
    age = models.PositiveIntegerField(null=True, blank=True)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)


class PG(models.Model):
    PG_TYPE_CHOICES = (
        ("boys", "Only Boys"),
        ("girls", "Only Girls"),
        ("coed", "Co-ed"),
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"user_type": "owner"},
        related_name="pgs",
    )
    pg_name = models.CharField(max_length=255)
    address = models.TextField()
    pg_type = models.CharField(max_length=10, choices=PG_TYPE_CHOICES, default="coed")
    lock_in_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Lock-in period in months (if applicable)",
    )
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deposit amount (if applicable)",
    )
    area = models.CharField(max_length=100)
    amenities = models.TextField(help_text="e.g., WiFi, AC, Food")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="pg_images/", null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.pg_name

    @property
    def amenities_list(self) -> list[str]:
        if not self.amenities:
            return []
        return [amenity.strip() for amenity in self.amenities.split(",") if amenity.strip()]

    @property
    def primary_photo(self):
        photo = self.image
        if photo:
            return photo
        first_additional = self.images.order_by("created_at", "id").first()
        return first_additional.image if first_additional else None


class Room(models.Model):
    ROOM_TYPE_CHOICES = (
        ("1-sharing", "1-Sharing"),
        ("2-sharing", "2-Sharing"),
        ("3-sharing", "3-Sharing"),
    )

    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    price_per_bed = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.pg.pg_name} - Room {self.room_number}"

    @property
    def share_capacity(self) -> int | None:
        raw_type = self.room_type or ""
        try:
            capacity_text = raw_type.split("-", 1)[0]
            capacity = int(capacity_text)
            return capacity if capacity > 0 else None
        except (ValueError, IndexError):
            return None


class Bed(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_identifier = models.CharField(max_length=20, help_text="e.g., A, B, Lower")
    is_available = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - display helper
        status = "Available" if self.is_available else "Occupied"
        return f"{self.room} - Bed {self.bed_identifier} ({status})"


class PGImage(models.Model):
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="pg_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"Image for {self.pg.pg_name} ({self.image.name})"


def add_months(start_date, months: int):
    """Return a date shifted forward by ``months`` preserving day when possible."""

    if months <= 0:
        return start_date
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, monthrange(year, month)[1])
    return start_date.replace(year=year, month=month, day=day)


class Booking(models.Model):
    BOOKING_TYPE_CHOICES = (("Online", "Online"), ("Offline", "Offline"))
    STATUS_CHOICES = (
        ("pending", "Pending Owner Approval"),
        ("upcoming", "Upcoming"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="upcoming")
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - display helper
        user_email = self.user.email if self.user else "Offline Booking"
        return f"Booking for {self.bed} by {user_email}"

    def mark_active(self) -> None:
        if self.status == "cancelled":
            return
        today = timezone.now().date()
        self.status = "active"
        if not self.check_in:
            self.check_in = today
        lock_in = self.lock_in_period_months
        if lock_in:
            self.check_out = add_months(self.check_in, lock_in)
        elif not self.check_out:
            self.check_out = self.check_in + timedelta(days=30)
        self.save(update_fields=["status", "check_in", "check_out"])

    def mark_cancelled(self) -> None:
        self.status = "cancelled"
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at"])

    def mark_pending(self) -> None:
        if self.status == "cancelled":
            return
        self.status = "pending"
        self.save(update_fields=["status"])

    def calculate_status(self, today=None) -> str:
        if self.status in {"cancelled", "pending"}:
            return self.status
        today = today or timezone.now().date()
        if self.check_in and self.check_in > today:
            return "upcoming"
        if self.check_out and self.check_out < today:
            return "completed"
        if self.check_in and self.check_in <= today and (not self.check_out or self.check_out >= today):
            return "active"
        return self.status

    def refresh_status(self, persist: bool = True) -> str:
        new_status = self.calculate_status()
        if new_status == self.status:
            return self.status
        self.status = new_status
        if persist:
            self.save(update_fields=["status"])
        return self.status

    @property
    def lock_in_period_months(self) -> int | None:
        if not self.bed_id:
            return None
        bed = getattr(self, "bed", None)
        if bed is None:
            return None
        room = getattr(bed, "room", None)
        if room is None:
            return None
        pg = getattr(room, "pg", None)
        if pg is None:
            return None
        return pg.lock_in_period or None


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
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

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"Profile for {self.user.get_full_name() or self.user.username}"


class Review(models.Model):
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"user_type": "student"},
        related_name="reviews",
    )
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"Review for {self.pg.pg_name} by {self.user.username}"


__all__ = [
    "User",
    "PG",
    "Room",
    "Bed",
    "PGImage",
    "Booking",
    "StudentProfile",
    "Review",
    "add_months",
]
