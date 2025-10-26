from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from ..forms import AddBedForm, AddRoomForm
from ..models import Bed, Booking, PG

User = get_user_model()


@dataclass(frozen=True)
class OwnerDashboardStats:
    total_pgs: int
    total_beds: int
    occupied_beds: int
    occupancy_rate: float


@dataclass(frozen=True)
class BookingActionOutcome:
    level: str
    message: str


class OwnerInventoryService:
    """Manage room and bed creation helpers for an owner's PGs."""

    def __init__(self, owner):
        self.owner = owner

    def room_form(self, pg: PG, data: Any | None = None) -> AddRoomForm:
        return AddRoomForm(data, pg=pg)

    def bed_form(self, pg: PG, data: Any | None = None) -> AddBedForm:
        return AddBedForm(data, pg=pg)

    def create_room(self, pg: PG, data: Any) -> tuple[bool, AddRoomForm, Any]:
        form = self.room_form(pg, data)
        if form.is_valid():
            room = form.save()
            return True, form, room
        return False, form, None

    def create_bed(self, pg: PG, data: Any) -> tuple[bool, AddBedForm, Any]:
        form = self.bed_form(pg, data)
        if form.is_valid():
            bed = form.save()
            return True, form, bed
        return False, form, None


class OwnerDashboardService:
    """Aggregate data required for the owner dashboard."""

    STATUS_BADGE_MAP = {
        "active": "bg-success-subtle text-success",
        "upcoming": "bg-primary-subtle text-primary",
        "completed": "bg-secondary-subtle text-secondary",
        "cancelled": "bg-secondary-subtle text-secondary",
        "pending": "bg-warning-subtle text-warning",
    }

    def __init__(self, owner, inventory_service: OwnerInventoryService | None = None):
        self.owner = owner
        self.inventory_service = inventory_service or OwnerInventoryService(owner)

    def properties(self) -> Iterable[PG]:
        queryset = (
            PG.objects.filter(owner=self.owner)
            .annotate(
                room_count=Count("rooms", distinct=True),
                total_beds=Count("rooms__beds", distinct=True),
                occupied_beds=Count(
                    "rooms__beds",
                    filter=Q(rooms__beds__is_available=False),
                    distinct=True,
                ),
                available_beds=Count(
                    "rooms__beds",
                    filter=Q(rooms__beds__is_available=True),
                    distinct=True,
                ),
            )
            .prefetch_related("rooms__beds")
        )
        pgs = list(queryset)
        for pg in pgs:
            pg.room_form = self.inventory_service.room_form(pg)
            pg.bed_form = self.inventory_service.bed_form(pg)
        return pgs

    def bookings(self) -> list[Booking]:
        booking_qs = (
            Booking.objects.filter(bed__room__pg__owner=self.owner)
            .select_related("bed__room__pg", "user")
            .order_by("-booking_date")
        )
        bookings: list[Booking] = []
        for booking in booking_qs:
            booking.refresh_status(persist=False)
            booking.status_label = booking.get_status_display()
            booking.status_badge_class = self.STATUS_BADGE_MAP.get(booking.status, "bg-light text-muted")
            booking.card_state = "booking-cancelled" if booking.status == "cancelled" else ""
            booking.can_approve = booking.status == "pending"
            booking.can_cancel = booking.status in {"pending", "active", "upcoming"}
            bookings.append(booking)
        return bookings

    def stats(self, properties: Iterable[PG]) -> OwnerDashboardStats:
        pgs = list(properties)
        total_pgs = len(pgs)
        total_beds = sum(pg.total_beds for pg in pgs)
        occupied_beds = sum(pg.occupied_beds for pg in pgs)
        occupancy_rate = round((occupied_beds / total_beds) * 100, 2) if total_beds else 0.0
        return OwnerDashboardStats(
            total_pgs=total_pgs,
            total_beds=total_beds,
            occupied_beds=occupied_beds,
            occupancy_rate=occupancy_rate,
        )


class OfflineBookingService:
    """Creates offline bookings on behalf of property owners."""

    def __init__(self, owner):
        self.owner = owner

    def ensure_bed_available(self, bed: Bed) -> bool:
        bed.refresh_from_db(fields=["is_available"])
        return bed.is_available

    def resolve_or_create_occupant(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        age: int | None,
        gender: str | None,
        occupation: str | None,
        contact: str | None,
    ) -> Any:
        occupant = User.objects.filter(email=email).first()
        if occupant is None:
            base_username = slugify_username(first_name, last_name, email)
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            occupant = User(username=username, email=email or "")
            occupant.user_type = "student"
            occupant.set_unusable_password()

        occupant.first_name = first_name
        occupant.last_name = last_name
        occupant.user_type = "student"
        occupant.age = age
        occupant.gender = gender
        occupant.occupation = occupation
        occupant.contact_number = contact or ""
        occupant.save()
        return occupant

    def create_booking(self, bed: Bed, occupant: Any) -> Booking:
        today: date = timezone.now().date()
        booking = Booking.objects.create(
            user=occupant,
            bed=bed,
            booking_type="Offline",
            status="active",
            check_in=today,
            check_out=today + timedelta(days=30),
        )
        bed.is_available = False
        bed.save(update_fields=["is_available"])
        return booking


class OwnerBookingActionService:
    """Approve or cancel bookings while enforcing ownership rules."""

    def __init__(self, owner):
        self.owner = owner

    def _owns_booking(self, booking: Booking) -> bool:
        bed = booking.bed
        return bool(bed and bed.room.pg.owner_id == self.owner.id)

    def approve(self, booking: Booking) -> BookingActionOutcome:
        if not self._owns_booking(booking):
            raise PermissionError("Cannot modify bookings for another owner.")
        if booking.status != "pending":
            return BookingActionOutcome("info", "This booking is no longer awaiting approval.")
        booking.mark_active()
        if booking.bed:
            booking.bed.is_available = False
            booking.bed.save(update_fields=["is_available"])
        return BookingActionOutcome("success", "Booking approved and activated.")

    def cancel(self, booking: Booking) -> BookingActionOutcome:
        if not self._owns_booking(booking):
            raise PermissionError("Cannot modify bookings for another owner.")
        if booking.status == "cancelled":
            return BookingActionOutcome("info", "This booking is already cancelled.")
        booking.mark_cancelled()
        if booking.bed:
            booking.bed.is_available = True
            booking.bed.save(update_fields=["is_available"])
        return BookingActionOutcome("success", "Booking request cancelled.")


def slugify_username(first_name: str, last_name: str, email: str | None) -> str:
    raw = " ".join(part for part in (first_name, last_name) if part)
    base = slugify(raw) if raw else ""
    if not base and email:
        base = slugify(email.split("@")[0])
    return base or "tenant"
