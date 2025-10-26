from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .property import PG
from .user import User


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

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"Review for {self.pg.pg_name} by {self.user.username}"
