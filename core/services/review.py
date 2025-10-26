from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model

from ..forms import ReviewForm
from ..models.booking import Booking
from ..models.property import PG
from ..models.review import Review

User = get_user_model()

if TYPE_CHECKING:  # pragma: no cover - used for static analysis only
    from ..models.user import User as UserType


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

    def form(self, pg: PG, data: dict[str, Any] | None = None) -> ReviewForm:
        return ReviewForm(data=data, instance=self.user_review(pg))

    def save(self, pg: PG, data: dict[str, Any]) -> tuple[bool, ReviewForm, Review | None, ReviewEligibility]:
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
