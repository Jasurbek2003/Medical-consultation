from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from apps.doctors.models import Doctor, DoctorViewStatistics
from apps.hospitals.models import Hospital
from apps.consultations.models import Consultation

User = get_user_model()


@login_required
def hospital_admin_required(view_func):
    """Decorator to ensure user is hospital admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_hospital_admin():
            messages.error(request, 'Bu sahifaga faqat shifoxona adminlari kira oladi.')
            return redirect('users:login')

        if not request.user.managed_hospital:
            messages.error(request, 'Sizga shifoxona tayinlanmagan.')
            return redirect('users:profile')

        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@hospital_admin_required
def hospital_dashboard(request):
    """Hospital admin dashboard"""

    hospital = request.user.managed_hospital

    # Doctor statistics
    doctors = Doctor.objects.filter(hospital=hospital)
    doctor_stats = {
        'total_doctors': doctors.count(),
        'active_doctors': doctors.filter(
            is_available=True,
            verification_status='approved'
        ).count(),
        'pending_approval': doctors.filter(
            verification_status='pending'
        ).count(),
        'average_rating': doctors.filter(
            verification_status='approved'
        ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
    }

    # Consultation statistics
    consultations = Consultation.objects.filter(doctor__hospital=hospital)
    consultation_stats = {
        'total_consultations': consultations.count(),
        'this_month': consultations.filter(
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).count(),
        'completed': consultations.filter(status='completed').count(),
        'pending': consultations.filter(status='scheduled').count(),
    }

    # View statistics
    total_views = sum(doctor.profile_views for doctor in doctors)
    monthly_views = sum(doctor.monthly_views for doctor in doctors)

    view_stats = {
        'total_views': total_views,
        'monthly_views': monthly_views,
        'average_views_per_doctor': total_views // doctors.count() if doctors.count() > 0 else 0,
    }

    # Top performing doctors
    top_doctors = doctors.filter(
        verification_status='approved'
    ).order_by('-rating', '-total_reviews')[:5]

    # Recent activities
    recent_consultations = consultations.order_by('-created_at')[:5]

    context = {
        'hospital': hospital,
        'doctor_stats': doctor_stats,
        'consultation_stats': consultation_stats,
        'view_stats': view_stats,
        'top_doctors': top_doctors,
        'recent_consultations': recent_consultations,
    }

    return render(request, 'hospital_admin/dashboard.html', context)


@login_required
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
    specialties = Doctor.SPECIALTIES

    context = {
        'doctors': doctors_page,
        'hospital': hospital,
        'specialties': specialties,
        'current_status': status_filter,
        'current_specialty': specialty_filter,
        'search_query': search_query,
    }

    return render(request, 'hospital_admin/doctors_list.html', context)


@login_required
@hospital_admin_required
def doctor_detail(request, doctor_id):
    """Doctor detail page for hospital admin"""

    hospital = request.user.managed_hospital
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

    # Get doctor statistics
    consultation_stats = {
        'total': doctor.total_consultations,
        'successful': doctor.successful_consultations,
        'success_rate': doctor.success_rate,
        'this_month': Consultation.objects.filter(
            doctor=doctor,
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).count(),
    }

    # View statistics for last 30 days
    thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
    daily_views = DoctorViewStatistics.objects.filter(
        doctor=doctor,
        date__gte=thirty_days_ago
    ).order_by('date')

    # Recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:10]

    # Monthly view trends
    view_data = []
    for stat in daily_views:
        view_data.append({
            'date': stat.date.strftime('%Y-%m-%d'),
            'views': stat.daily_views,
            'unique_visitors': stat.unique_visitors
        })

    context = {
        'doctor': doctor,
        'hospital': hospital,
        'consultation_stats': consultation_stats,
        'recent_consultations': recent_consultations,
        'view_data': view_data,
    }

    return render(request, 'hospital_admin/doctor_detail.html', context)


@login_required
@hospital_admin_required
def doctor_statistics(request):
    """Overall doctor statistics for hospital"""

    hospital = request.user.managed_hospital
    doctors = Doctor.objects.filter(hospital=hospital)

    # Specialty distribution
    specialty_stats = doctors.values('specialty').annotate(
        count=Count('id'),
        avg_rating=Avg('rating'),
        total_consultations=Count('consultations')
    ).order_by('-count')

    # Performance metrics
    performance_data = []
    for doctor in doctors.filter(verification_status='approved'):
        performance_data.append({
            'doctor': doctor,
            'rating': doctor.rating,
            'total_consultations': doctor.total_consultations,
            'success_rate': doctor.success_rate,
            'monthly_views': doctor.monthly_views,
            'total_reviews': doctor.total_reviews,
        })

    # Sort by rating
    performance_data.sort(key=lambda x: x['rating'], reverse=True)

    # Monthly trends
    current_month = timezone.now().month
    current_year = timezone.now().year

    monthly_stats = {
        'new_consultations': Consultation.objects.filter(
            doctor__hospital=hospital,
            created_at__month=current_month,
            created_at__year=current_year
        ).count(),
        'completed_consultations': Consultation.objects.filter(
            doctor__hospital=hospital,
            status='completed',
            created_at__month=current_month,
            created_at__year=current_year
        ).count(),
        'total_views': sum(doctor.monthly_views for doctor in doctors),
        'average_rating': doctors.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
    }

    context = {
        'hospital': hospital,
        'specialty_stats': specialty_stats,
        'performance_data': performance_data,
        'monthly_stats': monthly_stats,
    }

    return render(request, 'hospital_admin/statistics.html', context)


@login_required
@hospital_admin_required
def consultations_overview(request):
    """Consultations overview for hospital"""

    hospital = request.user.managed_hospital

    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    doctor_filter = request.GET.get('doctor', 'all')
    date_filter = request.GET.get('date', 'all')

    # Base queryset
    consultations = Consultation.objects.filter(
        doctor__hospital=hospital
    ).select_related('patient', 'doctor__user')

    # Apply filters
    if status_filter != 'all':
        consultations = consultations.filter(status=status_filter)

    if doctor_filter != 'all':
        consultations = consultations.filter(doctor__id=doctor_filter)

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


@login_required
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


@login_required
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


@login_required
@hospital_admin_required
def reports_and_analytics(request):
    """Reports and analytics for hospital admin"""

    hospital = request.user.managed_hospital

    # Time ranges
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    month_ago = today - timezone.timedelta(days=30)
    year_ago = today - timezone.timedelta(days=365)

    # Doctor performance report
    doctors = Doctor.objects.filter(hospital=hospital, verification_status='approved')
    doctor_performance = []

    for doctor in doctors:
        consultations_this_month = Consultation.objects.filter(
            doctor=doctor,
            created_at__date__gte=month_ago
        ).count()

        doctor_performance.append({
            'doctor': doctor,
            'rating': doctor.rating,
            'consultations_this_month': consultations_this_month,
            'total_consultations': doctor.total_consultations,
            'success_rate': doctor.success_rate,
            'monthly_views': doctor.monthly_views,
            'total_reviews': doctor.total_reviews,
        })

    # Sort by rating and consultations
    doctor_performance.sort(key=lambda x: (x['rating'], x['consultations_this_month']), reverse=True)

    # Consultation trends
    consultation_trends = []
    for i in range(30):
        date = today - timezone.timedelta(days=i)
        count = Consultation.objects.filter(
            doctor__hospital=hospital,
            created_at__date=date
        ).count()
        consultation_trends.append({
            'date': date.strftime('%Y-%m-%d'),
            'consultations': count
        })

    consultation_trends.reverse()  # Oldest first

    # Specialty performance
    specialty_performance = doctors.values('specialty').annotate(
        doctor_count=Count('id'),
        avg_rating=Avg('rating'),
        total_consultations=Count('consultations'),
        total_views=Count('view_statistics__daily_views')
    ).order_by('-total_consultations')

    # Revenue estimates (if consultation prices are tracked)
    revenue_data = {
        'total_potential': sum(d.total_consultations * d.consultation_price for d in doctors),
        'this_month_potential': sum(
            Consultation.objects.filter(
                doctor=d,
                created_at__date__gte=month_ago
            ).count() * d.consultation_price for d in doctors
        ),
    }

    # Patient satisfaction metrics
    from apps.consultations.models import Review
    reviews = Review.objects.filter(doctor__hospital=hospital, is_active=True)
    satisfaction_stats = {
        'total_reviews': reviews.count(),
        'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
        'rating_distribution': reviews.values('rating').annotate(count=Count('id')),
    }

    context = {
        'hospital': hospital,
        'doctor_performance': doctor_performance,
        'consultation_trends': consultation_trends,
        'specialty_performance': specialty_performance,
        'revenue_data': revenue_data,
        'satisfaction_stats': satisfaction_stats,
    }

    return render(request, 'hospital_admin/reports.html', context)


@login_required
@hospital_admin_required
def export_hospital_data(request):
    """Export hospital data"""

    hospital = request.user.managed_hospital
    export_type = request.GET.get('type', 'doctors')
    format_type = request.GET.get('format', 'csv')

    if export_type == 'doctors':
        # Export doctors data
        doctors = Doctor.objects.filter(hospital=hospital).select_related('user')
        data = []

        for doctor in doctors:
            data.append({
                'id': doctor.id,
                'name': doctor.full_name,
                'phone': doctor.phone,
                'email': doctor.email,
                'specialty': doctor.get_specialty_display(),
                'experience': doctor.experience,
                'rating': doctor.rating,
                'total_consultations': doctor.total_consultations,
                'success_rate': doctor.success_rate,
                'profile_views': doctor.profile_views,
                'monthly_views': doctor.monthly_views,
                'verification_status': doctor.get_verification_status_display(),
                'is_available': doctor.is_available,
                'created_at': doctor.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

    elif export_type == 'consultations':
        # Export consultations data
        consultations = Consultation.objects.filter(
            doctor__hospital=hospital
        ).select_related('patient', 'doctor__user')

        data = []
        for consultation in consultations:
            data.append({
                'id': consultation.id,
                'patient_name': consultation.patient.get_full_name(),
                'patient_phone': consultation.patient.phone,
                'doctor_name': consultation.doctor.full_name,
                'doctor_specialty': consultation.doctor.get_specialty_display(),
                'consultation_type': consultation.get_consultation_type_display(),
                'status': consultation.get_status_display(),
                'created_at': consultation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'scheduled_date': consultation.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if consultation.scheduled_date else '',
                'price': consultation.doctor.consultation_price,
            })

    elif export_type == 'statistics':
        # Export statistics summary
        doctors = Doctor.objects.filter(hospital=hospital)

        data = [{
            'hospital_name': hospital.name,
            'total_doctors': doctors.count(),
            'active_doctors': doctors.filter(is_available=True, verification_status='approved').count(),
            'total_consultations': sum(d.total_consultations for d in doctors),
            'average_rating': doctors.aggregate(avg=Avg('rating'))['avg'] or 0,
            'total_views': sum(d.profile_views for d in doctors),
            'monthly_views': sum(d.monthly_views for d in doctors),
            'export_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }]

    else:
        return JsonResponse({'error': 'Invalid export type'}, status=400)

    # Return data based on format
    if format_type == 'json':
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = f'attachment; filename="{hospital.name}_{export_type}_export.json"'
        return response

    elif format_type == 'csv':
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{hospital.name}_{export_type}_export.csv"'

        if data:
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        return response

    else:
        return JsonResponse({'error': 'Invalid format type'}, status=400)


@login_required
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


@login_required
@hospital_admin_required
def ajax_doctor_stats(request, doctor_id):
    """AJAX endpoint for doctor statistics"""

    hospital = request.user.managed_hospital
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)

    # Get statistics for the last 30 days
    thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)

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
        'doctor_name': doctor.full_name,
        'view_data': view_data,
        'consultation_data': consultation_data,
        'rating': doctor.rating,
        'total_reviews': doctor.total_reviews,
        'success_rate': doctor.success_rate,
    }

    return JsonResponse(response_data)


@login_required
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