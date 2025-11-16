from __future__ import annotations

import json
from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DetailView, FormView, RedirectView, TemplateView

from .decorators import owner_required, student_required
from .forms import (
    AMENITY_CHOICES,
    OfflineBookingForm,
    PropertyForm,
    RegisterForm,
)
from .models import Bed, Booking, PG, Room
from .services import (
    BedAvailabilityService,
    BookingMutationService,
    BookingRequestService,
    BookingSuccessService,
    OfflineBookingService,
    OwnerBookingActionService,
    OwnerDashboardService,
    OwnerInventoryService,
    PGCatalogService,
    PGDetailService,
    ReviewService,
    StudentBookingsService,
    StudentProfileService,
)


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


@method_decorator(owner_required, name="dispatch")
class OwnerDashboardView(TemplateView):
    template_name = "owner/dashboard.html"
    service_class = OwnerDashboardService

    def get_service(self) -> OwnerDashboardService:
        inventory_service = OwnerInventoryService(self.request.user)
        return self.service_class(self.request.user, inventory_service=inventory_service)

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
    template_name = "owner/add_property.html"
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
        form = context.get("form")
        if form is not None:
            context["amenity_choices"] = form.fields["amenities"].choices
        else:
            context["amenity_choices"] = AMENITY_CHOICES
        return context


@method_decorator(owner_required, name="dispatch")
class OwnerPropertyUpdateView(FormView):
    template_name = "owner/edit_property.html"
    form_class = PropertyForm
    success_url = reverse_lazy("owner_dashboard")

    def dispatch(self, request, *args, **kwargs):
        self.pg = get_object_or_404(PG, id=kwargs["pg_id"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        kwargs["instance"] = self.pg
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.pg.pg_name} updated successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted errors before saving.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pg"] = self.pg
        context["existing_images"] = self.pg.images.order_by("created_at", "id")
        form = context.get("form")
        context["show_delete_images"] = bool(form and "delete_images" in form.fields)
        return context


@method_decorator(owner_required, name="dispatch")
class OwnerBookingDecisionView(View):
    http_method_names = ["post"]
    service_class = OwnerBookingActionService

    def get_service(self) -> OwnerBookingActionService:
        return self.service_class(self.request.user)

    def post(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("bed__room__pg", "bed"),
            id=booking_id,
        )
        action = request.POST.get("action")
        if action not in {"approve", "cancel"}:
            messages.error(request, "Invalid action requested.")
            return redirect("owner_dashboard")

        service = self.get_service()
        try:
            outcome = service.approve(booking) if action == "approve" else service.cancel(booking)
        except PermissionError:
            messages.error(request, "You can only manage bookings for your own properties.")
            return redirect("owner_dashboard")

        notifier = getattr(messages, outcome.level, messages.info)
        notifier(request, outcome.message)
        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerRoomCreateView(View):
    http_method_names = ["post"]
    service_class = OwnerInventoryService

    def get_service(self) -> OwnerInventoryService:
        return self.service_class(self.request.user)

    def post(self, request, pg_id):
        pg = get_object_or_404(PG, id=pg_id, owner=request.user)
        service = self.get_service()
        success, form, room = service.create_room(pg, request.POST)
        if success:
            capacity = room.share_capacity
            if capacity:
                messages.success(
                    request,
                    f"Room {room.room_number} added to {pg.pg_name} with {capacity} bed"
                    f"{'s' if capacity != 1 else ''} automatically configured.",
                )
            else:
                messages.success(request, f"Room {room.room_number} added to {pg.pg_name}.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerBedCreateView(View):
    http_method_names = ["post"]
    service_class = OwnerInventoryService

    def get_service(self) -> OwnerInventoryService:
        return self.service_class(self.request.user)

    def post(self, request, pg_id):
        pg = get_object_or_404(PG, id=pg_id, owner=request.user)
        service = self.get_service()
        success, form, bed = service.create_bed(pg, request.POST)
        if success:
            messages.success(request, f"Bed {bed.bed_identifier} added to Room {bed.room.room_number}.")
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect("owner_dashboard")


@method_decorator(owner_required, name="dispatch")
class OwnerOfflineBookingView(FormView):
    template_name = "owner/offline_booking.html"
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


class SplashView(TemplateView):
    template_name = "public/splash.html"


class HomeView(TemplateView):
    template_name = "public/home.html"
    catalog_service_class = PGCatalogService

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, "user_type", "") == "owner":
            return redirect("owner_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_catalog_service(self) -> PGCatalogService:
        return self.catalog_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_catalog_service()
        filters = service.build_filters(self.request.GET)
        context.update(
            {
                "pgs": service.get_catalog(filters),
                "areas": service.available_areas(),
                "pg_type_choices": PG.PG_TYPE_CHOICES,
                "selected_pg_type": filters.pg_type,
                "room_type_choices": Room.ROOM_TYPE_CHOICES,
                "selected_room_type": filters.room_type,
            }
        )
        context["selected_area"] = filters.area
        context["selected_max_price"] = (
            str(filters.max_price) if filters.max_price is not None else self.request.GET.get("max_price", "")
        )
        return context


class AboutView(TemplateView):
    template_name = "public/about.html"


class ContactView(TemplateView):
    template_name = "public/contact.html"


class LoginView(FormView):
    template_name = "auth/login.html"
    form_class = AuthenticationForm
    success_url = reverse_lazy("home")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_success_url(self):
        redirect_to = self.request.POST.get("next") or self.request.GET.get("next")
        user = getattr(self.request, "user", None)
        is_owner = bool(user and user.is_authenticated and getattr(user, "user_type", "") == "owner")
        if redirect_to and url_has_allowed_host_and_scheme(redirect_to, allowed_hosts={self.request.get_host()}):
            if is_owner:
                target_path = urlsplit(redirect_to).path or redirect_to
                home_path = str(reverse_lazy("home"))
                home_variants = {home_path, home_path.lstrip("/")}
                home_variants.add(home_path.strip("/"))
                allowed_paths = {"", "/"}
                allowed_paths.update(home_variants)
                if target_path not in allowed_paths:
                    return redirect_to
                return str(reverse_lazy("owner_dashboard"))
            return redirect_to
        if is_owner:
            return str(reverse_lazy("owner_dashboard"))
        return super().get_success_url()

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(RedirectView):
    pattern_name = "home"

    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)


class RegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Registration successful. Please log in.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted errors.")
        return self.render_to_response(self.get_context_data(form=form))


class PGDetailView(DetailView):
    template_name = "pg/detail.html"
    model = PG
    context_object_name = "pg"
    service_class = PGDetailService

    def get_queryset(self):
        return super().get_queryset().prefetch_related("images")

    def get_review_service(self) -> ReviewService:
        return ReviewService(self.request.user)

    def get_context_data(self, **kwargs):
        review_form = kwargs.pop("review_form", None)
        user_review = kwargs.pop("user_review", None)
        review_eligibility = kwargs.pop("review_eligibility", None)

        context = super().get_context_data(**kwargs)
        service = self.service_class(self.object)
        context.update(service.build_context())

        review_service = self.get_review_service()
        if review_eligibility is None:
            review_eligibility = review_service.eligibility(self.object)
        if user_review is None:
            user_review = review_service.user_review(self.object)

        if review_eligibility.can_review:
            review_form = review_form or review_service.form(self.object)
        else:
            review_form = None

        context.update(
            {
                "review_form": review_form,
                "user_review": user_review,
                "user_can_review": review_eligibility.can_review,
                "review_eligibility_reason": review_eligibility.reason,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        review_service = self.get_review_service()
        existing_review = review_service.user_review(self.object)
        success, form, review, eligibility = review_service.save(self.object, request.POST)

        if success:
            if existing_review:
                messages.success(request, "Your review has been updated.")
            else:
                messages.success(request, "Thanks for reviewing this property!")
            return redirect(request.path)

        if not eligibility.can_review:
            if eligibility.reason:
                messages.error(request, eligibility.reason)
            else:
                messages.error(request, "You are not allowed to review this property.")
            return redirect(request.path)

        context = self.get_context_data(
            review_form=form,
            user_review=existing_review,
            review_eligibility=eligibility,
        )
        return self.render_to_response(context)


__all__ = [
    "BookingRequestView",
    "BookingSuccessView",
    "StudentProfileView",
    "StudentBookingsView",
    "StudentBookingUpdateDatesView",
    "StudentBookingCancelView",
    "BedAvailabilityToggleView",
    "OwnerDashboardView",
    "OwnerPropertyCreateView",
    "OwnerPropertyUpdateView",
    "OwnerBookingDecisionView",
    "OwnerRoomCreateView",
    "OwnerBedCreateView",
    "OwnerOfflineBookingView",
    "SplashView",
    "HomeView",
    "AboutView",
    "ContactView",
    "LoginView",
    "LogoutView",
    "RegisterView",
    "PGDetailView",
]
