from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from ..decorators import owner_required
from ..forms import AMENITY_CHOICES, AddBedForm, AddRoomForm, OfflineBookingForm, PropertyForm
from ..models import Booking, PG

User = get_user_model()


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
    context = {'pgs': pgs, 'stats': stats, 'bookings': bookings, 'students': students}
    return render(request, 'owner_dashboard.html', context)


@owner_required
def add_property_view(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Property submitted successfully.")
            return redirect('owner_dashboard')
    else:
        form = PropertyForm(owner=request.user)

    context = {
        'form': form,
        'amenity_choices': AMENITY_CHOICES,
    }
    return render(request, 'add_property.html', context)


@owner_required
def owner_update_booking_view(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related('bed__room__pg'), id=booking_id)
    if booking.bed.room.pg.owner != request.user:
        messages.error(request, "You can only modify bookings for your own properties.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            occupant = get_object_or_404(User, id=user_id, user_type='student')
            booking.user = occupant
        else:
            booking.user = None
        booking.save(update_fields=['user'])
        messages.success(request, "Booking occupant updated successfully.")

    return redirect('owner_dashboard')


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
                check_out=today + timedelta(days=30)
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
