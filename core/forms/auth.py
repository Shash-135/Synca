from django import forms

from ..models import User


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)
    gender = forms.ChoiceField(
        label="Gender",
        required=False,
        choices=[("", "Select gender")] + list(User.GENDER_CHOICES),
        widget=forms.Select,
    )

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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.gender = self.cleaned_data.get("gender") or None
        user.contact_number = self.cleaned_data.get("contact_number")
        if commit:
            user.save()
        return user
