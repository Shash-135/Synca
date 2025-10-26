from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone

from ..forms import BookingDatesForm, StudentBasicForm, StudentProfileForm
<<<<<<< HEAD
from ..models.booking import Booking
from ..models.property import Bed
from ..models.profile import StudentProfile
=======
from ..models import Bed, Booking, StudentProfile
>>>>>>> 302367afdaf4f58d43b2fa3059b039e751452676

User = get_user_model()


@dataclass(frozen=True)
class BookingQuote:
    monthly_rent: Decimal
    security_deposit: Decimal
    total_amount: Decimal
    deposit_applicable: bool


class BookingRequestService:
    """Builds booking quotes and orchestrates booking submissions."""

    def __init__(self, user):
        self.user = user

    def build_quote(self, bed: Bed) -> BookingQuote:
        monthly_rent = bed.room.price_per_bed or Decimal("0")
        raw_deposit = bed.room.pg.deposit
        deposit_applicable = raw_deposit is not None
        security_deposit = raw_deposit if deposit_applicable else Decimal("0")
        total_amount = monthly_rent + security_deposit
        return BookingQuote(
            monthly_rent=monthly_rent,
            security_deposit=security_deposit,
            total_amount=total_amount,
            deposit_applicable=deposit_applicable,
        )

    def create_booking(self, bed: Bed) -> Booking:
        if not bed.is_available:
            raise ValueError("Selected bed has already been booked.")

        today = timezone.now().date()
        booking = Booking.objects.create(
            user=self.user,
            bed=bed,
            booking_type="Online",
            status="pending",
            check_in=today,
            check_out=today + timedelta(days=30),
        )
        bed.is_available = False
        bed.save(update_fields=["is_available"])
        return booking


class BookingSuccessService:
    """Enriches booking confirmation details for the success page."""

    def __init__(self, booking: Booking):
        self.booking = booking
        self._quote_service = BookingRequestService(booking.user)

    def quote(self) -> BookingQuote:
        return self._quote_service.build_quote(self.booking.bed)

    def roommates(self) -> Iterable[Booking]:
        return (
            Booking.objects
            .select_related("user", "bed")
            .filter(bed__room=self.booking.bed.room, status__in=["active", "upcoming"])
            .exclude(id=self.booking.id)
            .order_by("bed__bed_identifier")
        )

    def awaiting_owner(self) -> bool:
        return self.booking.status == "pending"


class StudentBookingsService:
    """Provides booking history grouped by status for students."""

    placeholder_image = "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800"

    STATUS_BADGE_MAP = {
        "pending": "warning",
        "active": "success",
        "upcoming": "primary",
        "completed": "secondary",
        "cancelled": "danger",
    }

    def __init__(self, user):
        self.user = user

    def bookings(self) -> list[Booking]:
        booking_qs = (
            Booking.objects
            .filter(user=self.user)
            .select_related("bed__room__pg")
            .order_by("-booking_date")
        )

        bookings: list[Booking] = []
        for booking in booking_qs:
            booking.refresh_status(persist=False)
            booking.pg = booking.bed.room.pg
            booking.room = booking.bed.room
            if not booking.check_in:
                booking.check_in = booking.booking_date.date()
            if not booking.check_out and booking.check_in:
                booking.check_out = booking.check_in + timedelta(days=30)
            booking.badge_class = self.STATUS_BADGE_MAP.get(booking.status, "secondary")
            booking.status_label = booking.get_status_display()
            booking.image_url = booking.pg.image.url if booking.pg.image else self.placeholder_image
            booking.monthly_rent = booking.room.price_per_bed or Decimal("0")
            booking.dates_form = BookingDatesForm(instance=booking)
            bookings.append(booking)
        return bookings

    def grouped_bookings(self, bookings: Iterable[Booking]) -> dict[str, list[Booking]]:
        grouped: dict[str, list[Booking]] = {
            "pending": [],
            "active": [],
            "upcoming": [],
            "completed": [],
            "cancelled": [],
        }
        for booking in bookings:
            if booking.status in grouped:
                grouped[booking.status].append(booking)
        return grouped

    def status_counts(self, bookings: Iterable[Booking]) -> dict[str, int]:
        grouped = self.grouped_bookings(bookings)
        counts = {key: len(value) for key, value in grouped.items()}
        counts["all"] = sum(counts.values())
        return counts


class StudentProfileService:
    """Handles profile forms and recent booking summaries for students."""

    RECENT_BOOKINGS_LIMIT = 3

    def __init__(self, user):
        self.user = user
        self.profile, _ = StudentProfile.objects.get_or_create(user=user)

    # Form helpers -----------------------------------------------------
    def user_form(self) -> StudentBasicForm:
        return StudentBasicForm(instance=self.user)

    def profile_form(self) -> StudentProfileForm:
        return StudentProfileForm(instance=self.profile)

    def password_form(self) -> PasswordChangeForm:
        form = PasswordChangeForm(self.user)
        self._style_password_form(form)
        return form

    def _style_password_form(self, form: PasswordChangeForm) -> None:
        for field in form.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            form_class = f"{existing_class} form-control".strip()
            field.widget.attrs["class"] = form_class

    # Update handlers --------------------------------------------------
    def update_profile(self, data) -> tuple[bool, StudentBasicForm, StudentProfileForm]:
        user_form = StudentBasicForm(data, instance=self.user)
        profile_form = StudentProfileForm(data, instance=self.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return True, user_form, profile_form
        return False, user_form, profile_form

    def update_password(self, data) -> tuple[bool, PasswordChangeForm, Any]:
        form = PasswordChangeForm(self.user, data)
        self._style_password_form(form)
        if form.is_valid():
            user = form.save()
            return True, form, user
        return False, form, None

    # Query helpers ----------------------------------------------------
    def recent_bookings(self) -> list[Booking]:
        bookings = (
            Booking.objects
            .filter(user=self.user)
            .select_related("bed__room__pg")
            .order_by("-booking_date")[: self.RECENT_BOOKINGS_LIMIT]
        )
        badge_map = {
            "active": "success",
            "upcoming": "primary",
            "completed": "secondary",
            "cancelled": "danger",
            "pending": "warning",
        }
        for booking in bookings:
            booking.refresh_status(persist=False)
            booking.badge_class = badge_map.get(booking.status, "secondary")
        return list(bookings)


class BookingMutationService:
    """Updates or cancels student bookings with validation."""

    def __init__(self, user):
        self.user = user

    def update_dates(self, booking: Booking, data) -> BookingDatesForm:
        form = BookingDatesForm(data, instance=booking)
        if form.is_valid():
            updated_booking = form.save()
            updated_booking.refresh_status()
        return form

    def cancel_booking(self, booking: Booking) -> None:
        if booking.status == "cancelled":
            return
        booking.mark_cancelled()
        if booking.bed:
            booking.bed.is_available = True
            booking.bed.save(update_fields=["is_available"])


class BedAvailabilityService:
    """Toggles bed availability on behalf of an owner."""

    def __init__(self, owner):
        self.owner = owner

    def toggle(self, bed: Bed, *, is_available: bool) -> None:
        bed.is_available = is_available
        bed.save(update_fields=["is_available"])
        if not is_available:
            return
        affected_bookings = (
            Booking.objects
            .select_related("user")
            .filter(bed=bed, status__in=["active", "upcoming", "pending"])
        )
        for booking in affected_bookings:
            if booking.status != "cancelled":
                booking.mark_cancelled()
