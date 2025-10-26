from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, TemplateView

from ..decorators import owner_required
from ..forms import AMENITY_CHOICES, AddBedForm, AddRoomForm, OfflineBookingForm, PropertyForm
from ..models import Booking, PG
from ..services.owner import OfflineBookingService, OwnerDashboardService


@method_decorator(owner_required, name="dispatch")
class OwnerDashboardView(TemplateView):
    template_name = "owner_dashboard.html"
    service_class = OwnerDashboardService

    def get_service(self) -> OwnerDashboardService:
        return self.service_class(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_service()
        properties = service.properties()
        context.update(
            {
                "pgs": properties,
                "stats": service.stats(properties),
                "bookings": service.bookings(),
            }
        )
        return context


@method_decorator(owner_required, name="dispatch")
class OwnerPropertyCreateView(FormView):
    template_name = "add_property.html"
    form_class = PropertyForm
    success_url = reverse_lazy("owner_dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Property submitted successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please review the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["amenity_choices"] = AMENITY_CHOICES
        return context


@method_decorator(owner_required, name="dispatch")
class OwnerBookingDecisionView(View):
    http_method_names = ["post"]

    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("bed__room__pg", "bed"),
            id=booking_id,
        )
        if booking.bed.room.pg.owner != request.user:
            messages.error(request, "You can only manage bookings for your own properties.")
            return redirect("owner_dashboard")

        action = request.POST.get("action")
        if action not in {"approve", "cancel"}:
            messages.error(request, "Invalid action requested.")
            return redirect("owner_dashboard")

        if action == "approve":
            if booking.status != "pending":
                messages.info(request, "This booking is no longer awaiting approval.")
                return redirect("owner_dashboard")
            booking.mark_active()
            if booking.bed:
                booking.bed.is_available = False
                booking.bed.save(update_fields=["is_available"])
            messages.success(request, "Booking approved and activated.")
        else:
            if booking.status == "cancelled":
                messages.info(request, "This booking is already cancelled.")
                return redirect("owner_dashboard")
            booking.mark_cancelled()
            if booking.bed:
                booking.bed.is_available = True
                booking.bed.save(update_fields=["is_available"])
            messages.success(request, "Booking request cancelled.")

        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerRoomCreateView(View):
    http_method_names = ["post"]

    def post(self, request, pg_id):
        pg = get_object_or_404(PG, id=pg_id, owner=request.user)
        form = AddRoomForm(request.POST, pg=pg)
        if form.is_valid():
            room = form.save()
            messages.success(request, f"Room {room.room_number} added to {pg.pg_name}.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerBedCreateView(View):
    http_method_names = ["post"]

    def post(self, request, pg_id):
        pg = get_object_or_404(PG, id=pg_id, owner=request.user)
        form = AddBedForm(request.POST, pg=pg)
        if form.is_valid():
            bed = form.save()
            messages.success(request, f"Bed {bed.bed_identifier} added to Room {bed.room.room_number}.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerOfflineBookingView(FormView):
    template_name = "owner_add_offline_booking.html"
    form_class = OfflineBookingForm
    success_url = reverse_lazy("owner_dashboard")
    service_class = OfflineBookingService

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        return kwargs

    def get_service(self) -> OfflineBookingService:
        return self.service_class(self.request.user)

    def form_valid(self, form):
        service = self.get_service()
        bed = form.cleaned_data["bed"]
        if not service.ensure_bed_available(bed):
            form.add_error("bed", "Selected bed has already been booked.")
            return self.form_invalid(form)

        occupant = service.resolve_or_create_occupant(
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            age=form.cleaned_data.get("age"),
            gender=form.cleaned_data.get("gender") or None,
            occupation=form.cleaned_data.get("occupation") or None,
            contact=form.cleaned_data.get("contact_number"),
        )
        booking = service.create_booking(bed, occupant)
        messages.success(
            self.request,
            f"Offline booking created for {booking.user.get_full_name() or booking.user.username}.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Unable to create offline booking. Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        if form is not None:
            context["has_available_beds"] = form.fields["bed"].queryset.exists()
        else:
            context["has_available_beds"] = False
        return context
