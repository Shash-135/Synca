# core/views.py

from django.shortcuts import render

# This view will render your homepage
def home_view(request):
    # You can add logic here later to fetch PGs from the database
    # For now, it just renders the HTML page
    context = {} # This dictionary will pass data to the template
    return render(request, 'home.html', context)

def login_view(request):
    # We will add login logic here later
    return render(request, 'login.html')

def logout_view(request):
    # We will add logout logic here later
    # For now, it can redirect to the homepage
    from django.shortcuts import redirect
    return redirect('home')

def register_view(request):
    # We will add registration logic here later
    return render(request, 'register.html')

# TODO: Create views for login, logout, registration, pg_details, booking, etc.
#
# def login_view(request):
#     return render(request, 'login.html')