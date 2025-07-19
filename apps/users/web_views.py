from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('users:profile')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            password = form.cleaned_data['password']

            user = authenticate(request, username=phone, password=password)
            if user:
                if user.is_active:
                    login(request, user)

                    # Redirect based on user type
                    if user.is_admin():
                        return redirect('admin_panel:dashboard')
                    elif user.is_hospital_admin():
                        return redirect('hospital_admin:dashboard')
                    elif user.is_doctor():
                        return redirect('doctors:dashboard')
                    else:
                        return redirect('users:profile')
                else:
                    messages.error(request, 'Hisobingiz faol emas.')
            else:
                messages.error(request, 'Telefon raqam yoki parol noto\'g\'ri.')
    else:
        form = UserLoginForm()

    context = {
        'form': form,
        'title': 'Kirish'
    }
    return render(request, 'users/login.html', context)


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Tizimdan muvaffaqiyatli chiqildingiz.')
    return redirect('users:login')


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('users:profile')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Ro\'yxatdan o\'tish muvaffaqiyatli yakunlandi!')
            return redirect('users:profile')
    else:
        form = UserRegistrationForm()

    context = {
        'form': form,
        'title': 'Ro\'yxatdan o\'tish'
    }
    return render(request, 'users/register.html', context)


@login_required
def profile_view(request):
    """User profile view"""
    user = request.user

    context = {
        'user': user,
        'title': 'Mening profilim'
    }
    return render(request, 'users/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit user profile"""
    user = request.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            user.check_profile_completeness()
            messages.success(request, 'Profil muvaffaqiyatli yangilandi!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'title': 'Profilni tahrirlash'
    }
    return render(request, 'users/edit_profile.html', context)