from calendar import monthrange
from datetime import timedelta

from django.db import models
from django.utils import timezone

from .property import Bed
from .user import User


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

    def __str__(self) -> str:  # pragma: no cover - simple display helper
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


def add_months(start_date, months: int):
    """Return a date shifted forward by ``months`` preserving day when possible."""

    if months <= 0:
        return start_date
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, monthrange(year, month)[1])
    return start_date.replace(year=year, month=month, day=day)
