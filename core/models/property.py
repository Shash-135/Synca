from django.db import models

from .user import User


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

    def __str__(self) -> str:  # pragma: no cover - simple display helper
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

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"{self.pg.pg_name} - Room {self.room_number}"

    @property
    def share_capacity(self) -> int | None:
        """Return the expected number of beds based on the room's sharing type."""

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

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        status = "Available" if self.is_available else "Occupied"
        return f"{self.room} - Bed {self.bed_identifier} ({status})"


class PGImage(models.Model):
    pg = models.ForeignKey(PG, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="pg_images/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return f"Image for {self.pg.pg_name} ({self.image.name})"
