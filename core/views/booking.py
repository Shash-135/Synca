import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import BookingDatesForm, StudentBasicForm, StudentProfileForm
from ..models import Bed, Booking, StudentProfile

User = get_user_model()


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
