import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Min, Count, Avg, Q, Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import (
    RegisterForm, OfflineBookingForm, AddRoomForm, AddBedForm,
    StudentBasicForm, StudentProfileForm, BookingDatesForm
)
from .decorators import owner_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify

from .models import PG, Room, Booking, Bed, StudentProfile

User = get_user_model()


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


def about_view(request):
    return render(request, 'about.html')


def contact_view(request):
    return render(request, 'contact.html')


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

@owner_required
def owner_dashboard_view(request):
    pgs_qs = (
        PG.objects
        .filter(owner=request.user)
        .annotate(
            room_count=Count('rooms', distinct=True),
            total_beds=Count('rooms__beds', distinct=True),
            occupied_beds=Count('rooms__beds', filter=Q(rooms__beds__is_available=False), distinct=True),
            available_beds=Count('rooms__beds', filter=Q(rooms__beds__is_available=True), distinct=True),
        )
        .prefetch_related('rooms__beds')
    )
    pgs = list(pgs_qs)

    total_pgs = len(pgs)
    total_beds = sum(pg.total_beds for pg in pgs)
    occupied_beds = sum(pg.occupied_beds for pg in pgs)
    occupancy_rate = round((occupied_beds / total_beds) * 100, 2) if total_beds else 0

    bookings_qs = (
        Booking.objects
        .filter(bed__room__pg__owner=request.user)
        .select_related('bed__room__pg', 'user')
        .order_by('-booking_date')
    )

    status_badge_map = {
        'active': 'bg-success-subtle text-success',
        'upcoming': 'bg-primary-subtle text-primary',
        'completed': 'bg-secondary-subtle text-secondary',
        'cancelled': 'bg-secondary-subtle text-secondary',
    }

    bookings = []
    for booking in bookings_qs:
        booking.refresh_status(persist=False)
        booking.status_label = booking.get_status_display()
        booking.status_badge_class = status_badge_map.get(booking.status, 'bg-light text-muted')
        booking.card_state = 'booking-cancelled' if booking.status == 'cancelled' else ''
        bookings.append(booking)

    students = User.objects.filter(user_type='student').order_by('first_name', 'username')

    for pg in pgs:
        pg.room_form = AddRoomForm(pg=pg)
        pg.bed_form = AddBedForm(pg=pg)

    stats = {
        'total_pgs': total_pgs,
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'occupancy_rate': occupancy_rate,
    }
    context = {
        'pgs': pgs,
        'stats': stats,
    'bookings': bookings,
        'students': students,
    }
    return render(request, 'owner_dashboard.html', context)


@owner_required
def add_property_view(request):

    context = {
        'pg_type_choices': PG.PG_TYPE_CHOICES,
        'form_data': None,
        'selected_amenities': [],
        'selected_pg_type': 'coed',
    }

    if request.method == 'POST':
        pg_name = request.POST.get('pg_name', '').strip()
        area = request.POST.get('area', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        description = request.POST.get('description', '').strip()
        amenities_selected = request.POST.getlist('amenities')
        pg_type = request.POST.get('pg_type', 'coed')
        deposit_input = request.POST.get('deposit', '').strip()
        lock_in_input = request.POST.get('lock_in_period', '').strip()
        property_image = request.FILES.get('property_image')

        context.update({
            'form_data': request.POST.dict(),
            'selected_amenities': amenities_selected,
            'selected_pg_type': pg_type,
        })

        valid_pg_types = {choice[0] for choice in PG.PG_TYPE_CHOICES}
        if pg_type not in valid_pg_types:
            pg_type = 'coed'
            context['selected_pg_type'] = pg_type

        if not pg_name or not area or not address:
            messages.error(request, "Please fill in all required fields (name, area, address).")
            return render(request, 'add_property.html', context)

        full_address = address
        if city:
            full_address = f"{full_address}, {city}"
        if pincode:
            full_address = f"{full_address} - {pincode}"

        amenities_str = ', '.join(amenities_selected) if amenities_selected else ''

        deposit = None
        if deposit_input:
            try:
                deposit = Decimal(deposit_input)
            except (InvalidOperation, TypeError):
                messages.error(request, "Please enter a valid deposit amount.")
                return render(request, 'add_property.html', context)

        lock_in_period = None
        if lock_in_input:
            if lock_in_input.isdigit():
                lock_in_period = int(lock_in_input)
            else:
                messages.error(request, "Lock-in period must be a positive number of months.")
                return render(request, 'add_property.html', context)

        pg = PG(
            owner=request.user,
            pg_name=pg_name,
            area=area,
            address=full_address,
            amenities=amenities_str,
            pg_type=pg_type,
            deposit=deposit,
            lock_in_period=lock_in_period,
            description=description,
        )

        if property_image:
            pg.image = property_image

        pg.save()
        messages.success(request, "Property submitted successfully.")
        return redirect('owner_dashboard')

    return render(request, 'add_property.html', context)

def pg_detail_view(request, pg_id):
    try:
        pg = PG.objects.get(id=pg_id)
    except PG.DoesNotExist:
        messages.error(request, "PG not found.")
        return redirect('home')

    bed_bookings_prefetch = Prefetch(
        'beds',
        queryset=Bed.objects.prefetch_related(
            Prefetch(
                'bookings',
                queryset=Booking.objects.select_related('user').order_by('-booking_date')
            )
        ).order_by('bed_identifier')
    )

    rooms = (
        pg.rooms
        .annotate(
            total_beds=Count('beds'),
            available_beds=Count('beds', filter=Q(beds__is_available=True)),
        )
        .prefetch_related(bed_bookings_prefetch)
        .order_by('room_number')
    )

    for room in rooms:
        for bed in room.beds.all():
            bookings = list(bed.bookings.all())
            bed.current_booking = bookings[0] if bookings else None
            bed.current_occupant = bed.current_booking.user if bed.current_booking else None
        room.roommate_beds = [bed for bed in room.beds.all() if bed.current_occupant]

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
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to continue with the booking.")
        return redirect('login')

    if getattr(request.user, 'user_type', None) != 'student':
        messages.error(request, "Only student accounts can book beds online.")
        return redirect('home')

    bed = get_object_or_404(Bed.objects.select_related('room__pg'), id=bed_id)

    monthly_rent = bed.room.price_per_bed or Decimal('0')
    raw_deposit = bed.room.pg.deposit
    deposit_applicable = raw_deposit is not None
    security_deposit = raw_deposit if deposit_applicable else Decimal('0')
    total_amount = monthly_rent + security_deposit

    if request.method == 'POST':
        if not bed.is_available:
            messages.error(request, "Sorry, this bed has already been booked.")
            return redirect('pg_detail', pg_id=bed.room.pg.id)

        today = timezone.now().date()
        booking = Booking.objects.create(
            user=request.user,
            bed=bed,
            booking_type='Online',
            status='active',
            check_in=today,
            check_out=today + timedelta(days=30),
        )
        bed.is_available = False
        bed.save(update_fields=['is_available'])

        messages.success(request, "Booking confirmed! We'll notify the property owner.")
        return redirect('booking_success', booking_id=booking.id)

    context = {
        'bed': bed,
        'monthly_rent': monthly_rent,
        'security_deposit': security_deposit,
        'total_amount': total_amount,
        'deposit_applicable': deposit_applicable,
    }
    return render(request, 'booking.html', context)


def booking_success_view(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('bed__room__pg', 'user'),
        id=booking_id,
    )

    is_owner = request.user.is_authenticated and getattr(request.user, 'user_type', None) == 'owner'
    if booking.user != request.user and not is_owner:
        messages.error(request, "You do not have access to this booking.")
        return redirect('home')

    monthly_rent = booking.bed.room.price_per_bed or Decimal('0')
    raw_deposit = booking.bed.room.pg.deposit
    deposit_applicable = raw_deposit is not None
    security_deposit = raw_deposit if deposit_applicable else Decimal('0')
    total_amount = monthly_rent + security_deposit

    roommates = (
        Booking.objects
        .select_related('user', 'bed')
        .filter(bed__room=booking.bed.room)
        .exclude(id=booking.id)
        .order_by('bed__bed_identifier')
    )

    context = {
        'booking': booking,
        'monthly_rent': monthly_rent,
        'security_deposit': security_deposit,
        'total_amount': total_amount,
        'deposit_applicable': deposit_applicable,
        'roommates': roommates,
    }
    return render(request, 'booking_success.html', context)


@require_POST
@owner_required
def owner_add_room_view(request, pg_id):

    pg = get_object_or_404(PG, id=pg_id, owner=request.user)
    form = AddRoomForm(request.POST, pg=pg)
    if form.is_valid():
        room = form.save()
        messages.success(request, f"Room {room.room_number} added to {pg.pg_name}.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return redirect('owner_dashboard')


@require_POST
@owner_required
def owner_add_bed_view(request, pg_id):

    pg = get_object_or_404(PG, id=pg_id, owner=request.user)
    form = AddBedForm(request.POST, pg=pg)
    if form.is_valid():
        bed = form.save()
        messages.success(request, f"Bed {bed.bed_identifier} added to Room {bed.room.room_number}.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return redirect('owner_dashboard')


@owner_required
def owner_add_offline_booking_view(request):

    form = OfflineBookingForm(request.POST or None, owner=request.user)

    if request.method == 'POST':
        if form.is_valid():
            bed = form.cleaned_data['bed']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            age = form.cleaned_data.get('age')
            gender = form.cleaned_data.get('gender') or None
            occupation = form.cleaned_data.get('occupation') or None
            contact = form.cleaned_data.get('contact_number')

            bed.refresh_from_db(fields=['is_available'])
            if not bed.is_available:
                messages.error(request, "Selected bed has already been booked.")
                return redirect('owner_add_offline_booking')

            occupant = User.objects.filter(email=email).first()
            if occupant is None:
                username_base = slugify(f"{first_name}{last_name}") or (email.split('@')[0] if email else 'tenant')
                username = username_base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{username_base}{counter}"
                    counter += 1
                occupant = User(username=username, email=email or '')
                occupant.user_type = 'student'
                occupant.set_unusable_password()

            occupant.first_name = first_name
            occupant.last_name = last_name
            occupant.user_type = 'student'
            occupant.age = age
            occupant.gender = gender
            occupant.occupation = occupation
            occupant.contact_number = contact or ''
            occupant.save()

            today = timezone.now().date()
            booking = Booking.objects.create(
                user=occupant,
                bed=bed,
                booking_type='Offline',
                status='active',
                check_in=today,
                check_out=today + timedelta(days=30),
            )
            bed.is_available = False
            bed.save(update_fields=['is_available'])

            messages.success(
                request,
                f"Offline booking created for {occupant.get_full_name() or occupant.username}."
            )
            return redirect('owner_dashboard')

    has_available_beds = form.fields['bed'].queryset.exists()

    context = {
        'form': form,
        'has_available_beds': has_available_beds,
    }
    return render(request, 'owner_add_offline_booking.html', context)


def student_profile_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to view your profile.")
        return redirect('login')
    if getattr(request.user, 'user_type', None) != 'student':
        messages.error(request, "Only student accounts can access the student profile page.")
        return redirect('home')

    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    user_form = StudentBasicForm(instance=request.user)
    profile_form = StudentProfileForm(instance=profile)
    password_form = PasswordChangeForm(request.user)

    def _style_password_form(form):
        for field in form.fields.values():
            existing_class = field.widget.attrs.get('class', '')
            form_class = f"{existing_class} form-control".strip()
            field.widget.attrs['class'] = form_class

    _style_password_form(password_form)

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'profile')

        if form_type == 'profile':
            user_form = StudentBasicForm(request.POST, instance=request.user)
            profile_form = StudentProfileForm(request.POST, instance=profile)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect('student_profile')
            else:
                messages.error(request, "Please correct the highlighted errors and try again.")
                password_form = PasswordChangeForm(request.user)
                _style_password_form(password_form)

        elif form_type == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            _style_password_form(password_form)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect('student_profile')
            else:
                messages.error(request, "Please fix the errors in the password form and resubmit.")
                user_form = StudentBasicForm(instance=request.user)
                profile_form = StudentProfileForm(instance=profile)

    recent_bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('bed__room__pg')
        .order_by('-booking_date')[:3]
    )

    badge_map = {
        'active': 'success',
        'upcoming': 'primary',
        'completed': 'secondary',
        'cancelled': 'danger',
    }

    for booking in recent_bookings:
        booking.refresh_status(persist=False)
        booking.badge_class = badge_map.get(booking.status, 'secondary')

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'student_profile.html', context)


def student_bookings_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to view your bookings.")
        return redirect('login')
    if getattr(request.user, 'user_type', None) != 'student':
        messages.error(request, "Only student accounts can access bookings history.")
        return redirect('home')

    bookings_qs = (
        Booking.objects
        .filter(user=request.user)
        .select_related('bed__room__pg')
        .order_by('-booking_date')
    )

    badge_map = {
        'active': 'success',
        'upcoming': 'primary',
        'completed': 'secondary',
        'cancelled': 'danger',
    }

    placeholder_image = "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800"

    bookings = []
    bookings_by_status = {'active': [], 'upcoming': [], 'completed': [], 'cancelled': []}
    status_counts = {'all': 0, 'active': 0, 'upcoming': 0, 'completed': 0, 'cancelled': 0}

    for booking in bookings_qs:
        booking.refresh_status(persist=False)
        booking.pg = booking.bed.room.pg
        booking.room = booking.bed.room
        if not booking.check_in:
            booking.check_in = booking.booking_date.date()
        if not booking.check_out and booking.check_in:
            booking.check_out = booking.check_in + timedelta(days=30)
        booking.badge_class = badge_map.get(booking.status, 'secondary')
        booking.status_label = booking.get_status_display()
        booking.image_url = booking.pg.image.url if booking.pg.image else placeholder_image
        booking.monthly_rent = booking.room.price_per_bed or Decimal('0')
        booking.dates_form = BookingDatesForm(instance=booking)
        status_counts['all'] += 1
        if booking.status in bookings_by_status:
            bookings_by_status[booking.status].append(booking)
            status_counts[booking.status] += 1
        bookings.append(booking)

    context = {
        'bookings': bookings,
        'bookings_by_status': bookings_by_status,
        'status_counts': status_counts,
    }
    return render(request, 'my_bookings.html', context)


@require_POST
def student_booking_update_dates_view(request, booking_id):
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'student':
        messages.error(request, "You do not have permission to modify this booking.")
        return redirect('login')

    booking = get_object_or_404(Booking.objects.select_related('bed__room__pg'), id=booking_id, user=request.user)
    form = BookingDatesForm(request.POST, instance=booking)
    if form.is_valid():
        updated_booking = form.save()
        updated_booking.refresh_status()
        messages.success(request, "Booking dates updated.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return redirect('student_bookings')


@require_POST
def student_booking_cancel_view(request, booking_id):
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'student':
        messages.error(request, "You do not have permission to cancel this booking.")
        return redirect('login')

    booking = get_object_or_404(Booking.objects.select_related('bed'), id=booking_id, user=request.user)
    if booking.status == 'cancelled':
        messages.info(request, "This booking is already cancelled.")
        return redirect('student_bookings')

    booking.mark_cancelled()
    if booking.bed:
        booking.bed.is_available = True
        booking.bed.save(update_fields=['is_available'])

    messages.success(request, "Booking cancelled successfully.")
    return redirect('student_bookings')


@require_POST
def bed_toggle_api_view(request, bed_id):
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'owner':
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=403)

    bed = get_object_or_404(Bed.objects.select_related('room__pg'), id=bed_id)

    if bed.room.pg.owner != request.user:
        return JsonResponse({'success': False, 'error': 'You can only modify your own beds'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)

    if 'is_available' not in payload or not isinstance(payload['is_available'], bool):
        return JsonResponse({'success': False, 'error': 'is_available must be provided as a boolean'}, status=400)

    bed.is_available = payload['is_available']
    bed.save(update_fields=['is_available'])

    return JsonResponse({'success': True, 'is_available': bed.is_available})
    