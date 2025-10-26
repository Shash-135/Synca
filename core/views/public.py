from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Min, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import RegisterForm
from ..models import Bed, Booking, PG, Room

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
        return render(request, 'register.html', {'form': form})
    form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def pg_detail_view(request, pg_id):
    pg = get_object_or_404(PG, id=pg_id)

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
            active_booking = None
            pending_booking = None
            for booking in bookings:
                booking.refresh_status(persist=False)
                if booking.status == 'pending' and pending_booking is None:
                    pending_booking = booking
                if booking.status in {'active', 'upcoming'}:
                    active_booking = booking
                    break

            if not bed.is_available and active_booking:
                bed.current_booking = active_booking
                bed.current_occupant = active_booking.user if active_booking.user else None
            else:
                bed.current_booking = None
                bed.current_occupant = None

            bed.pending_booking = pending_booking if pending_booking and bed.is_available is False else None

        room.roommate_beds = [bed for bed in room.beds.all() if getattr(bed, 'current_occupant', None)]

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
