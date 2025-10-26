from django import forms

<<<<<<< HEAD
from ..models.booking import Booking
from ..models.profile import StudentProfile
from ..models.user import User
=======
from ..models import Booking, StudentProfile, User
>>>>>>> 302367afdaf4f58d43b2fa3059b039e751452676


class StudentBasicForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "age", "gender", "contact_number"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
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
        return cleaned_data
