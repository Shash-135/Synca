from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, RedirectView, TemplateView

from ..forms import RegisterForm
from ..models import PG, Room
from ..services.pg import PGDetailService, PGCatalogService


class SplashView(TemplateView):
    template_name = "public/splash.html"


class HomeView(TemplateView):
    template_name = "public/home.html"
    catalog_service_class = PGCatalogService

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
        # Preserve the original raw values for re-rendering the form inputs.
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
        if redirect_to and url_has_allowed_host_and_scheme(redirect_to, allowed_hosts={self.request.get_host()}):
            return redirect_to
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.service_class(self.object)
        context.update(service.build_context())
        return context
