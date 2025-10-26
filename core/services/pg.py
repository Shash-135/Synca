from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.db.models import Avg, Count, Min, Prefetch, Q

from ..models import Bed, Booking, PG, Room


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
        return {
            "reviews": reviews,
            "average_rating": self.calculate_average_rating(reviews),
            "amenities_list": self.get_amenities(),
            "rooms": rooms,
            "lock_in_period": self.pg.lock_in_period,
            "deposit": self.pg.deposit,
        }