from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Iterable

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Avg, Count, Min, Prefetch, Q
from django.utils import timezone
from django.utils.text import slugify

from .forms import (
    AddBedForm,
    AddRoomForm,
    BookingDatesForm,
    StudentBasicForm,
    StudentProfileForm,
)
from .models import Bed, Booking, PG, Review, Room, StudentProfile, add_months

if TYPE_CHECKING:  # pragma: no cover - static type hints only
    from .models import User as UserType

User = get_user_model()


# ---------------------------------------------------------------------------
# PG catalog and property detail helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PGFilters:
    """Value object holding filter parameters for PG catalog queries."""

    pg_type: str = ""
    area: str = ""
    room_type: str = ""
    max_price: Decimal | None = None


class PGCatalogService:
    """Encapsulates querying logic for the PG catalog."""

    def __init__(self, base_queryset: Iterable[PG] | None = None) -> None:
        self.base_queryset = base_queryset or PG.objects.all()

    def build_filters(self, data: dict[str, str]) -> PGFilters:
        """Return validated filter parameters from raw request data."""

        max_price_raw = (data.get("max_price") or "").strip()
        max_price: Decimal | None = None
        if max_price_raw:
            try:
                max_price = Decimal(max_price_raw)
            except (InvalidOperation, TypeError):
                max_price = None
        return PGFilters(
            pg_type=(data.get("pg_type") or "").strip(),
            area=(data.get("area") or "").strip(),
            room_type=(data.get("room_type") or "").strip(),
            max_price=max_price,
        )

    def get_catalog(self, filters: PGFilters):
        """Apply filters and return the PG catalog queryset."""

        queryset = self.base_queryset.annotate(
            min_price=Min("rooms__price_per_bed"),
            average_rating=Avg("reviews__rating"),
        ).prefetch_related("rooms")

        if filters.area:
            queryset = queryset.filter(area__iexact=filters.area)
        if filters.pg_type:
            queryset = queryset.filter(pg_type=filters.pg_type)
        if filters.room_type:
            queryset = queryset.filter(rooms__room_type=filters.room_type)
        if filters.max_price is not None:
            queryset = queryset.filter(rooms__price_per_bed__lte=filters.max_price)

        return queryset.distinct()

    @staticmethod
    def available_areas() -> Iterable[str]:
        return PG.objects.order_by("area").values_list("area", flat=True).distinct()


class PGDetailService:
    """Provides a rich representation of a PG and its rooms."""

    def __init__(self, pg: PG) -> None:
        self.pg = pg

    def get_rooms_with_beds(self):
        bed_bookings_prefetch = Prefetch(
            "beds",
            queryset=Bed.objects.prefetch_related(
                Prefetch(
                    "bookings",
                    queryset=Booking.objects.select_related("user").order_by("-booking_date"),
                )
            ).order_by("bed_identifier"),
        )

        rooms = (
            self.pg.rooms.annotate(
                total_beds=Count("beds"),
                available_beds=Count("beds", filter=Q(beds__is_available=True)),
            )
            .prefetch_related(bed_bookings_prefetch)
            .order_by("room_number")
        )

        for room in rooms:
            for bed in room.beds.all():
                bookings = list(bed.bookings.all())
                active_booking = None
                pending_booking = None
                for booking in bookings:
                    booking.refresh_status(persist=False)
                    if booking.status == "pending" and pending_booking is None:
                        pending_booking = booking
                    if booking.status in {"active", "upcoming"}:
                        active_booking = booking
                        break

                if not bed.is_available and active_booking:
                    bed.current_booking = active_booking
                    bed.current_occupant = active_booking.user if active_booking.user else None
                else:
                    bed.current_booking = None
                    bed.current_occupant = None

                bed.pending_booking = pending_booking if pending_booking and not bed.is_available else None

            room.roommate_beds = [
                bed
                for bed in room.beds.all()
                if getattr(bed, "current_occupant", None)
            ]

        return rooms

    def get_reviews(self):
        return self.pg.reviews.select_related("user").order_by("-created_at")

    def calculate_average_rating(self, reviews):
        return reviews.aggregate(avg_rating=Avg("rating"))["avg_rating"]

    def get_amenities(self) -> list[str]:
        if not self.pg.amenities:
            return []
        return [amenity.strip() for amenity in self.pg.amenities.split(",") if amenity.strip()]

    def build_context(self) -> dict[str, object]:
        reviews = self.get_reviews()
        rooms = self.get_rooms_with_beds()
        gallery_images = list(self.pg.images.all())
        return {
            "reviews": reviews,
            "average_rating": self.calculate_average_rating(reviews),
            "amenities_list": self.get_amenities(),
            "rooms": rooms,
            "lock_in_period": self.pg.lock_in_period,
            "deposit": self.pg.deposit,
            "primary_image": self.pg.primary_photo,
            "gallery_images": gallery_images,
        }


# ---------------------------------------------------------------------------
# Review helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewEligibility:
    can_review: bool
    reason: str | None = None


class ReviewService:
    """Handle review creation and eligibility around PG stays."""

    def __init__(self, user: "UserType"):
        self.user = user

    def user_review(self, pg: PG) -> Review | None:
        if not getattr(self.user, "is_authenticated", False):
            return None
        return Review.objects.filter(pg=pg, user=self.user).first()

    def eligibility(self, pg: PG) -> ReviewEligibility:
        if not getattr(self.user, "is_authenticated", False):
            return ReviewEligibility(False, "You must be logged in to review this property.")
        if getattr(self.user, "user_type", "") != "student":
            return ReviewEligibility(False, "Only students can review properties.")
        eligible_statuses = {"active", "completed"}
        booking_exists = (
            Booking.objects.filter(user=self.user, bed__room__pg=pg, status__in=eligible_statuses)
            .exclude(bed__isnull=True)
            .exists()
        )
        if not booking_exists:
            return ReviewEligibility(False, "You can review only after staying at this property.")
        return ReviewEligibility(True, None)

    def form(self, pg: PG, data: dict[str, Any] | None = None):
        from .forms import ReviewForm  # local import to avoid circular dependency at module import time

        return ReviewForm(data=data, instance=self.user_review(pg))

    def save(self, pg: PG, data: dict[str, Any]):
        from .forms import ReviewForm  # local import keeps dependency light-weight

        eligibility = self.eligibility(pg)
        if not eligibility.can_review:
            form = self.form(pg, data=data)
            return False, form, None, eligibility
        form = self.form(pg, data=data)
        if not form.is_valid():
            return False, form, None, eligibility
        review = form.save(commit=False)
        review.pg = pg
        review.user = self.user
        review.save()
        return True, form, review, eligibility


# ---------------------------------------------------------------------------
# Owner-facing workflows
# ---------------------------------------------------------------------------


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
        lock_in_months = bed.room.pg.lock_in_period or 0
        if lock_in_months:
            checkout_date = add_months(today, lock_in_months)
        else:
            checkout_date = today + timedelta(days=30)
        booking = Booking.objects.create(
            user=occupant,
            bed=bed,
            booking_type="Offline",
            status="active",
            check_in=today,
            check_out=checkout_date,
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


# ---------------------------------------------------------------------------
# Student-facing workflows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookingQuote:
    monthly_rent: Decimal
    security_deposit: Decimal
    total_amount: Decimal
    deposit_applicable: bool
    lock_in_period: int | None


class BookingRequestService:
    """Builds booking quotes and orchestrates booking submissions."""

    def __init__(self, user):
        self.user = user

    def build_quote(self, bed: Bed) -> BookingQuote:
        monthly_rent = bed.room.price_per_bed or Decimal("0")
        raw_deposit = bed.room.pg.deposit
        deposit_applicable = raw_deposit is not None
        security_deposit = raw_deposit if deposit_applicable else Decimal("0")
        lock_in_period = bed.room.pg.lock_in_period or None
        total_amount = monthly_rent + security_deposit
        return BookingQuote(
            monthly_rent=monthly_rent,
            security_deposit=security_deposit,
            total_amount=total_amount,
            deposit_applicable=deposit_applicable,
            lock_in_period=lock_in_period,
        )

    def create_booking(self, bed: Bed, *, check_in: date, check_out: date) -> Booking:
        if not bed.is_available:
            raise ValueError("Selected bed has already been booked.")

        booking = Booking.objects.create(
            user=self.user,
            bed=bed,
            booking_type="Online",
            status="pending",
            check_in=check_in,
            check_out=check_out,
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
                lock_in_months = getattr(booking.pg, "lock_in_period", 0) or 0
                if lock_in_months:
                    booking.check_out = add_months(booking.check_in, lock_in_months)
                else:
                    booking.check_out = booking.check_in + timedelta(days=30)
            booking.badge_class = self.STATUS_BADGE_MAP.get(booking.status, "secondary")
            booking.status_label = booking.get_status_display()
            primary_photo = getattr(booking.pg, "primary_photo", None)
            image_field = primary_photo if primary_photo else booking.pg.image
            image_url = None
            if image_field:
                try:
                    image_url = image_field.url
                except ValueError:
                    image_url = None
            booking.image_url = image_url or self.placeholder_image
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

    def update_profile(self, data, files=None) -> tuple[bool, StudentBasicForm, StudentProfileForm]:
        user_form = StudentBasicForm(data, files, instance=self.user)
        profile_form = StudentProfileForm(data, instance=self.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            remove_photo = user_form.cleaned_data.get("remove_profile_photo")
            uploaded_photo = user_form.cleaned_data.get("profile_photo")
            if remove_photo and not uploaded_photo:
                if user.profile_photo:
                    user.profile_photo.delete(save=False)
                user.profile_photo = None
                user.save(update_fields=["profile_photo"])
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
        lock_in = getattr(booking.bed.room.pg, "lock_in_period", None)
        if lock_in:
            months_label = "month" if lock_in == 1 else "months"
            form.add_error(None, f"This booking has a lock-in period of {lock_in} {months_label}; dates cannot be changed.")
            return form
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


__all__ = [
    "PGFilters",
    "PGCatalogService",
    "PGDetailService",
    "ReviewEligibility",
    "ReviewService",
    "OwnerDashboardStats",
    "BookingActionOutcome",
    "OwnerInventoryService",
    "OwnerDashboardService",
    "OfflineBookingService",
    "OwnerBookingActionService",
    "slugify_username",
    "BookingQuote",
    "BookingRequestService",
    "BookingSuccessService",
    "StudentBookingsService",
    "StudentProfileService",
    "BookingMutationService",
    "BedAvailabilityService",
]
