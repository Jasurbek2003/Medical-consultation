from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from functools import wraps

from apps.doctors.models import Doctor, DoctorViewStatistics
from apps.hospitals.models import Hospital
from apps.consultations.models import Consultation

User = get_user_model()


def hospital_admin_required(view_func):
    """Decorator to ensure user is hospital admin"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, 'Bu sahifaga kirish uchun tizimga kiring.')
            return redirect('users:login')

        # Check if user is hospital admin
        if not request.user.is_hospital_admin():
            messages.error(request, 'Bu sahifaga faqat shifoxona adminlari kira oladi.')
            return redirect('users:login')

        # Check if user has assigned hospital
        if not request.user.managed_hospital:
            messages.error(request, 'Sizga shifoxona tayinlanmagan.')
            return redirect('users:login')

        return view_func(request, *args, **kwargs)

    return wrapper


@hospital_admin_required
def dashboard(request):
    """Hospital admin dashboard"""

    hospital = request.user.managed_hospital

    # Get hospital statistics
    total_doctors = Doctor.objects.filter(hospital=hospital).count()
    active_doctors = Doctor.objects.filter(
        hospital=hospital,
        is_available=True,
        verification_status='approved'
    ).count()
    pending_doctors = Doctor.objects.filter(
        hospital=hospital,
        verification_status='pending'
    ).count()

    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor__hospital=hospital
    ).order_by('-created_at')[:10]

    # Get top doctors by rating
    top_doctors = Doctor.objects.filter(
        hospital=hospital,
        verification_status='approved'
    ).order_by('-rating')[:5]

    # Monthly statistics
    current_month = timezone.now().replace(day=1)
    monthly_consultations = Consultation.objects.filter(
        doctor__hospital=hospital,
        created_at__gte=current_month
    ).count()

    context = {
        'hospital': hospital,
        'total_doctors': total_doctors,
        'active_doctors': active_doctors,
        'pending_doctors': pending_doctors,
        'monthly_consultations': monthly_consultations,
        'top_doctors': top_doctors,
        'recent_consultations': recent_consultations,
    }

    return render(request, 'hospital_admin/dashboard.html', context)


@hospital_admin_required
def doctors_list(request):
    """List of doctors in hospital"""

    hospital = request.user.managed_hospital

    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    specialty_filter = request.GET.get('specialty', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    doctors = Doctor.objects.filter(hospital=hospital).select_related('user')

    # Apply filters
    if status_filter == 'active':
        doctors = doctors.filter(is_available=True, verification_status='approved')
    elif status_filter == 'inactive':
        doctors = doctors.filter(is_available=False)
    elif status_filter == 'pending':
        doctors = doctors.filter(verification_status='pending')
    elif status_filter == 'approved':
        doctors = doctors.filter(verification_status='approved')

    if specialty_filter != 'all':
        doctors = doctors.filter(specialty=specialty_filter)

    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__phone__icontains=search_query) |
            Q(license_number__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(doctors, 15)
    page_number = request.GET.get('page')
    doctors_page = paginator.get_page(page_number)

    # Get filter options
    specialties = Doctor.SPECIALTIES if hasattr(Doctor, 'SPECIALTIES') else []

    context = {
        'doctors': doctors_page,
        'hospital': hospital,
        'specialties': specialties,
        'current_status': status_filter,
        'current_specialty': specialty_filter,
        'search_query': search_query,
    }

    return render(request, 'hospital_admin/doctors_list.html', context)


@hospital_admin_required
def doctor_detail(request, doctor_id):
    """Doctor detail page for hospital admin"""

    hospital = request.user.managed_hospital
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

    # Get doctor statistics
    total_consultations = Consultation.objects.filter(doctor=doctor).count()
    monthly_consultations = Consultation.objects.filter(
        doctor=doctor,
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    ).count()

    # Get recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:10]

    context = {
        'hospital': hospital,
        'doctor': doctor,
        'total_consultations': total_consultations,
        'monthly_consultations': monthly_consultations,
        'recent_consultations': recent_consultations,
    }

    return render(request, 'hospital_admin/doctor_detail.html', context)


@hospital_admin_required
def consultations_overview(request):
    """Consultations overview for hospital admin"""

    hospital = request.user.managed_hospital

    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    doctor_filter = request.GET.get('doctor', 'all')
    date_filter = request.GET.get('date', 'all')

    # Base queryset
    consultations = Consultation.objects.filter(doctor__hospital=hospital)

    # Apply filters
    if status_filter != 'all':
        consultations = consultations.filter(status=status_filter)

    if doctor_filter != 'all':
        consultations = consultations.filter(doctor_id=doctor_filter)

    if date_filter == 'today':
        consultations = consultations.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now().date() - timezone.timedelta(days=7)
        consultations = consultations.filter(created_at__date__gte=week_ago)
    elif date_filter == 'month':
        consultations = consultations.filter(
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        )

    # Pagination
    paginator = Paginator(consultations.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    consultations_page = paginator.get_page(page_number)

    # Statistics
    consultation_stats = {
        'total': consultations.count(),
        'by_status': consultations.values('status').annotate(count=Count('id')),
    }

    # Get doctors for filter
    hospital_doctors = Doctor.objects.filter(
        hospital=hospital,
        verification_status='approved'
    ).select_related('user')

    context = {
        'consultations': consultations_page,
        'hospital': hospital,
        'hospital_doctors': hospital_doctors,
        'consultation_stats': consultation_stats,
        'current_status': status_filter,
        'current_doctor': doctor_filter,
        'current_date': date_filter,
    }

    return render(request, 'hospital_admin/consultations.html', context)


@hospital_admin_required
def hospital_profile(request):
    """Hospital profile management"""

    hospital = request.user.managed_hospital

    if request.method == 'POST':
        # Update hospital information (limited fields)
        hospital.description = request.POST.get('description', hospital.description)
        hospital.services = request.POST.get('services', hospital.services)
        hospital.working_hours = request.POST.get('working_hours', hospital.working_hours)

        # Handle logo upload
        if 'logo' in request.FILES:
            hospital.logo = request.FILES['logo']

        hospital.save()
        messages.success(request, 'Shifoxona ma\'lumotlari yangilandi.')
        return redirect('hospital_admin:hospital_profile')

    context = {
        'hospital': hospital,
    }

    return render(request, 'hospital_admin/hospital_profile.html', context)


@hospital_admin_required
def my_profile(request):
    """Hospital admin profile management"""

    user = request.user

    if request.method == 'POST':
        # Update admin profile (limited fields)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.region = request.POST.get('region', user.region)
        user.district = request.POST.get('district', user.district)
        user.address = request.POST.get('address', user.address)

        # Handle avatar upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        # Update notification preferences
        user.email_notifications = 'email_notifications' in request.POST
        user.sms_notifications = 'sms_notifications' in request.POST

        user.save()
        messages.success(request, 'Profil ma\'lumotlari yangilandi.')
        return redirect('hospital_admin:my_profile')

    context = {
        'user': user,
    }

    return render(request, 'hospital_admin/my_profile.html', context)


@hospital_admin_required
def notification_center(request):
    """Notification center for hospital admin"""

    hospital = request.user.managed_hospital

    # Get recent activities and notifications
    notifications = []

    # New doctor applications
    pending_doctors = Doctor.objects.filter(
        hospital=hospital,
        verification_status='pending'
    ).count()

    if pending_doctors > 0:
        notifications.append({
            'type': 'doctor_application',
            'title': 'Yangi shifokor so\'rovlari',
            'message': f'{pending_doctors} ta yangi shifokor tasdiqlashni kutmoqda',
            'count': pending_doctors,
            'url': 'hospital_admin:doctors_list',
            'created_at': timezone.now(),
        })

    # Recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor__hospital=hospital,
        created_at__date=timezone.now().date()
    ).count()

    if recent_consultations > 0:
        notifications.append({
            'type': 'consultation',
            'title': 'Bugungi konsultatsiyalar',
            'message': f'Bugun {recent_consultations} ta konsultatsiya bo\'ldi',
            'count': recent_consultations,
            'url': 'hospital_admin:consultations_overview',
            'created_at': timezone.now(),
        })

    # Low-rated doctors (rating < 3.0)
    low_rated_doctors = Doctor.objects.filter(
        hospital=hospital,
        verification_status='approved',
        rating__lt=3.0,
        total_reviews__gte=5  # Only if they have enough reviews
    ).count()

    if low_rated_doctors > 0:
        notifications.append({
            'type': 'warning',
            'title': 'Past reytingli shifokorlar',
            'message': f'{low_rated_doctors} ta shifokorning reytingi pastlashgan',
            'count': low_rated_doctors,
            'url': 'hospital_admin:doctor_statistics',
            'created_at': timezone.now(),
        })

    context = {
        'hospital': hospital,
        'notifications': notifications,
    }

    return render(request, 'hospital_admin/notifications.html', context)


@hospital_admin_required
def ajax_doctor_stats(request, doctor_id):
    """AJAX endpoint for doctor statistics"""

    hospital = request.user.managed_hospital
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

    # Get statistics for the last 30 days
    thirty_days_ago = timezone.now().date() - timedelta(days=30)

    # Daily view statistics
    daily_stats = DoctorViewStatistics.objects.filter(
        doctor=doctor,
        date__gte=thirty_days_ago
    ).order_by('date')

    view_data = []
    for stat in daily_stats:
        view_data.append({
            'date': stat.date.strftime('%Y-%m-%d'),
            'views': stat.daily_views,
            'unique_visitors': stat.unique_visitors
        })

    # Consultation statistics
    consultations = Consultation.objects.filter(doctor=doctor)
    consultation_data = {
        'total': consultations.count(),
        'this_month': consultations.filter(
            created_at__date__gte=thirty_days_ago
        ).count(),
        'by_status': {}
    }

    # Group by status
    status_counts = consultations.values('status').annotate(count=Count('id'))
    for item in status_counts:
        consultation_data['by_status'][item['status']] = item['count']

    response_data = {
        'doctor_id': doctor.id,
        'doctor_name': doctor.full_name if hasattr(doctor,
                                                   'full_name') else f"{doctor.user.first_name} {doctor.user.last_name}",
        'view_data': view_data,
        'consultation_data': consultation_data,
        'rating': doctor.rating,
        'total_reviews': doctor.total_reviews,
        'success_rate': getattr(doctor, 'success_rate', 0),
    }

    return JsonResponse(response_data)


@hospital_admin_required
def doctor_availability_toggle(request, doctor_id):
    """Toggle doctor availability (AJAX)"""

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    hospital = request.user.managed_hospital
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

    # Hospital admin cannot directly change doctor availability
    # They can only view statistics and send notifications
    return JsonResponse({
        'error': 'Shifokor mavjudligini faqat shifokor o\'zi o\'zgartira oladi'
    }, status=403)