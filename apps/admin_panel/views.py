from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView

from apps.doctors.models import Doctor
from apps.doctors.serializers import DoctorSerializer
from apps.hospitals.models import Hospital, Regions, Districts
from apps.consultations.models import Consultation
from apps.hospitals.serializers import HospitalSerializer
from test import region
from .models import DoctorComplaint, DoctorComplaintFile

from .serializers import (
    AdminHospitalSerializer,
    AdminDoctorSerializer,
    AdminUserSerializer,
    DoctorComplaintSerializer,
    AdminDoctorComplaintSerializer,
    DoctorComplaintCreateSerializer,
    DoctorComplaintUpdateSerializer,
    DoctorComplaintFileSerializer,
    DoctorComplaintStatisticsSerializer
)

User = get_user_model()


class IsAdminPermission(permissions.BasePermission):
    """Custom permission to only allow admin users"""

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.is_staff
        )


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

    context = {
        'doctor': serializer.data,
        'consultation_stats': consultation_stats,
        'recent_consultations': list(recent_consultations.values()),
    }

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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

    serializer = HospitalSerializer(hospitals_page, many=True)

    data = {
        'hospitals': serializer.data,
        'pagination': {
            'current_page': hospitals_page.number,
            'total_pages': hospitals_page.paginator.num_pages,
            'has_next': hospitals_page.has_next(),
            'has_previous': hospitals_page.has_previous(),
            'total_items': hospitals_page.paginator.count,
        },
        'filters': {
            'hospital_types': dict(Hospital.HOSPITAL_TYPES),
            'current_type': hospital_type_filter,
            'search_query': search_query,
        }
    }

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_hospital_admin(request):
    """Create hospital admin user"""

    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username', '')
        hospital_id = request.POST.get('hospital_id')
        password = request.POST.get('password')
        region = request.POST.get('region', None)
        district = request.POST.get('district', None)
        region_ = Regions.objects.get(id=region)
        district_ = Districts.objects.get(id=district)

        try:
            # Check if user with this phone already exists
            if User.objects.filter(phone=phone).exists():
                messages.error(request, 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan.')
                return Response({'error': 'Telefon raqam allaqachon mavjud'}, status=400)

            # Get hospital
            hospital = get_object_or_404(Hospital, id=hospital_id)

            # Create hospital admin user
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                username=username,
                user_type='hospital_admin',
                managed_hospital=hospital,
                is_verified=True,
                is_approved_by_admin=True,
                approved_by=request.user,
                approval_date=timezone.now(),
                region=region_,
                district=district_,
            )

            messages.success(request, f'Shifoxona administratori {user.get_full_name()} muvaffaqiyatli yaratildi.')

        except Exception as e:
            messages.error(request, f'Xatolik: {str(e)}')
            return Response({'error': str(e)}, status=500)

        return Response(
            {
                'success': True,
                'message': f'Shifoxona administratori {first_name} {last_name} muvaffaqiyatli yaratildi.'
            },
            status=201
        )
    return Response({'error': 'Invalid request method'}, status=405)


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


class AdminHospitalViewSet(viewsets.ModelViewSet):
    """
    Hospital management ViewSet for admin panel
    Provides CRUD operations for hospitals
    """
    queryset = Hospital.objects.all()
    serializer_class = AdminHospitalSerializer
    permission_classes = [IsAdminPermission]

    def get_queryset(self):
        """Filter and search hospitals"""
        queryset = Hospital.objects.all()

        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )

        # Filter by hospital type
        hospital_type = self.request.query_params.get('type', None)
        if hospital_type:
            queryset = queryset.filter(hospital_type=hospital_type)

        # Filter by region
        region = self.request.query_params.get('region', None)
        if region:
            queryset = queryset.filter(region=region)

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Create a new hospital"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = serializer.save()

        return Response({
            'message': 'Shifoxona muvaffaqiyatli yaratildi',
            'hospital': AdminHospitalSerializer(hospital).data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update hospital information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        hospital = serializer.save()

        return Response({
            'message': 'Shifoxona ma\'lumotlari yangilandi',
            'hospital': AdminHospitalSerializer(hospital).data
        })

    def destroy(self, request, *args, **kwargs):
        """Delete hospital"""
        instance = self.get_object()

        # Check if hospital has doctors
        if instance.doctors.exists():
            return Response({
                'error': 'Bu shifoxonada shifokorlar mavjud. Avval shifokorlarni boshqa shifoxonaga ko\'chiring.'
            }, status=status.HTTP_400_BAD_REQUEST)

        instance.delete()
        return Response({
            'message': 'Shifoxona muvaffaqiyatli o\'chirildi'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        """Get all doctors in this hospital"""
        hospital = self.get_object()
        doctors = Doctor.objects.filter(hospital=hospital)
        serializer = AdminDoctorSerializer(doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get hospital statistics"""
        hospital = self.get_object()

        stats = {
            'total_doctors': hospital.doctors.count(),
            'active_doctors': hospital.doctors.filter(is_available=True).count(),
            'verified_doctors': hospital.doctors.filter(verification_status='approved').count(),
            'pending_doctors': hospital.doctors.filter(verification_status='pending').count(),
            'total_consultations': Consultation.objects.filter(
                doctor__hospital=hospital
            ).count(),
            'completed_consultations': Consultation.objects.filter(
                doctor__hospital=hospital,
                status='completed'
            ).count(),
            'average_rating': hospital.doctors.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
        }

        return Response(stats)


class AdminDoctorViewSet(viewsets.ModelViewSet):
    """
    Doctor management ViewSet for admin panel
    Provides CRUD operations for doctors with edit and delete functionality
    """
    queryset = Doctor.objects.select_related('user', 'hospital').all()
    serializer_class = AdminDoctorSerializer
    permission_classes = [IsAdminPermission]

    def get_queryset(self):
        """Filter and search doctors"""
        queryset = Doctor.objects.select_related('user', 'hospital').all()

        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(license_number__icontains=search) |
                Q(workplace__icontains=search)
            )

        # Filter by verification status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(verification_status=status_filter)

        # Filter by specialty
        specialty = self.request.query_params.get('specialty', None)
        if specialty:
            queryset = queryset.filter(specialty=specialty)

        # Filter by hospital
        hospital_id = self.request.query_params.get('hospital', None)
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        # Filter by availability
        is_available = self.request.query_params.get('available', None)
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available.lower() == 'true')

        return queryset.order_by('-created_at')

    def update(self, request, *args, **kwargs):
        """Update doctor information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Separate user data from doctor data
        user_data = {}
        doctor_data = {}

        user_fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone', 'is_active']

        for field, value in request.data.items():
            if field in user_fields:
                user_data[field] = value
            else:
                doctor_data[field] = value

        # Update user fields if provided
        if user_data:
            user = instance.user
            for field, value in user_data.items():
                setattr(user, field, value)
            user.save()

        # Update doctor fields
        serializer = self.get_serializer(instance, data=doctor_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()

        return Response({
            'message': 'Shifokor ma\'lumotlari yangilandi',
            'doctor': AdminDoctorSerializer(doctor).data
        })

    def destroy(self, request, *args, **kwargs):
        """Delete doctor and associated user"""
        instance = self.get_object()

        # Check for active consultations
        active_consultations = Consultation.objects.filter(
            doctor=instance,
            status__in=['scheduled', 'in_progress']
        ).count()

        if active_consultations > 0:
            return Response({
                'error': f'Bu shifokorning {active_consultations} ta faol konsultatsiyasi mavjud. Avval ularni yakunlang.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Delete user (this will cascade delete doctor profile)
        user = instance.user
        user.delete()

        return Response({
            'message': 'Shifokor muvaffaqiyatli o\'chirildi'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve doctor verification"""
        doctor = self.get_object()
        doctor.verification_status = 'approved'
        doctor.approved_by = request.user
        doctor.approved_at = timezone.now()
        doctor.save()

        # Also approve user
        doctor.user.is_approved_by_admin = True
        doctor.user.save()

        return Response({
            'message': 'Shifokor tasdiqlandi',
            'doctor': AdminDoctorSerializer(doctor).data
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject doctor verification"""
        doctor = self.get_object()
        reason = request.data.get('reason', '')

        doctor.verification_status = 'rejected'
        doctor.rejection_reason = reason
        doctor.rejected_by = request.user
        doctor.rejected_at = timezone.now()
        doctor.save()

        return Response({
            'message': 'Shifokor rad etildi',
            'doctor': AdminDoctorSerializer(doctor).data
        })

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle doctor availability"""
        doctor = self.get_object()
        doctor.is_available = not doctor.is_available
        doctor.save()

        status_text = "mavjud" if doctor.is_available else "mavjud emas"
        return Response({
            'message': f'Shifokor holati "{status_text}" ga o\'zgartirildi',
            'is_available': doctor.is_available
        })

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get doctor statistics"""
        doctor = self.get_object()

        # Get consultation stats
        total_consultations = Consultation.objects.filter(doctor=doctor).count()
        completed_consultations = Consultation.objects.filter(
            doctor=doctor, status='completed'
        ).count()

        stats = {
            'total_consultations': total_consultations,
            'completed_consultations': completed_consultations,
            'success_rate': (completed_consultations / total_consultations * 100) if total_consultations > 0 else 0,
            'rating': doctor.rating,
            'total_reviews': doctor.total_reviews,
            'profile_views': getattr(doctor, 'profile_views', 0),
            'earnings': getattr(doctor, 'total_earnings', 0),
        }

        return Response(stats)


class AdminDashboardAPIView(APIView):
    """
    Admin dashboard API with comprehensive statistics
    """
    permission_classes = [IsAdminPermission]

    @staticmethod
    def get(request):
        """Get admin dashboard statistics"""

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

        # Hospital statistics
        hospital_stats = {
            'total_hospitals': Hospital.objects.count(),
            'active_hospitals': Hospital.objects.filter(is_active=True).count(),
            'hospitals_with_doctors': Hospital.objects.annotate(
                doctor_count=Count('doctors')
            ).filter(doctor_count__gt=0).count(),
        }

        # Doctor statistics
        doctor_stats = {
            'total_doctors': Doctor.objects.count(),
            'verified_doctors': Doctor.objects.filter(verification_status='approved').count(),
            'pending_doctors': Doctor.objects.filter(verification_status='pending').count(),
            'rejected_doctors': Doctor.objects.filter(verification_status='rejected').count(),
            'available_doctors': Doctor.objects.filter(is_available=True).count(),
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
        pending_doctors = Doctor.objects.filter(
            verification_status='pending'
        ).order_by('-created_at')[:5]

        return Response({
            'user_stats': user_stats,
            'hospital_stats': hospital_stats,
            'doctor_stats': doctor_stats,
            'consultation_stats': consultation_stats,
            'recent_users': AdminUserSerializer(recent_users, many=True).data,
            'pending_doctors': AdminDoctorSerializer(pending_doctors, many=True).data,
        })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def export_data(request):
    """Export data in various formats"""

    data_type = request.GET.get('type', 'users')
    format_type = request.GET.get('format', 'json')

    if data_type == 'users':
        users = User.objects.all().values(
            'id', 'first_name', 'last_name', 'phone', 'email',
            'user_type', 'is_active', 'is_verified', 'created_at'
        )
        data = list(users)

    elif data_type == 'doctors':
        doctors = Doctor.objects.select_related('user', 'hospital').all()
        data = []
        for doctor in doctors:
            data.append({
                'id': doctor.id,
                'name': doctor.full_name(),
                'phone': doctor.user.phone,
                'email': doctor.user.email or '',
                'specialty': doctor.get_specialty_display(),
                'experience': doctor.experience,
                'rating': doctor.rating,
                'hospital': doctor.hospital.name if doctor.hospital else '',
                'verification_status': doctor.verification_status,
                'is_available': doctor.is_available,
                'created_at': doctor.created_at.isoformat(),
            })

    elif data_type == 'hospitals':
        hospitals = Hospital.objects.all()
        data = []
        for hospital in hospitals:
            data.append({
                'id': hospital.id,
                'name': hospital.name,
                'address': hospital.address,
                'phone': hospital.phone,
                'email': hospital.email or '',
                'hospital_type': hospital.get_hospital_type_display() if hasattr(hospital,
                                                                                 'get_hospital_type_display') else '',
                'region': getattr(hospital, 'region', ''),
                'district': getattr(hospital, 'district', ''),
                'doctor_count': hospital.doctors.count(),
                'is_active': getattr(hospital, 'is_active', True),
                'created_at': getattr(hospital, 'created_at', '').isoformat() if hasattr(hospital,
                                                                                         'created_at') else '',
            })

    else:
        return Response({'error': 'Invalid data type'}, status=400)

    return Response({
        'data': data,
        'count': len(data),
        'type': data_type,
        'format': format_type,
        'exported_at': timezone.now().isoformat()
    })


# Additional utility views
@api_view(['GET'])
@permission_classes([IsAdminPermission])
def get_filter_options(request):
    """Get filter options for admin panel"""

    return Response({
        'specialties': dict(Doctor.SPECIALTIES) if hasattr(Doctor, 'SPECIALTIES') else {},
        'verification_statuses': dict(Doctor.VERIFICATION_STATUS) if hasattr(Doctor, 'VERIFICATION_STATUS') else {},
        'hospital_types': dict(Hospital.HOSPITAL_TYPES) if hasattr(Hospital, 'HOSPITAL_TYPES') else {},
        'user_types': dict(User.USER_TYPE_CHOICES) if hasattr(User, 'USER_TYPE_CHOICES') else {},
        'regions': list(
            User.objects.values_list('region', flat=True).distinct().exclude(region__isnull=True).exclude(region='')),
    })


@api_view(['POST'])
@permission_classes([IsAdminPermission])
def bulk_actions(request):
    """Perform bulk actions on multiple items"""

    action = request.data.get('action')
    item_type = request.data.get('type')  # 'doctors' or 'hospitals'
    item_ids = request.data.get('ids', [])

    if not action or not item_type or not item_ids:
        return Response({'error': 'Action, type, and ids are required'}, status=400)

    if item_type == 'doctors':
        items = Doctor.objects.filter(id__in=item_ids)

        if action == 'approve':
            items.update(
                verification_status='approved',
                approved_by=request.user,
                approved_at=timezone.now()
            )
            # Also update user approval
            User.objects.filter(
                doctor_profile__in=items
            ).update(is_approved_by_admin=True)
            message = f'{items.count()} ta shifokor tasdiqlandi'

        elif action == 'reject':
            reason = request.data.get('reason', 'Admin tomonidan rad etildi')
            items.update(
                verification_status='rejected',
                rejection_reason=reason,
                rejected_by=request.user,
                rejected_at=timezone.now()
            )
            message = f'{items.count()} ta shifokor rad etildi'

        elif action == 'delete':
            count = items.count()
            # Delete users (will cascade to doctors)
            User.objects.filter(doctor_profile__in=items).delete()
            message = f'{count} ta shifokor o\'chirildi'

        else:
            return Response({'error': 'Invalid action for doctors'}, status=400)

    elif item_type == 'hospitals':
        items = Hospital.objects.filter(id__in=item_ids)

        if action == 'delete':
            # Check for hospitals with doctors
            hospitals_with_doctors = items.annotate(
                doctor_count=Count('doctors')
            ).filter(doctor_count__gt=0)

            if hospitals_with_doctors.exists():
                return Response({
                    'error': 'Ba\'zi shifoxonalarda shifokorlar mavjud. Avval ularni ko\'chiring.'
                }, status=400)

            count = items.count()
            items.delete()
            message = f'{count} ta shifoxona o\'chirildi'

        else:
            return Response({'error': 'Invalid action for hospitals'}, status=400)

    else:
        return Response({'error': 'Invalid item type'}, status=400)

    return Response({'message': message})


class DoctorComplaintViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor complaints
    Provides CRUD operations for DoctorComplaint model
    """
    queryset = DoctorComplaint.objects.select_related('doctor', 'doctor__user', 'doctor__hospital').prefetch_related('files')
    permission_classes = [IsAdminPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return DoctorComplaintCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DoctorComplaintUpdateSerializer
        elif self.action == 'list':
            return AdminDoctorComplaintSerializer
        return DoctorComplaintSerializer
    
    def get_queryset(self):
        """Filter and search complaints"""
        queryset = DoctorComplaint.objects.select_related(
            'doctor', 'doctor__user', 'doctor__hospital'
        ).prefetch_related('files')
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search) |
                Q(description__icontains=search) |
                Q(doctor__user__first_name__icontains=search) |
                Q(doctor__user__last_name__icontains=search) |
                Q(doctor__user__phone__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by complaint type
        complaint_type = self.request.query_params.get('type', None)
        if complaint_type:
            queryset = queryset.filter(complaint_type=complaint_type)
        
        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by doctor
        doctor_id = self.request.query_params.get('doctor', None)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        # Filter by hospital
        hospital_id = self.request.query_params.get('hospital', None)
        if hospital_id:
            queryset = queryset.filter(doctor__hospital_id=hospital_id)
        
        # Date filtering
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new complaint"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()
        
        return Response({
            'message': 'Shikoyat muvaffaqiyatli yaratildi',
            'complaint': DoctorComplaintSerializer(complaint).data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update complaint (admin only)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Save resolution notes if provided
        resolution_notes = request.data.get('resolution_notes')
        if resolution_notes:
            # You might want to add a resolution_notes field to the model
            pass
        
        complaint = serializer.save()
        
        return Response({
            'message': 'Shikoyat holati yangilandi',
            'complaint': DoctorComplaintSerializer(complaint).data
        })
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark complaint as resolved"""
        complaint = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        if not resolution_notes:
            return Response({
                'error': 'Shikoyatni yechish uchun izoh majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        complaint.status = 'resolved'
        complaint.resolution_notes = resolution_notes
        complaint.save()
        
        return Response({
            'message': 'Shikoyat yechilgan deb belgilandi',
            'complaint': DoctorComplaintSerializer(complaint).data
        })
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close complaint"""
        complaint = self.get_object()
        
        if complaint.status == 'resolved':
            return Response({
                'error': 'Faqat pending shikoyatlarni yopish mumkin'
            }, status=status.HTTP_400_BAD_REQUEST)

        resolution_notes = request.data.get('resolution_notes', '')

        if not resolution_notes:
            return Response({
                'error': 'Shikoyatni yopish uchun izoh majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        complaint.status = 'closed'
        complaint.resolution_notes = resolution_notes
        complaint.save()
        
        return Response({
            'message': 'Shikoyat yopildi',
            'complaint': DoctorComplaintSerializer(complaint).data
        })
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get all files for this complaint"""
        complaint = self.get_object()
        files = complaint.files.all()
        serializer = DoctorComplaintFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get complaint statistics"""
        from django.db.models import Count, Avg, F
        from django.utils import timezone
        from datetime import timedelta
        
        # Basic counts
        total_complaints = DoctorComplaint.objects.count()
        
        # By status
        status_counts = DoctorComplaint.objects.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        # By type
        type_counts = DoctorComplaint.objects.values('complaint_type').annotate(count=Count('id'))
        type_dict = {item['complaint_type']: item['count'] for item in type_counts}
        
        # By priority
        priority_counts = DoctorComplaint.objects.values('priority').annotate(count=Count('id'))
        priority_dict = {item['priority']: item['count'] for item in priority_counts}
        
        # Time-based statistics
        now = timezone.now()
        this_week = now - timedelta(weeks=1)
        this_month = now - timedelta(days=30)
        
        complaints_this_week = DoctorComplaint.objects.filter(created_at__gte=this_week).count()
        complaints_this_month = DoctorComplaint.objects.filter(created_at__gte=this_month).count()
        
        # Average resolution time (for resolved complaints)
        resolved_complaints = DoctorComplaint.objects.filter(status='resolved')
        avg_resolution_days = 0
        if resolved_complaints.exists():
            # This is a simplified calculation - you might want to track actual resolution dates
            total_days = sum((complaint.updated_at - complaint.created_at).days 
                           for complaint in resolved_complaints)
            avg_resolution_days = total_days / resolved_complaints.count()
        
        stats = {
            'total_complaints': total_complaints,
            'in_progress_complaints': status_dict.get('in_progress', 0),
            'resolved_complaints': status_dict.get('resolved', 0),
            'closed_complaints': status_dict.get('closed', 0),
            'general_complaints': type_dict.get('general', 0),
            'service_complaints': type_dict.get('service', 0),
            'billing_complaints': type_dict.get('billing', 0),
            'urgent_complaints': priority_dict.get('urgent', 0),
            'high_complaints': priority_dict.get('high', 0),
            'medium_complaints': priority_dict.get('medium', 0),
            'low_complaints': priority_dict.get('low', 0),
            'complaints_this_month': complaints_this_month,
            'complaints_this_week': complaints_this_week,
            'average_resolution_days': round(avg_resolution_days, 2)
        }
        
        serializer = DoctorComplaintStatisticsSerializer(stats)
        return Response(serializer.data)


class DoctorComplaintFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing complaint files
    Provides CRUD operations for DoctorComplaintFile model
    """
    queryset = DoctorComplaintFile.objects.select_related('complaint').all()
    serializer_class = DoctorComplaintFileSerializer
    permission_classes = [IsAdminPermission]
    
    def get_queryset(self):
        """Filter files by complaint"""
        queryset = DoctorComplaintFile.objects.select_related('complaint')
        
        # Filter by complaint
        complaint_id = self.request.query_params.get('complaint', None)
        if complaint_id:
            queryset = queryset.filter(complaint_id=complaint_id)
        
        return queryset.order_by('-uploaded_at')
    
    def create(self, request, *args, **kwargs):
        """Upload a file for a complaint"""
        complaint_id = request.data.get('complaint')
        if not complaint_id:
            return Response({
                'error': 'Shikoyat ID majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            complaint = DoctorComplaint.objects.get(id=complaint_id)
        except DoctorComplaint.DoesNotExist:
            return Response({
                'error': 'Shikoyat topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.save(complaint=complaint)
        
        return Response({
            'message': 'Fayl muvaffaqiyatli yuklandi',
            'file': DoctorComplaintFileSerializer(file_obj, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a complaint file"""
        instance = self.get_object()
        
        # Delete the physical file
        if instance.file:
            instance.file.delete()
        
        instance.delete()
        
        return Response({
            'message': 'Fayl muvaffaqiyatli o\'chirildi'
        }, status=status.HTTP_204_NO_CONTENT)


# Doctor-specific views for their own complaints
class DoctorComplaintPermission(permissions.BasePermission):
    """Permission for doctors to access their own complaints"""

    def has_permission(self, request, view):
        """Check if user is a verified doctor"""
        if not request.user.is_authenticated:
            return False

        print("User:", request.user,  hasattr(request.user, 'doctor_profile'))
        
        # Check if user has doctor profile and is verified
        return (
            hasattr(request.user, 'doctor_profile') and
            request.user.doctor_profile.verification_status == 'approved'
        )
    
    def has_object_permission(self, request, view, obj):
        """Check if doctor can access specific complaint"""
        return obj.doctor.user == request.user


@api_view(['POST'])
@permission_classes([DoctorComplaintPermission])
def doctor_create_complaint(request):
    """Create a new complaint by doctor"""
    
    # Get doctor instance
    doctor = request.user.doctor_profile
    
    # Prepare data
    data = request.data.copy()
    data['doctor'] = doctor.id
    
    # Create complaint
    serializer = DoctorComplaintCreateSerializer(data=data)
    if serializer.is_valid():
        complaint = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Shikoyat muvaffaqiyatli yaratildi',
            'complaint': DoctorComplaintSerializer(complaint).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([DoctorComplaintPermission])
def doctor_complaint_list(request):
    """Get list of doctor's own complaints"""
    
    # Get doctor instance
    doctor = request.user.doctor_profile
    
    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    complaint_type = request.GET.get('type', 'all')
    priority = request.GET.get('priority', 'all')
    search = request.GET.get('search', '')
    
    # Base queryset - only doctor's own complaints
    queryset = DoctorComplaint.objects.filter(
        doctor=doctor
    ).select_related('doctor', 'doctor__user').prefetch_related('files')
    
    # Apply filters
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    
    if complaint_type != 'all':
        queryset = queryset.filter(complaint_type=complaint_type)
    
    if priority != 'all':
        queryset = queryset.filter(priority=priority)
    
    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    page_size = int(request.GET.get('page_size', 10))
    page_number = request.GET.get('page', 1)
    
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)
    
    # Serialize data
    serializer = DoctorComplaintSerializer(page_obj, many=True)
    
    return Response({
        'complaints': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': page_size
        },
        'filters': {
            'status_options': dict(DoctorComplaint.STATUS),
            'type_options': dict(DoctorComplaint.TYPES),
            'priority_options': dict(DoctorComplaint.PRIORITY),
            'current_filters': {
                'status': status_filter,
                'type': complaint_type,
                'priority': priority,
                'search': search
            }
        },
        'statistics': {
            'total_complaints': doctor.complaints.count(),
            'in_progress': doctor.complaints.filter(status='in_progress').count(),
            'resolved': doctor.complaints.filter(status='resolved').count(),
            'closed': doctor.complaints.filter(status='closed').count(),
        }
    })


@api_view(['GET'])
@permission_classes([DoctorComplaintPermission])
def doctor_complaint_detail(request, complaint_id):
    """Get specific complaint details for doctor"""
    
    try:
        complaint = DoctorComplaint.objects.select_related(
            'doctor', 'doctor__user'
        ).prefetch_related('files').get(
            id=complaint_id,
            doctor=request.user.doctor_profile
        )
    except DoctorComplaint.DoesNotExist:
        return Response({
            'error': 'Shikoyat topilmadi yoki sizga tegishli emas'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = DoctorComplaintSerializer(complaint)
    
    return Response({
        'complaint': serializer.data
    })
