from decimal import Decimal, InvalidOperation

from django.db.models import Min, Count, Avg, Q
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django import forms

from .models import PG, Room

User = get_user_model()

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    gender = forms.ChoiceField(
        label='Gender',
        required=False,
        choices=[('', 'Select gender')] + list(User.GENDER_CHOICES),
        widget=forms.Select,
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'age', 'gender', 'occupation', 'contact_number', 'user_type'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.gender = self.cleaned_data.get('gender') or None
        if commit:
            user.save()
        return user

def splash_view(request):
    return render(request, 'splash.html')

def home_view(request):
    selected_pg_type = request.GET.get('pg_type', '')
    selected_area = request.GET.get('area', '')
    selected_room_type = request.GET.get('room_type', '')
    max_price = request.GET.get('max_price', '')

    pgs = (
        PG.objects.all()
        .annotate(min_price=Min('rooms__price_per_bed'))
        .prefetch_related('rooms')
    )

    if selected_area:
        pgs = pgs.filter(area__iexact=selected_area)

    if selected_pg_type:
        pgs = pgs.filter(pg_type=selected_pg_type)

    if selected_room_type:
        pgs = pgs.filter(rooms__room_type=selected_room_type)

    if max_price:
        try:
            price_value = Decimal(max_price)
        except (InvalidOperation, TypeError):
            price_value = None
        if price_value is not None:
            pgs = pgs.filter(rooms__price_per_bed__lte=price_value)

    pgs = pgs.distinct()

    areas = PG.objects.order_by('area').values_list('area', flat=True).distinct()

    context = {
        'pgs': pgs,
        'areas': areas,
        'pg_type_choices': PG.PG_TYPE_CHOICES,
        'selected_pg_type': selected_pg_type,
        'room_type_choices': Room.ROOM_TYPE_CHOICES,
        'selected_room_type': selected_room_type,
    }
    return render(request, 'home.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'login.html', {'form': {'errors': True}})
    return render(request, 'login.html', {'form': {}})

def logout_view(request):
    logout(request)
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
        else:
            return render(request, 'register.html', {'form': form})
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def owner_dashboard_view(request):
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'owner':
        messages.error(request, "You do not have permission to access the owner dashboard.")
        return redirect('login')
    context = {}
    return render(request, 'owner_dashboard.html', context)

def pg_detail_view(request, pg_id):
    try:
        pg = PG.objects.get(id=pg_id)
    except PG.DoesNotExist:
        messages.error(request, "PG not found.")
        return redirect('home')

    rooms = (
        pg.rooms
        .annotate(
            total_beds=Count('beds'),
            available_beds=Count('beds', filter=Q(beds__is_available=True)),
        )
        .prefetch_related('beds')
        .order_by('room_number')
    )

    reviews = pg.reviews.select_related('user').order_by('-created_at')
    average_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
    amenities_list = [amenity.strip() for amenity in pg.amenities.split(',') if amenity.strip()] if pg.amenities else []

    context = {
        'pg': pg,
        'rooms': rooms,
        'reviews': reviews,
        'average_rating': average_rating,
        'amenities_list': amenities_list,
    }
    return render(request, 'pg_detail.html', context)

def booking_view(request, bed_id):
    context = {
        'bed_id': bed_id,
        # Add other context variables as needed
    }
    return render(request, 'booking.html', context)
    