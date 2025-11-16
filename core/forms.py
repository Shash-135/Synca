from __future__ import annotations

from string import ascii_uppercase

from django import forms
from django.core.exceptions import ValidationError

from PIL import Image, UnidentifiedImageError

from .models import Bed, Booking, PG, PGImage, Review, Room, StudentProfile, User, add_months

AMENITY_CHOICES = [
    ("WiFi", "WiFi"),
    ("AC", "Air Conditioning"),
    ("Meals", "Meals Included"),
    ("Laundry", "Laundry"),
    ("Security", "24/7 Security"),
    ("Parking", "Parking"),
    ("Gym", "Gym"),
    ("Power Backup", "Power Backup"),
    ("Refrigerator", "Refrigerator"),
]


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)
    gender = forms.ChoiceField(
        label="Gender",
        required=False,
        choices=[("", "Select gender")] + list(User.GENDER_CHOICES),
        widget=forms.Select,
    )
    profile_photo = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "age",
            "gender",
            "occupation",
            "contact_number",
            "user_type",
            "profile_photo",
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def clean_contact_number(self):
        contact = (self.cleaned_data.get("contact_number") or "").strip()
        if contact:
            digits_only = "".join(ch for ch in contact if ch.isdigit())
            if len(digits_only) != 10:
                raise forms.ValidationError("Contact number must contain exactly 10 digits.")
            contact = digits_only
        return contact

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.gender = self.cleaned_data.get("gender") or None
        user.contact_number = self.cleaned_data.get("contact_number")
        profile_photo = self.cleaned_data.get("profile_photo")
        if profile_photo:
            user.profile_photo = profile_photo
        if commit:
            user.save()
        return user


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if not files:
            return []
        return files.getlist(name)


class MultipleImageField(forms.FileField):
    widget = MultiFileInput

    def __init__(self, *args, allowed_formats=None, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)
        self.allowed_formats = {fmt.upper() for fmt in (allowed_formats or {"JPEG", "JPG", "PNG", "WEBP"})}

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        errors = []

        for uploaded in data:
            if not uploaded:
                continue
            if not hasattr(uploaded, "read"):
                errors.append(ValidationError("No file was submitted. Check the encoding type on the form."))
                continue
            try:
                uploaded.seek(0)
                with Image.open(uploaded) as image:
                    image.verify()
                    image_format = (image.format or "").upper()
                    if image_format not in self.allowed_formats:
                        errors.append(
                            ValidationError(
                                f"Unsupported image type for {uploaded.name}. Please upload JPG, JPEG, PNG, or WEBP files."
                            )
                        )
                        continue
            except (UnidentifiedImageError, OSError):
                errors.append(ValidationError(f"{uploaded.name} is not a valid image file."))
                continue
            finally:
                try:
                    uploaded.seek(0)
                except Exception:  # pragma: no cover - defensive seek reset
                    pass

            cleaned_files.append(uploaded)

        if errors:
            raise ValidationError(errors)

        return cleaned_files


class OfflineBookingForm(forms.Form):
    bed = forms.ModelChoiceField(queryset=Bed.objects.none(), label="Select Bed")
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    age = forms.IntegerField(required=False, min_value=0)
    gender = forms.ChoiceField(
        required=False,
        choices=[("", "Select gender")] + list(User.GENDER_CHOICES),
    )
    occupation = forms.ChoiceField(
        required=False,
        choices=[("", "Select occupation")] + list(User.OCCUPATION_CHOICES),
    )
    contact_number = forms.CharField(required=False, max_length=15)

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is None:
            raise ValueError("OfflineBookingForm requires an owner instance")
        self.owner = owner
        available_beds = (
            Bed.objects.filter(room__pg__owner=owner, is_available=True)
            .select_related("room__pg")
            .order_by("room__pg__pg_name", "room__room_number", "bed_identifier")
        )
        self.fields["bed"].queryset = available_beds
        self.fields["bed"].label_from_instance = (
            lambda bed: f"{bed.room.pg.pg_name} · Room {bed.room.room_number} · Bed {bed.bed_identifier}"
        )
        widget_classes = {
            "bed": "form-select",
            "first_name": "form-control",
            "last_name": "form-control",
            "email": "form-control",
            "age": "form-control",
            "gender": "form-select",
            "occupation": "form-select",
            "contact_number": "form-control",
        }
        for field_name, css_class in widget_classes.items():
            field = self.fields.get(field_name)
            if field:
                existing_class = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing_class} {css_class}".strip()

        self.fields["first_name"].widget.attrs.update(
            {"placeholder": "Tenant first name", "minlength": 2, "autocomplete": "given-name"}
        )
        self.fields["last_name"].widget.attrs.update(
            {"placeholder": "Tenant last name", "minlength": 2, "autocomplete": "family-name"}
        )
        self.fields["email"].widget.attrs.update(
            {"placeholder": "tenant@example.com", "autocomplete": "email"}
        )
        self.fields["age"].widget.attrs.update({"min": 0, "max": 120})
        self.fields["contact_number"].widget.attrs.update(
            {
                "placeholder": "e.g., +91 98765 43210",
                "pattern": r"^[0-9+\-\s()]{7,15}$",
                "inputmode": "tel",
                "maxlength": 20,
            }
        )

    def clean_bed(self):
        bed = self.cleaned_data["bed"]
        if bed.room.pg.owner != self.owner:
            raise forms.ValidationError("You can only assign beds from your own properties.")
        if not bed.is_available:
            raise forms.ValidationError("Selected bed is no longer available.")
        return bed


class AddRoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["room_number", "room_type", "price_per_bed"]

    def __init__(self, *args, pg=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pg is None:
            raise ValueError("AddRoomForm requires a PG instance")
        self.pg = pg
        css_map = {
            "room_number": "form-control",
            "room_type": "form-select",
            "price_per_bed": "form-control",
        }
        for field_name, css_class in css_map.items():
            field = self.fields[field_name]
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} {css_class}".strip()

    def clean_room_number(self):
        room_number = self.cleaned_data["room_number"]
        if Room.objects.filter(pg=self.pg, room_number__iexact=room_number).exists():
            raise forms.ValidationError("A room with this number already exists in this PG.")
        return room_number

    def save(self, commit: bool = True):
        room = super().save(commit=False)
        room.pg = self.pg
        if commit:
            room.save()
            self._ensure_required_beds(room)
        return room

    def _ensure_required_beds(self, room: Room) -> None:
        capacity = room.share_capacity
        if not capacity:
            return
        existing_identifiers = set(room.beds.values_list("bed_identifier", flat=True))
        if len(existing_identifiers) >= capacity:
            return

        index = 0
        while len(existing_identifiers) < capacity:
            if index < len(ascii_uppercase):
                candidate = ascii_uppercase[index]
            else:
                candidate = f"Bed {index + 1}"
            index += 1
            if candidate in existing_identifiers:
                continue
            Bed.objects.create(room=room, bed_identifier=candidate)
            existing_identifiers.add(candidate)


class AddBedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ["room", "bed_identifier"]

    def __init__(self, *args, pg=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pg is None:
            raise ValueError("AddBedForm requires a PG instance")
        self.pg = pg
        rooms = list(Room.objects.filter(pg=pg).order_by("room_number"))
        available_room_ids: list[int] = []
        for room in rooms:
            capacity = room.share_capacity
            if capacity is None or room.beds.count() < capacity:
                available_room_ids.append(room.id)
        if available_room_ids:
            queryset = Room.objects.filter(pg=pg, id__in=available_room_ids).order_by("room_number")
        else:
            queryset = Room.objects.none()
        self.fields["room"].queryset = queryset
        css_map = {
            "room": "form-select",
            "bed_identifier": "form-control",
        }
        for field_name, css_class in css_map.items():
            field = self.fields[field_name]
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} {css_class}".strip()

    def clean_bed_identifier(self):
        bed_identifier = self.cleaned_data["bed_identifier"]
        room = self.cleaned_data.get("room")
        if room and Bed.objects.filter(room=room, bed_identifier__iexact=bed_identifier).exists():
            raise forms.ValidationError("This bed identifier already exists in the selected room.")
        return bed_identifier

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        if not room:
            return cleaned_data
        capacity = room.share_capacity
        if capacity and room.beds.count() >= capacity:
            raise forms.ValidationError(
                f"Room {room.room_number} is already configured for {capacity} bed{'s' if capacity != 1 else ''}."
            )
        return cleaned_data


class PropertyForm(forms.ModelForm):
    MIN_PHOTOS = 4

    city = forms.CharField(max_length=100, required=True)
    pincode = forms.CharField(max_length=10, required=True)
    amenities = forms.MultipleChoiceField(
        choices=AMENITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    property_images = MultipleImageField(
        help_text="Select at least four photos; hold Ctrl or Shift to pick multiple files.",
    )
    delete_images = forms.ModelMultipleChoiceField(
        queryset=PGImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Remove existing photos",
    )

    class Meta:
        model = PG
        fields = [
            "pg_name",
            "area",
            "address",
            "pg_type",
            "description",
            "deposit",
            "lock_in_period",
        ]
        widgets = {
            "pg_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Sunshine PG"}),
            "area": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Koramangala"}),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Enter complete address with landmarks",
                }
            ),
            "pg_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "deposit": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "lock_in_period": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
        self.fields["city"].widget.attrs.update({"class": "form-control", "placeholder": "e.g., Bangalore"})
        self.fields["pincode"].widget.attrs.update({"class": "form-control", "placeholder": "e.g., 560034"})
        self._existing_image_count = 0
        if self.instance and getattr(self.instance, "pk", None):
            self._existing_image_count = self.instance.images.count()
            address_line, city, pincode = self._split_address(self.instance.address or "")
            if address_line:
                self.fields["address"].initial = address_line
            if city:
                self.fields["city"].initial = city
            if pincode:
                self.fields["pincode"].initial = pincode
        self._require_images = self._existing_image_count == 0
        property_images_field = self.fields["property_images"]
        property_images_field.required = False
        property_images_field.widget.attrs.update(
            {"class": "form-control", "accept": "image/*", "multiple": True}
        )
        if self._existing_image_count:
            self.fields["delete_images"].queryset = self.instance.images.order_by("created_at", "id")
        else:
            self.fields.pop("delete_images")
        self._include_delete_field = "delete_images" in self.fields

    def clean_pincode(self):
        pincode = self.cleaned_data.get("pincode", "").strip()
        if pincode and not pincode.isdigit():
            raise forms.ValidationError("PIN Code must contain only digits.")
        return pincode

    def clean_deposit(self):
        deposit = self.cleaned_data.get("deposit")
        if deposit is not None and deposit < 0:
            raise forms.ValidationError("Deposit cannot be negative.")
        return deposit

    def clean_lock_in_period(self):
        lock_in = self.cleaned_data.get("lock_in_period")
        if lock_in is not None and lock_in < 0:
            raise forms.ValidationError("Lock-in period must be zero or a positive number of months.")
        return lock_in

    def clean(self):
        cleaned_data = super().clean()
        uploaded_images = cleaned_data.get("property_images") or []
        delete_images = cleaned_data.get("delete_images") if self._include_delete_field else []

        if self._require_images and len(uploaded_images) < self.MIN_PHOTOS:
            self.add_error(
                "property_images",
                f"Please upload at least {self.MIN_PHOTOS} property photos.",
            )

        remaining_count = self._existing_image_count - (len(delete_images) if delete_images else 0) + len(uploaded_images)
        if remaining_count < self.MIN_PHOTOS:
            error_message = (
                f"Please ensure the property keeps at least {self.MIN_PHOTOS} photos after your updates."
            )
            if self._include_delete_field:
                self.add_error("delete_images", error_message)
            else:
                self.add_error("property_images", error_message)
        return cleaned_data

    def save(self, commit: bool = True):
        pg = super().save(commit=False)
        if not self.owner:
            raise ValueError("PropertyForm.save() requires an owner instance")
        pg.owner = self.owner

        address_line = (self.cleaned_data.get("address") or "").strip()
        city = self.cleaned_data.get("city")
        pincode = self.cleaned_data.get("pincode")
        pg.address = self._compose_address(address_line, city, pincode)

        amenities = self.cleaned_data.get("amenities") or []
        pg.amenities = ", ".join(amenities)

        if commit:
            pg.save()
        else:
            raise ValueError("PropertyForm.save() requires commit=True to persist images")

        delete_images = self.cleaned_data.get("delete_images") if self._include_delete_field else []
        if delete_images:
            primary_name = pg.image.name if pg.image else ""
            for image in delete_images:
                if primary_name and image.image.name == primary_name:
                    pg.image = None
                image.image.delete(save=False)
                image.delete()
            if pg.image is None:
                pg.save(update_fields=["image"])

        new_images = self.cleaned_data.get("property_images") or []
        for image_file in new_images:
            PGImage.objects.create(pg=pg, image=image_file)

        if not pg.image:
            cover = pg.images.order_by("created_at", "id").first()
            if cover:
                pg.image = cover.image.name
                pg.save(update_fields=["image"])

        return pg

    @staticmethod
    def _split_address(full_address: str) -> tuple[str, str, str]:
        if not full_address:
            return "", "", ""
        base = full_address.strip()
        pincode = ""
        if " - " in base:
            base, potential_pincode = base.rsplit(" - ", 1)
            pincode = potential_pincode.strip()
        base = base.strip()
        city = ""
        if "," in base:
            address_line, potential_city = base.rsplit(",", 1)
            return address_line.strip(), potential_city.strip(), pincode
        return base, "", pincode

    @classmethod
    def _compose_address(cls, address_line: str, city: str | None, pincode: str | None) -> str:
        address_parts: list[str] = []
        if address_line:
            address_parts.append(address_line.strip())
        if city:
            address_parts.append(city.strip())
        composed = ", ".join(part for part in address_parts if part)
        if pincode:
            composed = f"{composed} - {pincode.strip()}" if composed else pincode.strip()
        return composed


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput,
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "minlength": 20,
                    "required": True,
                }
            ),
        }


class StudentBasicForm(forms.ModelForm):
    remove_profile_photo = forms.BooleanField(
        required=False,
        label="Remove current photo",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "age", "gender", "contact_number", "profile_photo"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "profile_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            "phone",
            "date_of_birth",
            "address_line",
            "city",
            "state",
            "pincode",
            "college",
            "course",
            "academic_year",
            "emergency_contact_name",
            "emergency_contact_phone",
            "bio",
        ]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "address_line": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pincode": forms.TextInput(attrs={"class": "form-control"}),
            "college": forms.TextInput(attrs={"class": "form-control"}),
            "course": forms.TextInput(attrs={"class": "form-control"}),
            "academic_year": forms.TextInput(attrs={"class": "form-control"}),
            "emergency_contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "emergency_contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BookingDatesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_in_months = None
        instance = getattr(self, "instance", None)
        if instance and getattr(instance, "bed_id", None):
            pg = instance.bed.room.pg
            self.lock_in_months = pg.lock_in_period or None
        if self.lock_in_months:
            for field in self.fields.values():
                field.disabled = True
                field.widget.attrs["readonly"] = True

    class Meta:
        model = Booking
        fields = ["check_in", "check_out"]
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "check_out": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        if check_in and check_out and check_out < check_in:
            self.add_error("check_out", "Check-out date cannot be before check-in date.")
        lock_in = getattr(self, "lock_in_months", None)
        if lock_in and check_in:
            expected_checkout = add_months(check_in, lock_in)
            if not check_out or check_out != expected_checkout:
                message = (
                    f"Check-out must be exactly {lock_in} month{'s' if lock_in != 1 else ''} after check-in."
                )
                self.add_error("check_out", message)
                cleaned_data["check_out"] = expected_checkout
        return cleaned_data


__all__ = [
    "RegisterForm",
    "OfflineBookingForm",
    "AddRoomForm",
    "AddBedForm",
    "StudentBasicForm",
    "StudentProfileForm",
    "BookingDatesForm",
    "PropertyForm",
    "AMENITY_CHOICES",
    "ReviewForm",
]
