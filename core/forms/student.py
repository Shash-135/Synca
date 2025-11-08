from django import forms

from ..models import Booking, StudentProfile, User
from ..models.booking import add_months


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
