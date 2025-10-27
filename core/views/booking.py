import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from ..decorators import owner_required, student_required
from ..models import Bed, Booking
from ..services.student import (
    BedAvailabilityService,
    BookingMutationService,
    BookingRequestService,
    BookingSuccessService,
    StudentBookingsService,
    StudentProfileService,
)

__all__ = [
    "BookingRequestView",
    "BookingSuccessView",
    "StudentProfileView",
    "StudentBookingsView",
    "StudentBookingUpdateDatesView",
    "StudentBookingCancelView",
    "BedAvailabilityToggleView",
]


@method_decorator(student_required, name="dispatch")
class BookingRequestView(TemplateView):
    template_name = "booking/request.html"
    service_class = BookingRequestService

    def dispatch(self, request, *args, **kwargs):
        self.bed = self.get_bed(kwargs["bed_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_bed(self, bed_id: int) -> Bed:
        return get_object_or_404(Bed.objects.select_related("room__pg"), id=bed_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.service_class(self.request.user)
        quote = service.build_quote(self.bed)
        context.update(
            {
                "bed": self.bed,
                "monthly_rent": quote.monthly_rent,
                "security_deposit": quote.security_deposit,
                "total_amount": quote.total_amount,
                "deposit_applicable": quote.deposit_applicable,
                "lock_in_period": quote.lock_in_period,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        self.bed.refresh_from_db(fields=["is_available"])
        service = self.service_class(request.user)
        try:
            booking = service.create_booking(self.bed)
        except ValueError:
            messages.error(request, "Sorry, this bed has already been booked.")
            return redirect("pg_detail", pk=self.bed.room.pg.id)
        messages.success(request, "Booking request sent! The owner will review and respond soon.")
        return redirect("booking_success", booking_id=booking.id)


class BookingSuccessView(TemplateView):
    template_name = "booking/success.html"
    service_class = BookingSuccessService

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(
            Booking.objects.select_related("bed__room__pg", "user"),
            id=kwargs["booking_id"],
        )
        if not request.user.is_authenticated:
            messages.error(request, "You do not have access to this booking.")
            return redirect("home")
        is_owner = getattr(request.user, "user_type", None) == "owner"
        if self.booking.user != request.user and not is_owner:
            messages.error(request, "You do not have access to this booking.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.service_class(self.booking)
        quote = service.quote()
        context.update(
            {
                "booking": self.booking,
                "monthly_rent": quote.monthly_rent,
                "security_deposit": quote.security_deposit,
                "total_amount": quote.total_amount,
                "deposit_applicable": quote.deposit_applicable,
                "lock_in_period": quote.lock_in_period,
                "roommates": service.roommates(),
                "awaiting_owner": service.awaiting_owner(),
            }
        )
        return context


@method_decorator(student_required, name="dispatch")
class StudentProfileView(TemplateView):
    template_name = "student/profile.html"
    service_class = StudentProfileService

    def dispatch(self, request, *args, **kwargs):
        self.service = self.service_class(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_form = kwargs.get("user_form") or self.service.user_form()
        profile_form = kwargs.get("profile_form") or self.service.profile_form()
        password_form = kwargs.get("password_form") or self.service.password_form()
        context.update(
            {
                "user_form": user_form,
                "profile_form": profile_form,
                "password_form": password_form,
                "profile": self.service.profile,
                "recent_bookings": self.service.recent_bookings(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get("form_type", "profile")
        if form_type == "profile":
            success, user_form, profile_form = self.service.update_profile(request.POST, request.FILES)
            password_form = self.service.password_form()
            if success:
                messages.success(request, "Profile updated successfully.")
                return redirect("student_profile")
            messages.error(request, "Please correct the highlighted errors and try again.")
        elif form_type == "password":
            success, password_form, updated_user = self.service.update_password(request.POST)
            user_form = self.service.user_form()
            profile_form = self.service.profile_form()
            if success:
                update_session_auth_hash(request, updated_user)
                messages.success(request, "Password updated successfully.")
                return redirect("student_profile")
            messages.error(request, "Please fix the errors in the password form and resubmit.")
        else:
            user_form = self.service.user_form()
            profile_form = self.service.profile_form()
            password_form = self.service.password_form()

        context = self.get_context_data(
            user_form=user_form,
            profile_form=profile_form,
            password_form=password_form,
        )
        return self.render_to_response(context)


@method_decorator(student_required, name="dispatch")
class StudentBookingsView(TemplateView):
    template_name = "student/bookings.html"
    service_class = StudentBookingsService

    def get_service(self) -> StudentBookingsService:
        return self.service_class(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_service()
        bookings = service.bookings()
        grouped = service.grouped_bookings(bookings)
        context.update(
            {
                "bookings": bookings,
                "bookings_by_status": grouped,
                "status_counts": service.status_counts(bookings),
            }
        )
        return context


@method_decorator(student_required, name="dispatch")
class StudentBookingUpdateDatesView(View):
    service_class = BookingMutationService

    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("bed__room__pg"),
            id=booking_id,
            user=request.user,
        )
        service = self.service_class(request.user)
        form = service.update_dates(booking, request.POST)
        if form.is_valid():
            messages.success(request, "Booking dates updated.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("student_bookings")


@method_decorator(student_required, name="dispatch")
class StudentBookingCancelView(View):
    service_class = BookingMutationService

    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("bed"),
            id=booking_id,
            user=request.user,
        )
        if booking.status == "cancelled":
            messages.info(request, "This booking is already cancelled.")
            return redirect("student_bookings")

        service = self.service_class(request.user)
        service.cancel_booking(booking)
        messages.success(request, "Booking cancelled successfully.")
        return redirect("student_bookings")


@method_decorator(owner_required, name="dispatch")
class BedAvailabilityToggleView(View):
    http_method_names = ["post"]
    service_class = BedAvailabilityService

    def post(self, request, bed_id):
        bed = get_object_or_404(Bed.objects.select_related("room__pg"), id=bed_id)
        if bed.room.pg.owner != request.user:
            return JsonResponse({"success": False, "error": "You can only modify your own beds"}, status=403)

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON payload"}, status=400)

        if "is_available" not in payload or not isinstance(payload["is_available"], bool):
            return JsonResponse({"success": False, "error": "is_available must be provided as a boolean"}, status=400)

        service = self.service_class(request.user)
        service.toggle(bed, is_available=payload["is_available"])
        return JsonResponse({"success": True, "is_available": bed.is_available})
