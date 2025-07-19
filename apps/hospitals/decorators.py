from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def hospital_admin_required(view_func):
    """Decorator to ensure user is hospital admin"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')

        if not hasattr(request.user, 'is_hospital_admin') or not request.user.is_hospital_admin():
            messages.error(request, 'Bu sahifaga faqat shifoxona adminlari kira oladi.')
            return redirect('users:login')

        if not hasattr(request.user, 'managed_hospital') or not request.user.managed_hospital:
            messages.error(request, 'Sizga shifoxona tayinlanmagan.')
            return redirect('users:login')

        return view_func(request, *args, **kwargs)

    return wrapper


# Alternative approach - combining with login_required
def hospital_admin_required_alt(view_func):
    """Alternative decorator that combines login_required"""

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_hospital_admin():
            messages.error(request, 'Bu sahifaga faqat shifoxona adminlari kira oladi.')
            return redirect('users:login')

        if not request.user.managed_hospital:
            messages.error(request, 'Sizga shifoxona tayinlanmagan.')
            return redirect('users:login')

        return view_func(request, *args, **kwargs)

    return wrapper