from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.doctors.models import Doctor
from apps.doctors.serializers import DoctorSerializer
from apps.hospitals.models import Hospital
from apps.consultations.models import Consultation

User = get_user_model()


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with statistics"""

    # User statistics
    user_stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'patients': User.objects.filter(user_type='patient').count(),
        'doctors': User.objects.filter(user_type='doctor').count(),
        'approved_doctors': User.objects.filter(
            user_type='doctor',
            is_approved_by_admin=True
        ).count(),
        'pending_doctors': User.objects.filter(
            user_type='doctor',
            is_approved_by_admin=False,
            is_active=True
        ).count(),
        'hospital_admins': User.objects.filter(user_type='hospital_admin').count(),
    }

    # Doctor statistics
    doctor_stats = {
        'total_doctors': Doctor.objects.count(),
        'verified_doctors': Doctor.objects.filter(verification_status='approved').count(),
        'pending_doctors': Doctor.objects.filter(verification_status='pending').count(),
        'rejected_doctors': Doctor.objects.filter(verification_status='rejected').count(),
        'active_doctors': Doctor.objects.filter(
            verification_status='approved',
            is_available=True
        ).count(),
    }

    # Consultation statistics
    consultation_stats = {
        'total_consultations': Consultation.objects.count(),
        'completed_consultations': Consultation.objects.filter(status='completed').count(),
        'pending_consultations': Consultation.objects.filter(status='scheduled').count(),
        'cancelled_consultations': Consultation.objects.filter(status='cancelled').count(),
    }

    # Recent activities
    recent_users = User.objects.filter(is_active=True).order_by('-created_at')[:5]
    pending_doctors = User.objects.filter(
        user_type='doctor',
        is_approved_by_admin=False,
        is_active=True
    ).order_by('-created_at')[:5]

    context = {
        'user_stats': user_stats,
        'doctor_stats': doctor_stats,
        'consultation_stats': consultation_stats,
        'recent_users': recent_users,
        'pending_doctors': pending_doctors,
    }

    return render(request, 'admin_panel/dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_management(request):
    """Doctor management page for admin"""

    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    specialty_filter = request.GET.get('specialty', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    doctors = Doctor.objects.select_related('user', 'hospital').all()

    # Apply filters
    if status_filter != 'all':
        doctors = doctors.filter(verification_status=status_filter)

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
    paginator = Paginator(doctors, 20)
    page_number = request.GET.get('page')
    doctors_page = paginator.get_page(page_number)

    # Get filter options
    serializer = DoctorSerializer(doctors_page, many=True)

    data = {
        'doctors': serializer.data,
        'pagination': {
            'current_page': doctors_page.number,
            'total_pages': doctors_page.paginator.num_pages,
            'has_next': doctors_page.has_next(),
            'has_previous': doctors_page.has_previous(),
            'total_items': doctors_page.paginator.count,
        },
        'filters': {
            'specialties': dict(Doctor.SPECIALTIES),
            'statuses': dict(Doctor.VERIFICATION_STATUS),
            'current_status': status_filter,
            'current_specialty': specialty_filter,
            'search_query': search_query,
        }
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_detail(request, doctor_id):
    """Doctor detail page for admin"""

    doctor = get_object_or_404(Doctor, id=doctor_id)

    # Get doctor statistics
    consultation_stats = {
        'total': doctor.total_consultations,
        'successful': doctor.successful_consultations,
        'success_rate': doctor.success_rate,
    }

    # Recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:10]

    serializer = DoctorSerializer(doctor)
    print(consultation_stats)

    context = {
        'doctor': serializer.data,
        'consultation_stats': consultation_stats,
        'recent_consultations': list(recent_consultations.values()),
    }
    print("Admin doctor detail context:", context)

    return JsonResponse(context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_doctor(request, doctor_id):
    """Approve doctor"""

    if request.method == 'POST':
        doctor = get_object_or_404(Doctor, id=doctor_id)

        # Approve the doctor
        doctor.approve(request.user)

        messages.success(request, f'Shifokor {doctor.full_name} muvaffaqiyatli tasdiqlandi.')

        return JsonResponse({
            'success': True,
            'message': 'Shifokor tasdiqlandi'
        })

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_doctor(request, doctor_id):
    """Reject doctor"""

    if request.method == 'POST':
        doctor = get_object_or_404(Doctor, id=doctor_id)
        reason = request.POST.get('reason', '')

        # Reject the doctor
        doctor.reject(reason)

        messages.warning(request, f'Shifokor {doctor.full_name} rad etildi.')

        return JsonResponse({
            'success': True,
            'message': 'Shifokor rad etildi'
        })

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@staff_member_required
def user_management(request):
    """User management page"""

    # Filter parameters
    user_type_filter = request.GET.get('user_type', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    users = User.objects.all()

    # Apply filters
    if user_type_filter != 'all':
        users = users.filter(user_type=user_type_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'verified':
        users = users.filter(is_verified=True)
    elif status_filter == 'unverified':
        users = users.filter(is_verified=False)

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)

    context = {
        'users': users_page,
        'user_types': User.USER_TYPES,
        'current_user_type': user_type_filter,
        'current_status': status_filter,
        'search_query': search_query,
    }

    return render(request, 'admin_panel/user_management.html', context)


@staff_member_required
def user_detail(request, user_id):
    """User detail page"""

    user = get_object_or_404(User, id=user_id)

    # Get additional info based on user type
    doctor_profile = None
    if user.is_doctor() and hasattr(user, 'doctor_profile'):
        doctor_profile = user.doctor_profile

    context = {
        'user': user,
        'doctor_profile': doctor_profile,
    }

    return render(request, 'admin_panel/user_detail.html', context)


@staff_member_required
def toggle_user_status(request, user_id):
    """Toggle user active status"""

    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)

        user.is_active = not user.is_active
        user.save()

        status_text = "faollashtirildi" if user.is_active else "faolsizlashtirildi"
        messages.success(request, f'Foydalanuvchi {user.get_full_name()} {status_text}.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Foydalanuvchi {status_text}',
                'is_active': user.is_active
            })

        return redirect('admin_panel:user_detail', user_id=user_id)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@staff_member_required
def hospital_management(request):
    """Hospital management page"""

    # Filter parameters
    search_query = request.GET.get('search', '')
    hospital_type_filter = request.GET.get('type', 'all')

    # Base queryset
    hospitals = Hospital.objects.all()

    # Apply filters
    if hospital_type_filter != 'all':
        hospitals = hospitals.filter(hospital_type=hospital_type_filter)

    if search_query:
        hospitals = hospitals.filter(
            Q(name__icontains=search_query) |
            Q(region__icontains=search_query) |
            Q(district__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(hospitals, 15)
    page_number = request.GET.get('page')
    hospitals_page = paginator.get_page(page_number)

    context = {
        'hospitals': hospitals_page,
        'hospital_types': Hospital.HOSPITAL_TYPES,
        'current_type': hospital_type_filter,
        'search_query': search_query,
    }

    return render(request, 'admin_panel/hospital_management.html', context)


@staff_member_required
def create_hospital_admin(request):
    """Create hospital admin user"""

    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email', '')
        hospital_id = request.POST.get('hospital_id')
        password = request.POST.get('password')

        try:
            # Check if user with this phone already exists
            if User.objects.filter(phone=phone).exists():
                messages.error(request, 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan.')
                return redirect('admin_panel:hospital_management')

            # Get hospital
            hospital = get_object_or_404(Hospital, id=hospital_id)

            # Create hospital admin user
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                user_type='hospital_admin',
                managed_hospital=hospital,
                is_verified=True,
                is_approved_by_admin=True,
                approved_by=request.user,
                approval_date=timezone.now()
            )

            messages.success(request, f'Shifoxona administratori {user.get_full_name()} muvaffaqiyatli yaratildi.')

        except Exception as e:
            messages.error(request, f'Xatolik: {str(e)}')

        return redirect('admin_panel:hospital_management')

    # GET request - show form
    hospitals = Hospital.objects.filter(is_active=True)
    context = {
        'hospitals': hospitals,
    }

    return render(request, 'admin_panel/create_hospital_admin.html', context)


@staff_member_required
def statistics_overview(request):
    """Statistics overview page"""

    # Time ranges
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    month_ago = today - timezone.timedelta(days=30)

    # User registration statistics
    user_registration_stats = {
        'today': User.objects.filter(created_at__date=today).count(),
        'this_week': User.objects.filter(created_at__date__gte=week_ago).count(),
        'this_month': User.objects.filter(created_at__date__gte=month_ago).count(),
    }

    # Doctor application statistics
    doctor_application_stats = {
        'pending': Doctor.objects.filter(verification_status='pending').count(),
        'approved_this_week': Doctor.objects.filter(
            verification_status='approved',
            user__approval_date__date__gte=week_ago
        ).count(),
        'rejected_this_week': Doctor.objects.filter(
            verification_status='rejected',
            updated_at__date__gte=week_ago
        ).count(),
    }

    # Consultation statistics
    consultation_statistics = {
        'total': Consultation.objects.count(),
        'this_week': Consultation.objects.filter(created_at__date__gte=week_ago).count(),
        'this_month': Consultation.objects.filter(created_at__date__gte=month_ago).count(),
        'by_status': Consultation.objects.values('status').annotate(count=Count('id')),
    }

    # Top performing doctors
    top_doctors = Doctor.objects.filter(
        verification_status='approved'
    ).order_by('-rating', '-total_reviews')[:10]

    # Most active hospitals
    hospital_stats = Hospital.objects.annotate(
        doctor_count=Count('doctors'),
        active_doctor_count=Count('doctors', filter=Q(doctors__is_available=True))
    ).order_by('-doctor_count')[:10]

    context = {
        'user_registration_stats': user_registration_stats,
        'doctor_application_stats': doctor_application_stats,
        'consultation_statistics': consultation_statistics,
        'top_doctors': top_doctors,
        'hospital_stats': hospital_stats,
    }

    return render(request, 'admin_panel/statistics.html', context)


@staff_member_required
def export_data(request):
    """Export data in various formats"""

    data_type = request.GET.get('type', 'users')
    format_type = request.GET.get('format', 'csv')

    if data_type == 'users':
        # Export users data
        users = User.objects.all().values(
            'id', 'first_name', 'last_name', 'phone', 'email',
            'user_type', 'is_active', 'is_verified', 'created_at'
        )
        data = list(users)

    elif data_type == 'doctors':
        # Export doctors data
        doctors = Doctor.objects.select_related('user').all()
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
                'verification_status': doctor.get_verification_status_display(),
                'created_at': doctor.created_at,
            })

    elif data_type == 'consultations':
        # Export consultations data
        consultations = Consultation.objects.select_related('patient', 'doctor').all()
        data = []
        for consultation in consultations:
            data.append({
                'id': consultation.id,
                'patient': consultation.patient.get_full_name(),
                'doctor': consultation.doctor.full_name,
                'status': consultation.get_status_display(),
                'consultation_type': consultation.get_consultation_type_display(),
                'created_at': consultation.created_at,
                'scheduled_date': consultation.scheduled_date,
            })

    else:
        return JsonResponse({'error': 'Invalid data type'}, status=400)

    if format_type == 'json':
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.json"'
        return response

    elif format_type == 'csv':
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.csv"'

        if data:
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        return response

    else:
        return JsonResponse({'error': 'Invalid format type'}, status=400)


@staff_member_required
def system_settings(request):
    """System settings page"""

    if request.method == 'POST':
        # Handle settings update
        # This would typically involve a Settings model
        messages.success(request, 'Sozlamalar muvaffaqiyatli yangilandi.')
        return redirect('admin_panel:system_settings')

    context = {
        # Add system settings here
    }

    return render(request, 'admin_panel/settings.html', context)