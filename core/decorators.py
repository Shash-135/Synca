from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def owner_required(view_func):
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'user_type', None) != 'owner':
            messages.error(request, "You do not have permission to access that page.")
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def student_required(view_func):
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'user_type', None) != 'student':
            messages.error(request, "Only student accounts can access that page.")
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped_view
