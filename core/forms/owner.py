from django import forms

from ..models import Bed, PG, Room, User

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

    def save(self, commit=True):
        room = super().save(commit=False)
        room.pg = self.pg
        if commit:
            room.save()
        return room


class AddBedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ["room", "bed_identifier"]

    def __init__(self, *args, pg=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pg is None:
            raise ValueError("AddBedForm requires a PG instance")
        self.pg = pg
        self.fields["room"].queryset = Room.objects.filter(pg=pg).order_by("room_number")
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


class PropertyForm(forms.ModelForm):
    city = forms.CharField(max_length=100, required=True)
    pincode = forms.CharField(max_length=10, required=True)
    amenities = forms.MultipleChoiceField(
        choices=AMENITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    property_image = forms.ImageField(required=False)

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
        self.fields["property_image"].widget.attrs.update({"class": "form-control", "accept": "image/*"})
        self.fields["property_image"].required = not (self.instance and self.instance.pk)

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

    def save(self, commit=True):
        pg = super().save(commit=False)
        if not self.owner:
            raise ValueError("PropertyForm.save() requires an owner instance")
        pg.owner = self.owner

        city = self.cleaned_data.get("city")
        pincode = self.cleaned_data.get("pincode")
        if city:
            pg.address = f"{pg.address.strip()}, {city.strip()}" if pg.address else city.strip()
        if pincode:
            pg.address = f"{pg.address.strip()} - {pincode.strip()}" if pg.address else pincode.strip()

        amenities = self.cleaned_data.get("amenities") or []
        pg.amenities = ", ".join(amenities)

        property_image = self.cleaned_data.get("property_image")
        if property_image:
            pg.image = property_image

        if commit:
            pg.save()
        return pg
