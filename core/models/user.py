from django.contrib.auth.models import AbstractUser
from django.db import models


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
