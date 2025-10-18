from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import WalletTransaction
from apps.consultations.models import Consultation
from apps.doctors.models import ChargeLog, Doctor
from apps.doctors.serializers import DoctorSerializer
from apps.hospitals.models import Districts, Hospital, Regions
from apps.hospitals.serializers import HospitalSerializer

from .models import DoctorComplaint, DoctorComplaintFile
from .serializers import (
    AdminDoctorComplaintSerializer,
    AdminDoctorSerializer,
    AdminHospitalAdminSerializer,
    AdminHospitalAdminUpdateSerializer,
    AdminHospitalSerializer,
    AdminUserSerializer,
    ChargeLogSerializer,
    DoctorComplaintCreateSerializer,
    DoctorComplaintFileSerializer,
    DoctorComplaintSerializer,
    DoctorComplaintStatisticsSerializer,
    DoctorComplaintUpdateSerializer,
    DoctorStatisticsSerializer,
    DoctorStatisticsSummarySerializer,
    TransactionStatisticsSerializer,
    WalletTransactionSerializer,
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

    # Get wallet information
    wallet_data = None
    if hasattr(doctor.user, 'wallet'):
        wallet = doctor.user.wallet
        wallet_data = {
            'balance': wallet.balance,
            'total_spent': wallet.total_spent,
            'total_topped_up': wallet.total_topped_up,
            'is_blocked': wallet.is_blocked,
            'created_at': wallet.created_at,
            'updated_at': wallet.updated_at,
        }

    # Get recent transactions
    transactions_data = []
    if hasattr(doctor.user, 'wallet'):
        recent_transactions = WalletTransaction.objects.filter(
            wallet=doctor.user.wallet
        ).order_by('-created_at')[:20]
        transactions_serializer = WalletTransactionSerializer(
            recent_transactions,
            many=True,
            context={'request': request}
        )
        transactions_data = transactions_serializer.data

    context = {
        'doctor': serializer.data,
        'consultation_stats': consultation_stats,
        'recent_consultations': list(recent_consultations.values()),
        'wallet': wallet_data,
        'transactions': transactions_data,
    }

    return JsonResponse(context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_doctor(request, doctor_id):
    """Approve doctor"""

    if request.method == 'POST':
        doctor = get_object_or_404(Doctor, id=doctor_id)

        # Check if doctor has a wallet
        if not hasattr(doctor.user, 'wallet'):
            return JsonResponse({
                'success': False,
                'error': 'Shifokor hamyoni topilmadi'
            }, status=400)

        wallet = doctor.user.wallet

        # Check if wallet has sufficient balance (250,000 sums)
        required_amount = 250000
        if wallet.balance < required_amount:
            return JsonResponse({
                'success': False,
                'error': f'Hamyonda yetarli mablag\' yo\'q. Kerakli summa: {required_amount:,.0f} so\'m, Mavjud: {wallet.balance:,.2f} so\'m'
            }, status=400)

        # Check if wallet is blocked
        if wallet.is_blocked:
            return JsonResponse({
                'success': False,
                'error': 'Hamyon bloklangan'
            }, status=400)

        try:
            # Deduct the approval fee from wallet
            wallet.deduct_balance(
                amount=required_amount,
                description="Shifokor tasdiqlash to'lovi / Doctor approval fee"
            )

            # Approve the doctor
            doctor.approve(request.user)

            messages.success(request, f'Shifokor {doctor.full_name} muvaffaqiyatli tasdiqlandi.')

            return JsonResponse({
                'success': True,
                'message': 'Shifokor tasdiqlandi',
                'amount_charged': required_amount,
                'remaining_balance': float(wallet.balance)
            })

        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'To\'lov xatoligi: {str(e)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Xatolik: {str(e)}'
            }, status=500)

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
        phone = request.data.get('phone')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        username = request.data.get('username', '')
        hospital_id = request.data.get('hospital_id')
        password = request.data.get('password')
        region_id = request.data.get('region', None)
        district = request.data.get('district', None)

        if region_id:
            region_ = Regions.objects.get(id=int(region_id))
            print(region_, type(region_), "region_id")
        else:
            region_ = None
        if district:
            district_ = Districts.objects.get(id=int(district))
            print(district_, type(district_), "district_id")
        else:
            district_ = None
        gender = request.POST.get('gender', None)
        birth_date = request.POST.get('birth_date', None)

        try:
            # Check if user with this phone already exists
            if User.objects.filter(phone=phone).exists():
                messages.error(request, 'Bu telefon raqam allaqachon ro\'yxatdan o\'tgan.')
                return Response({'error': 'Telefon raqam allaqachon mavjud'}, status=400)
            print(hospital_id, type(hospital_id), "hospital_id")
            # Get hospital
            hospital = get_object_or_404(Hospital, id=hospital_id)

            print("hospital", hospital)
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Bu username allaqachon ro\'yxatdan o\'tgan.')
                return Response({'error': 'Username allaqachon mavjud'}, status=400)

            # Create hospital admin user
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type='hospital_admin',
                managed_hospital=hospital,
                username=username,
                is_verified=True,
                is_approved_by_admin=True,
                approved_by=request.user,
                approval_date=timezone.now(),
                region=region_,
                district=district_,
                gender=gender,
                birth_date=birth_date
            )
            user.username = username if username else f'admin_{hospital.id}_{phone}'
            user.gender = gender if gender else 'male'
            user.save()

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

    def retrieve(self, request, *args, **kwargs):
        """Get doctor detail with wallet and transaction information"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get wallet information
        wallet_data = None
        if hasattr(instance.user, 'wallet'):
            wallet = instance.user.wallet
            wallet_data = {
                'balance': wallet.balance,
                'total_spent': wallet.total_spent,
                'total_topped_up': wallet.total_topped_up,
                'is_blocked': wallet.is_blocked,
                'created_at': wallet.created_at,
                'updated_at': wallet.updated_at,
            }

        # Get recent transactions
        transactions_data = []
        if hasattr(instance.user, 'wallet'):
            recent_transactions = WalletTransaction.objects.filter(
                wallet=instance.user.wallet
            ).order_by('-created_at')[:20]
            transactions_serializer = WalletTransactionSerializer(
                recent_transactions,
                many=True,
                context={'request': request}
            )
            transactions_data = transactions_serializer.data

        return Response({
            'doctor': serializer.data,
            'wallet': wallet_data,
            'transactions': transactions_data,
        })

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


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def hospital_admin_list(request):
    """Get list of all hospital administrators for admin panel"""

    # Filter parameters
    search_query = request.GET.get('search', '')
    hospital_filter = request.GET.get('hospital', 'all')
    status_filter = request.GET.get('status', 'all')
    region_filter = request.GET.get('region', 'all')

    # Base queryset - only hospital admin users
    queryset = User.objects.filter(
        user_type='hospital_admin'
    ).select_related('managed_hospital', 'region', 'district', 'approved_by')

    # Apply filters
    if search_query:
        queryset = queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(managed_hospital__name__icontains=search_query)
        )

    if hospital_filter != 'all':
        queryset = queryset.filter(managed_hospital_id=hospital_filter)

    if status_filter == 'active':
        queryset = queryset.filter(is_active=True, is_verified=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)
    elif status_filter == 'pending':
        queryset = queryset.filter(is_verified=False)

    if region_filter != 'all':
        queryset = queryset.filter(region_id=region_filter)

    # Pagination
    from django.core.paginator import Paginator
    page_size = int(request.GET.get('page_size', 20))
    page_number = request.GET.get('page', 1)

    paginator = Paginator(queryset.order_by('-created_at'), page_size)
    page_obj = paginator.get_page(page_number)

    # Serialize data
    serializer = AdminHospitalAdminSerializer(page_obj, many=True)

    # Get filter options
    hospitals = Hospital.objects.filter(administrators__isnull=False).distinct().values('id', 'name')
    regions = User.objects.filter(
        user_type='hospital_admin',
        region__isnull=False
    ).values_list('region__id', 'region__name').distinct()

    # Statistics
    total_admins = User.objects.filter(user_type='hospital_admin').count()
    active_admins = User.objects.filter(
        user_type='hospital_admin',
        is_active=True,
        is_verified=True
    ).count()
    pending_admins = User.objects.filter(
        user_type='hospital_admin',
        is_verified=False
    ).count()

    return Response({
        'hospital_admins': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': page_size
        },
        'filters': {
            'hospitals': list(hospitals),
            'regions': [{'id': r[0], 'name': r[1]} for r in regions],
            'current_filters': {
                'search': search_query,
                'hospital': hospital_filter,
                'status': status_filter,
                'region': region_filter
            }
        },
        'statistics': {
            'total_admins': total_admins,
            'active_admins': active_admins,
            'pending_admins': pending_admins,
            'inactive_admins': total_admins - active_admins
        }
    })


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAdminPermission])
def hospital_admin_detail(request, admin_id):
    """Get, update, or partially update a specific hospital administrator"""

    # Get the hospital admin user
    try:
        admin_user = User.objects.select_related(
            'managed_hospital', 'region', 'district', 'approved_by'
        ).get(
            id=admin_id,
            user_type='hospital_admin'
        )
    except User.DoesNotExist:
        return Response({
            'error': 'Shifoxona administratori topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Return detailed information about the hospital admin
        serializer = AdminHospitalAdminSerializer(admin_user)

        # Additional statistics for this admin
        admin_stats = {
            'managed_hospital_info': None,
            'recent_activity': None
        }

        if admin_user.managed_hospital:
            hospital = admin_user.managed_hospital
            admin_stats['managed_hospital_info'] = {
                'doctors_count': hospital.doctors.count(),
                'active_doctors_count': hospital.doctors.filter(is_available=True).count(),
                'verified_doctors_count': hospital.doctors.filter(verification_status='approved').count(),
                'total_consultations': Consultation.objects.filter(doctor__hospital=hospital).count(),
                'hospital_rating': hospital.rating,
                'hospital_services_count': hospital.services.count() if hasattr(hospital, 'services') else 0
            }

        return Response({
            'hospital_admin': serializer.data,
            'statistics': admin_stats
        })

    elif request.method in ['PUT', 'PATCH']:
        # Update hospital admin information
        partial = request.method == 'PATCH'
        serializer = AdminHospitalAdminUpdateSerializer(
            admin_user,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            updated_admin = serializer.save()

            # Return updated data
            response_serializer = AdminHospitalAdminSerializer(updated_admin)
            return Response({
                'message': 'Shifoxona administratori ma\'lumotlari muvaffaqiyatli yangilandi',
                'hospital_admin': response_serializer.data
            })

        return Response({
            'error': 'Xatolik yuz berdi',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminPermission])
def hospital_admin_activate_deactivate(request, admin_id):
    """Activate or deactivate a hospital administrator"""

    try:
        admin_user = User.objects.get(
            id=admin_id,
            user_type='hospital_admin'
        )
    except User.DoesNotExist:
        return Response({
            'error': 'Shifoxona administratori topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    if action not in ['activate', 'deactivate']:
        return Response({
            'error': 'Yaroqsiz harakat. "activate" yoki "deactivate" bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)

    admin_user.is_active = action == 'activate'
    admin_user.save()

    status_text = "faollashtirildi" if admin_user.is_active else "faolsizlantirildi"
    return Response({
        'message': f'Administrator {admin_user.get_full_name()} {status_text}',
        'is_active': admin_user.is_active
    })


@api_view(['POST'])
@permission_classes([IsAdminPermission])
def hospital_admin_verify(request, admin_id):
    """Verify a hospital administrator"""

    try:
        admin_user = User.objects.get(
            id=admin_id,
            user_type='hospital_admin'
        )
    except User.DoesNotExist:
        return Response({
            'error': 'Shifoxona administratori topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    if admin_user.is_verified:
        return Response({
            'error': 'Administrator allaqachon tasdiqlangan'
        }, status=status.HTTP_400_BAD_REQUEST)

    admin_user.is_verified = True
    admin_user.is_approved_by_admin = True
    admin_user.approved_by = request.user
    admin_user.approval_date = timezone.now()
    admin_user.save()

    return Response({
        'message': f'Administrator {admin_user.get_full_name()} tasdiqlandi',
        'is_verified': admin_user.is_verified
    })


@api_view(['DELETE'])
@permission_classes([IsAdminPermission])
def hospital_admin_delete(request, admin_id):
    """Delete a hospital administrator"""

    try:
        admin_user = User.objects.get(
            id=admin_id,
            user_type='hospital_admin'
        )
    except User.DoesNotExist:
        return Response({
            'error': 'Shifoxona administratori topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    # Check if this admin is currently managing any active operations
    managed_hospital = admin_user.managed_hospital
    admin_name = admin_user.get_full_name()

    # Additional security: Prevent deletion if admin is the only admin for a hospital
    if managed_hospital:
        other_admins = User.objects.filter(
            user_type='hospital_admin',
            managed_hospital=managed_hospital,
            is_active=True
        ).exclude(id=admin_id)

        if not other_admins.exists():
            return Response({
                'error': f'Bu administrator {managed_hospital.name} shifoxonasining yagona administratori. '
                        'Avval boshqa administrator tayinlang.'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Optional: Check for recent activity or pending operations
    # You can add additional checks here based on your business logic

    # Get confirmation from request (optional safety measure)
    confirm_deletion = request.data.get('confirm', False)
    if not confirm_deletion:
        return Response({
            'error': 'O\'chirishni tasdiqlash uchun "confirm": true yuborishingiz kerak',
            'warning': f'Administrator {admin_name} o\'chiriladi. Bu harakat bekor qilib bo\'lmaydi.',
            'managed_hospital': managed_hospital.name if managed_hospital else None
        }, status=status.HTTP_400_BAD_REQUEST)

    # Store information for response before deletion
    hospital_name = managed_hospital.name if managed_hospital else None

    # Perform the deletion
    admin_user.delete()

    return Response({
        'message': f'Shifoxona administratori {admin_name} muvaffaqiyatli o\'chirildi',
        'deleted_admin': {
            'id': admin_id,
            'name': admin_name,
            'managed_hospital': hospital_name
        }
    }, status=status.HTTP_200_OK)


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
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

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

    doctor_id = request.GET.get('doctor_id', None)
    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

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
            Q(description__icontains=search) |
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search)
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


# ==================== Transaction Management APIs ====================

@api_view(['GET'])
@permission_classes([IsAdminPermission])
def wallet_transactions_list(request):
    """
    Get all wallet transactions with filtering and pagination
    Supports filters: user_type, transaction_type, status, date_from, date_to, search
    """
    # Base queryset
    queryset = WalletTransaction.objects.select_related(
        'wallet', 'wallet__user'
    ).all()

    # Apply filters
    user_type = request.GET.get('user_type', None)
    if user_type:
        queryset = queryset.filter(wallet__user__user_type=user_type)

    transaction_type = request.GET.get('transaction_type', None)
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)

    status_filter = request.GET.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Date filtering
    date_from = request.GET.get('date_from', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = request.GET.get('date_to', None)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    # Search by user name or phone
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(wallet__user__first_name__icontains=search) |
            Q(wallet__user__last_name__icontains=search) |
            Q(wallet__user__phone__icontains=search) |
            Q(description__icontains=search)
        )

    # Order by latest first
    queryset = queryset.order_by('-created_at')

    # Pagination
    paginator = Paginator(queryset, int(request.GET.get('page_size', 20)))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Serialize
    serializer = WalletTransactionSerializer(page_obj, many=True)

    return Response({
        'transactions': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': int(request.GET.get('page_size', 20))
        },
        'filters': {
            'transaction_types': dict(WalletTransaction.TRANSACTION_TYPES),
            'statuses': dict(WalletTransaction.TRANSACTION_STATUS),
            'current_filters': {
                'user_type': user_type,
                'transaction_type': transaction_type,
                'status': status_filter,
                'date_from': date_from,
                'date_to': date_to,
                'search': search
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def doctor_charges_list(request):
    """
    Get all doctor charges (ChargeLog) with filtering and pagination
    Supports filters: doctor_id, hospital_id, charge_type, date_from, date_to, search
    """
    # Base queryset
    queryset = ChargeLog.objects.select_related(
        'doctor', 'doctor__user', 'doctor__hospital', 'user'
    ).all()

    # Apply filters
    doctor_id = request.GET.get('doctor_id', None)
    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

    hospital_id = request.GET.get('hospital_id', None)
    if hospital_id:
        queryset = queryset.filter(doctor__hospital_id=hospital_id)

    charge_type = request.GET.get('charge_type', None)
    if charge_type:
        queryset = queryset.filter(charge_type=charge_type)

    # Date filtering
    date_from = request.GET.get('date_from', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = request.GET.get('date_to', None)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    # Search by doctor name or phone
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search) |
            Q(doctor__user__phone__icontains=search)
        )

    # Order by latest first
    queryset = queryset.order_by('-created_at')

    # Pagination
    paginator = Paginator(queryset, int(request.GET.get('page_size', 20)))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Serialize
    serializer = ChargeLogSerializer(page_obj, many=True)

    return Response({
        'charges': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': int(request.GET.get('page_size', 20))
        },
        'filters': {
            'charge_types': dict(ChargeLog.CHARGE_TYPES),
            'current_filters': {
                'doctor_id': doctor_id,
                'hospital_id': hospital_id,
                'charge_type': charge_type,
                'date_from': date_from,
                'date_to': date_to,
                'search': search
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def hospital_transactions(request, hospital_id):
    """
    Get all transactions for a specific hospital
    Shows all ChargeLog entries for doctors in this hospital
    """
    # Verify hospital exists
    hospital = get_object_or_404(Hospital, id=hospital_id)

    # Get all charge logs for doctors in this hospital
    queryset = ChargeLog.objects.select_related(
        'doctor', 'doctor__user', 'doctor__hospital', 'user'
    ).filter(doctor__hospital=hospital)

    # Apply filters
    charge_type = request.GET.get('charge_type', None)
    if charge_type:
        queryset = queryset.filter(charge_type=charge_type)

    # Date filtering
    date_from = request.GET.get('date_from', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = request.GET.get('date_to', None)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    # Search by doctor name
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search) |
            Q(doctor__user__phone__icontains=search)
        )

    # Order by latest first
    queryset = queryset.order_by('-created_at')

    # Calculate statistics
    from django.db.models import Count, Sum
    stats = queryset.aggregate(
        total_amount=Sum('amount'),
        total_transactions=Count('id')
    )

    # Pagination
    paginator = Paginator(queryset, int(request.GET.get('page_size', 20)))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Serialize
    serializer = ChargeLogSerializer(page_obj, many=True)

    return Response({
        'hospital': {
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address
        },
        'transactions': serializer.data,
        'statistics': {
            'total_amount': stats['total_amount'] or 0,
            'total_transactions': stats['total_transactions']
        },
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': int(request.GET.get('page_size', 20))
        },
        'filters': {
            'charge_types': dict(ChargeLog.CHARGE_TYPES),
            'current_filters': {
                'charge_type': charge_type,
                'date_from': date_from,
                'date_to': date_to,
                'search': search
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def doctor_transactions(request, doctor_id):
    """
    Get all transactions for a specific doctor
    Shows ChargeLog entries for this doctor
    """
    # Verify doctor exists
    doctor = get_object_or_404(Doctor, id=doctor_id)

    # Get all charge logs for this doctor
    queryset = ChargeLog.objects.select_related(
        'doctor', 'doctor__user', 'doctor__hospital', 'user'
    ).filter(doctor=doctor)

    # Apply filters
    charge_type = request.GET.get('charge_type', None)
    if charge_type:
        queryset = queryset.filter(charge_type=charge_type)

    # Date filtering
    date_from = request.GET.get('date_from', None)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = request.GET.get('date_to', None)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    # Order by latest first
    queryset = queryset.order_by('-created_at')

    # Calculate statistics
    from django.db.models import Count, Sum
    stats = queryset.aggregate(
        total_amount=Sum('amount'),
        total_transactions=Count('id')
    )

    # Get wallet info
    wallet_info = {}
    if hasattr(doctor.user, 'wallet'):
        wallet = doctor.user.wallet
        wallet_info = {
            'balance': float(wallet.balance),
            'total_spent': float(wallet.total_spent),
            'total_topped_up': float(wallet.total_topped_up),
            'is_blocked': wallet.is_blocked
        }

    # Pagination
    paginator = Paginator(queryset, int(request.GET.get('page_size', 20)))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Serialize
    serializer = ChargeLogSerializer(page_obj, many=True)

    return Response({
        'doctor': {
            'id': doctor.id,
            'name': doctor.user.get_full_name(),
            'phone': doctor.user.phone,
            'specialty': doctor.get_specialty_display(),
            'hospital': doctor.hospital.name if doctor.hospital else None,
            'wallet': wallet_info
        },
        'transactions': serializer.data,
        'statistics': {
            'total_amount': stats['total_amount'] or 0,
            'total_transactions': stats['total_transactions']
        },
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': int(request.GET.get('page_size', 20))
        },
        'filters': {
            'charge_types': dict(ChargeLog.CHARGE_TYPES),
            'current_filters': {
                'charge_type': charge_type,
                'date_from': date_from,
                'date_to': date_to
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def transaction_statistics(request):
    """
    Get comprehensive transaction statistics
    """
    from datetime import timedelta

    from django.db.models import Count, Sum

    now = timezone.now()
    today = now.date()
    this_week_start = now - timedelta(weeks=1)
    this_month_start = now - timedelta(days=30)

    # Wallet transaction statistics
    wallet_stats = WalletTransaction.objects.aggregate(
        total_transactions=Count('id'),
        total_amount=Sum('amount'),
        credit_count=Count('id', filter=Q(transaction_type='credit')),
        credit_amount=Sum('amount', filter=Q(transaction_type='credit')),
        debit_count=Count('id', filter=Q(transaction_type='debit')),
        debit_amount=Sum('amount', filter=Q(transaction_type='debit')),
        transactions_today=Count('id', filter=Q(created_at__date=today)),
        transactions_this_week=Count('id', filter=Q(created_at__gte=this_week_start)),
        transactions_this_month=Count('id', filter=Q(created_at__gte=this_month_start))
    )

    # Doctor charge statistics
    charge_stats = ChargeLog.objects.aggregate(
        total_doctor_charges=Count('id'),
        total_charge_amount=Sum('amount')
    )

    # Combine statistics
    stats = {
        'total_transactions': wallet_stats['total_transactions'] or 0,
        'total_amount': wallet_stats['total_amount'] or 0,
        'credit_count': wallet_stats['credit_count'] or 0,
        'credit_amount': wallet_stats['credit_amount'] or 0,
        'debit_count': wallet_stats['debit_count'] or 0,
        'debit_amount': wallet_stats['debit_amount'] or 0,
        'total_doctor_charges': charge_stats['total_doctor_charges'] or 0,
        'total_charge_amount': charge_stats['total_charge_amount'] or 0,
        'transactions_today': wallet_stats['transactions_today'] or 0,
        'transactions_this_week': wallet_stats['transactions_this_week'] or 0,
        'transactions_this_month': wallet_stats['transactions_this_month'] or 0
    }

    serializer = TransactionStatisticsSerializer(stats)
    return Response(serializer.data)


# ==================== Doctor Statistics APIs ====================

@api_view(['GET'])
@permission_classes([IsAdminPermission])
def doctor_statistics_detail(request, doctor_id):
    """
    Get comprehensive statistics for a specific doctor
    """
    from django.db.models import Count, Sum

    # Get doctor
    doctor = get_object_or_404(
        Doctor.objects.select_related('user', 'hospital'),
        id=doctor_id
    )

    # Get charge statistics
    charge_stats = ChargeLog.objects.filter(doctor=doctor).aggregate(
        total_searches=Count('id', filter=Q(charge_type='search')),
        total_card_views=Count('id', filter=Q(charge_type='view_card')),
        total_phone_views=Count('id', filter=Q(charge_type='view_phone')),
        total_charges=Count('id'),
        total_charge_amount=Sum('amount')
    )

    # Calculate success rate
    success_rate = 0
    if doctor.total_consultations > 0:
        success_rate = round((doctor.successful_consultations / doctor.total_consultations) * 100, 2)

    # Get wallet info
    wallet_balance = None
    if hasattr(doctor.user, 'wallet'):
        wallet_balance = float(doctor.user.wallet.balance)

    # Prepare statistics
    stats = {
        'doctor_id': doctor.id,
        'doctor_name': doctor.user.get_full_name(),
        'doctor_phone': doctor.user.phone,
        'doctor_specialty': doctor.specialty,
        'doctor_specialty_display': doctor.get_specialty_display(),
        'hospital_name': doctor.hospital.name if doctor.hospital else None,

        # View statistics
        'total_profile_views': doctor.profile_views,
        'weekly_views': doctor.weekly_views,
        'monthly_views': doctor.monthly_views,

        # Contact statistics
        'total_searches': charge_stats['total_searches'] or 0,
        'total_card_views': charge_stats['total_card_views'] or 0,
        'total_phone_views': charge_stats['total_phone_views'] or 0,

        # Consultation statistics
        'total_consultations': doctor.total_consultations,
        'successful_consultations': doctor.successful_consultations,
        'success_rate': success_rate,

        # Rating statistics
        'rating': doctor.rating,
        'total_reviews': doctor.total_reviews,

        # Financial statistics
        'total_charges': charge_stats['total_charges'] or 0,
        'total_charge_amount': charge_stats['total_charge_amount'] or 0,

        # Wallet information
        'wallet_balance': wallet_balance,
        'is_blocked': doctor.is_blocked,

        # Status
        'is_available': doctor.is_available,
        'verification_status': doctor.verification_status,

        # Timestamps
        'created_at': doctor.created_at,
        'last_activity': doctor.last_activity
    }

    serializer = DoctorStatisticsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def doctors_statistics_list(request):
    """
    Get statistics for all doctors with filtering and sorting
    """
    from django.db.models import Count, Sum

    # Base queryset
    doctors = Doctor.objects.select_related('user', 'hospital').all()

    # Apply filters
    specialty = request.GET.get('specialty', None)
    if specialty:
        doctors = doctors.filter(specialty=specialty)

    hospital_id = request.GET.get('hospital_id', None)
    if hospital_id:
        doctors = doctors.filter(hospital_id=hospital_id)

    verification_status = request.GET.get('verification_status', None)
    if verification_status:
        doctors = doctors.filter(verification_status=verification_status)

    is_available = request.GET.get('is_available', None)
    if is_available is not None:
        doctors = doctors.filter(is_available=is_available.lower() == 'true')

    is_blocked = request.GET.get('is_blocked', None)
    if is_blocked is not None:
        doctors = doctors.filter(is_blocked=is_blocked.lower() == 'true')

    # Search
    search = request.GET.get('search', '')
    if search:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__phone__icontains=search)
        )

    # Sorting
    sort_by = request.GET.get('sort_by', '-profile_views')
    valid_sorts = [
        'profile_views', '-profile_views',
        'total_consultations', '-total_consultations',
        'rating', '-rating',
        'created_at', '-created_at'
    ]
    if sort_by in valid_sorts:
        doctors = doctors.order_by(sort_by)

    # Prepare statistics for each doctor
    doctors_stats = []
    for doctor in doctors:
        # Get charge statistics for this doctor
        charge_stats = ChargeLog.objects.filter(doctor=doctor).aggregate(
            total_searches=Count('id', filter=Q(charge_type='search')),
            total_card_views=Count('id', filter=Q(charge_type='view_card')),
            total_phone_views=Count('id', filter=Q(charge_type='view_phone')),
            total_charges=Count('id'),
            total_charge_amount=Sum('amount')
        )

        # Calculate success rate
        success_rate = 0
        if doctor.total_consultations > 0:
            success_rate = round((doctor.successful_consultations / doctor.total_consultations) * 100, 2)

        # Get wallet info
        wallet_balance = None
        if hasattr(doctor.user, 'wallet'):
            wallet_balance = float(doctor.user.wallet.balance)

        doctors_stats.append({
            'doctor_id': doctor.id,
            'doctor_name': doctor.user.get_full_name(),
            'doctor_phone': doctor.user.phone,
            'doctor_specialty': doctor.specialty,
            'doctor_specialty_display': doctor.get_specialty_display(),
            'hospital_name': doctor.hospital.name if doctor.hospital else None,

            'total_profile_views': doctor.profile_views,
            'weekly_views': doctor.weekly_views,
            'monthly_views': doctor.monthly_views,

            'total_searches': charge_stats['total_searches'] or 0,
            'total_card_views': charge_stats['total_card_views'] or 0,
            'total_phone_views': charge_stats['total_phone_views'] or 0,

            'total_consultations': doctor.total_consultations,
            'successful_consultations': doctor.successful_consultations,
            'success_rate': success_rate,

            'rating': doctor.rating,
            'total_reviews': doctor.total_reviews,

            'total_charges': charge_stats['total_charges'] or 0,
            'total_charge_amount': charge_stats['total_charge_amount'] or 0,

            'wallet_balance': wallet_balance,
            'is_blocked': doctor.is_blocked,

            'is_available': doctor.is_available,
            'verification_status': doctor.verification_status,

            'created_at': doctor.created_at,
            'last_activity': doctor.last_activity
        })

    # Pagination
    paginator = Paginator(doctors_stats, int(request.GET.get('page_size', 20)))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Serialize
    serializer = DoctorStatisticsSerializer(page_obj, many=True)

    return Response({
        'doctors': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': int(request.GET.get('page_size', 20))
        },
        'filters': {
            'specialties': dict(Doctor.SPECIALTIES),
            'verification_statuses': dict(Doctor.VERIFICATION_STATUS),
            'current_filters': {
                'specialty': specialty,
                'hospital_id': hospital_id,
                'verification_status': verification_status,
                'is_available': is_available,
                'is_blocked': is_blocked,
                'search': search,
                'sort_by': sort_by
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def doctors_statistics_summary(request):
    """
    Get summary statistics for all doctors
    """
    from django.db.models import Avg, Count, Sum

    # Overall doctor statistics
    doctor_stats = Doctor.objects.aggregate(
        total_doctors=Count('id'),
        active_doctors=Count('id', filter=Q(is_available=True)),
        verified_doctors=Count('id', filter=Q(verification_status='approved')),
        blocked_doctors=Count('id', filter=Q(is_blocked=True)),
        total_profile_views=Sum('profile_views'),
        total_consultations=Sum('total_consultations'),
        average_rating=Avg('rating'),
        total_reviews=Sum('total_reviews')
    )

    # Charge statistics
    charge_stats = ChargeLog.objects.aggregate(
        total_searches=Count('id', filter=Q(charge_type='search')),
        total_card_views=Count('id', filter=Q(charge_type='view_card')),
        total_phone_views=Count('id', filter=Q(charge_type='view_phone')),
        total_charges=Count('id'),
        total_charge_amount=Sum('amount')
    )

    # Combine statistics
    summary = {
        'total_doctors': doctor_stats['total_doctors'] or 0,
        'active_doctors': doctor_stats['active_doctors'] or 0,
        'verified_doctors': doctor_stats['verified_doctors'] or 0,
        'blocked_doctors': doctor_stats['blocked_doctors'] or 0,

        'total_profile_views': doctor_stats['total_profile_views'] or 0,
        'total_searches': charge_stats['total_searches'] or 0,
        'total_card_views': charge_stats['total_card_views'] or 0,
        'total_phone_views': charge_stats['total_phone_views'] or 0,

        'total_consultations': doctor_stats['total_consultations'] or 0,
        'average_rating': round(doctor_stats['average_rating'], 2) if doctor_stats['average_rating'] else 0,
        'total_reviews': doctor_stats['total_reviews'] or 0,

        'total_charges': charge_stats['total_charges'] or 0,
        'total_charge_amount': charge_stats['total_charge_amount'] or 0
    }

    serializer = DoctorStatisticsSummarySerializer(summary)
    return Response(serializer.data)


# ==================== Doctor Service Name Management APIs ====================

@api_view(['POST'])
@permission_classes([IsAdminPermission])
def create_doctor_service_name(request):
    """
    Create a new DoctorServiceName with automatic translation

    Request body:
    {
        "name": "Yurak tekshiruvi",
        "description": "To'liq yurak tekshiruvi va diagnostika"
    }

    Response:
    {
        "success": true,
        "message": "Xizmat nomi muvaffaqiyatli yaratildi",
        "service_name": {
            "id": 1,
            "name": "Yurak tekshiruvi",
            "name_en": "Heart examination",
            "name_ru": "Обследование сердца",
            "name_kr": "Юрак текшируви",
            "description": "To'liq yurak tekshiruvi va diagnostika",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    }
    """
    from .serializers import (
        DoctorServiceNameCreateSerializer,
        DoctorServiceNameSerializer,
    )

    # Validate and create
    serializer = DoctorServiceNameCreateSerializer(data=request.data)

    if serializer.is_valid():
        service_name = serializer.save()

        # Return created service name with translations
        response_serializer = DoctorServiceNameSerializer(service_name)

        return Response({
            'success': True,
            'message': 'Xizmat nomi muvaffaqiyatli yaratildi va tarjima qilindi',
            'service_name': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def list_doctor_service_names(request):
    """
    Get list of all DoctorServiceName entries

    Query parameters:
    - search: Search by name
    - page: Page number
    - page_size: Items per page (default: 20)
    """
    from apps.doctors.models import DoctorServiceName

    from .serializers import DoctorServiceNameSerializer

    # Base queryset
    queryset = DoctorServiceName.objects.all()

    # Search functionality
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(name_en__icontains=search) |
            Q(name_ru__icontains=search) |
            Q(name_kr__icontains=search) |
            Q(description__icontains=search)
        )

    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')

    # Pagination
    page_size = int(request.GET.get('page_size', 20))
    page_number = request.GET.get('page', 1)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    # Serialize data
    serializer = DoctorServiceNameSerializer(page_obj, many=True)

    return Response({
        'service_names': serializer.data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_size': page_size
        },
        'filters': {
            'search': search
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def get_doctor_service_name_detail(request, service_id):
    """Get detailed information about a specific DoctorServiceName"""
    from apps.doctors.models import DoctorServiceName

    from .serializers import DoctorServiceNameSerializer

    try:
        service_name = DoctorServiceName.objects.get(id=service_id)
    except DoctorServiceName.DoesNotExist:
        return Response({
            'error': 'Xizmat nomi topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = DoctorServiceNameSerializer(service_name)

    # Get usage statistics
    usage_count = service_name.doctor_services.count()

    return Response({
        'service_name': serializer.data,
        'usage_statistics': {
            'total_doctors_using': usage_count
        }
    })


@api_view(['DELETE'])
@permission_classes([IsAdminPermission])
def delete_doctor_service_name(request, service_id):
    """Delete a DoctorServiceName (only if not in use)"""
    from apps.doctors.models import DoctorServiceName

    try:
        service_name = DoctorServiceName.objects.get(id=service_id)
    except DoctorServiceName.DoesNotExist:
        return Response({
            'error': 'Xizmat nomi topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    # Check if service is in use
    usage_count = service_name.doctor_services.count()
    if usage_count > 0:
        return Response({
            'error': f'Bu xizmat nomi {usage_count} ta shifokor tomonidan ishlatilmoqda. Avval ularni boshqa xizmatga o\'tkazing.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Delete the service name
    service_name_text = service_name.name
    service_name.delete()

    return Response({
        'success': True,
        'message': f'"{service_name_text}" xizmat nomi muvaffaqiyatli o\'chirildi'
    }, status=status.HTTP_200_OK)


# ==================== User Complaint Management APIs ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user_complaint(request):
    """
    Create a new user complaint about a doctor (authenticated users only)

    Request body:
    {
        "doctor_id": 1,
        "subject": "Muammo mavzusi",
        "description": "Muammo tavsifi",
        "complaint_type": "wrong_information"  // optional: wrong_information, fake_credentials, unprofessional_behavior, pricing_issue, other
    }

    Response:
    {
        "success": true,
        "message": "Shikoyat muvaffaqiyatli yaratildi",
        "complaint": {...}
    }
    """
    from .serializers import UserComplaintCreateSerializer, UserComplaintSerializer

    # Create complaint
    serializer = UserComplaintCreateSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        complaint = serializer.save()

        # Return created complaint
        response_serializer = UserComplaintSerializer(complaint)

        return Response({
            'success': True,
            'message': 'Shikoyat muvaffaqiyatli yaratildi',
            'complaint': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_complaint_list(request):
    """
    Get list of authenticated user's own complaints

    Query parameters:
    - status: Filter by status (pending, in_progress, resolved, closed)
    - complaint_type: Filter by type (wrong_information, fake_credentials, unprofessional_behavior, pricing_issue, other)
    - doctor_id: Filter by doctor
    - search: Search by subject or description
    - page: Page number
    - page_size: Items per page (default: 10)
    """
    from .models import UserComplaint
    from .serializers import UserComplaintSerializer

    # Base queryset - only user's own complaints
    queryset = UserComplaint.objects.filter(
        user=request.user
    ).select_related('user', 'doctor', 'doctor__user', 'resolved_by').prefetch_related('files')

    # Apply filters
    status_filter = request.GET.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    complaint_type = request.GET.get('complaint_type', None)
    if complaint_type:
        queryset = queryset.filter(complaint_type=complaint_type)

    doctor_id = request.GET.get('doctor_id', None)
    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

    # Search functionality
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search) |
            Q(description__icontains=search) |
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search)
        )

    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')

    # Pagination
    page_size = int(request.GET.get('page_size', 10))
    page_number = request.GET.get('page', 1)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    # Serialize data
    serializer = UserComplaintSerializer(page_obj, many=True)

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
            'current_filters': {
                'status': status_filter,
                'complaint_type': complaint_type,
                'doctor_id': doctor_id,
                'search': search
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_complaint_detail(request, complaint_id):
    """Get specific complaint details (user's own complaint only)"""
    from .models import UserComplaint
    from .serializers import UserComplaintSerializer

    try:
        complaint = UserComplaint.objects.select_related(
            'user', 'resolved_by'
        ).prefetch_related('files').get(
            id=complaint_id,
            user=request.user
        )
    except UserComplaint.DoesNotExist:
        return Response({
            'error': 'Shikoyat topilmadi yoki sizga tegishli emas'
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = UserComplaintSerializer(complaint)

    return Response({
        'complaint': serializer.data
    })


# Admin-only views for managing all user complaints

@api_view(['GET'])
@permission_classes([IsAdminPermission])
def admin_user_complaint_list(request):
    """
    Get list of all user complaints (admin only)

    Query parameters:
    - status: Filter by status
    - complaint_type: Filter by type
    - priority: Filter by priority
    - user_id: Filter by user
    - search: Search by subject, description, or user name
    - page: Page number
    - page_size: Items per page (default: 20)
    """
    from .models import UserComplaint
    from .serializers import UserComplaintSerializer

    # Base queryset - all complaints
    queryset = UserComplaint.objects.select_related(
        'user', 'resolved_by'
    ).prefetch_related('files').all()

    # Apply filters
    status_filter = request.GET.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    complaint_type = request.GET.get('complaint_type', None)
    if complaint_type:
        queryset = queryset.filter(complaint_type=complaint_type)

    doctor_id = request.GET.get('doctor_id', None)
    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

    priority = request.GET.get('priority', None)
    if priority:
        queryset = queryset.filter(priority=priority)

    user_id = request.GET.get('user_id', None)
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    doctor_id = request.GET.get('doctor_id', None)
    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

    # Search functionality
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search) |
            Q(description__icontains=search) |
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search)
        )

    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')

    # Pagination
    page_size = int(request.GET.get('page_size', 20))
    page_number = request.GET.get('page', 1)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    # Serialize data
    serializer = UserComplaintSerializer(page_obj, many=True)

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
            'current_filters': {
                'status': status_filter,
                'complaint_type': complaint_type,
                'priority': priority,
                'user_id': user_id,
                'doctor_id': doctor_id,
                'search': search
            }
        }
    })


@api_view(['PATCH'])
@permission_classes([IsAdminPermission])
def admin_update_user_complaint(request, complaint_id):
    """
    Update user complaint status (admin only)

    Request body:
    {
        "status": "resolved",
        "resolution_notes": "Muammo hal qilindi..."
    }
    """
    from .models import UserComplaint
    from .serializers import UserComplaintSerializer, UserComplaintUpdateSerializer

    try:
        complaint = UserComplaint.objects.get(id=complaint_id)
    except UserComplaint.DoesNotExist:
        return Response({
            'error': 'Shikoyat topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)

    # Validate and update
    serializer = UserComplaintUpdateSerializer(data=request.data)

    if serializer.is_valid():
        # Update complaint
        complaint.status = serializer.validated_data['status']

        if 'resolution_notes' in serializer.validated_data:
            complaint.resolution_notes = serializer.validated_data['resolution_notes']

        # Set resolved_by if status is resolved or closed
        if complaint.status in ['resolved', 'closed']:
            complaint.resolved_by = request.user

        complaint.save()

        # Return updated complaint
        response_serializer = UserComplaintSerializer(complaint)

        return Response({
            'success': True,
            'message': 'Shikoyat holati yangilandi',
            'complaint': response_serializer.data
        })

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def admin_user_complaint_statistics(request):
    """
    Get statistics for all user complaints (admin only)
    """
    from datetime import timedelta

    from django.db.models import Count

    from .models import UserComplaint
    from .serializers import UserComplaintStatisticsSerializer

    # Basic counts by status
    status_counts = UserComplaint.objects.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}

    # Counts by type
    type_counts = UserComplaint.objects.values('complaint_type').annotate(count=Count('id'))
    type_dict = {item['complaint_type']: item['count'] for item in type_counts}

    # Counts by priority
    priority_counts = UserComplaint.objects.values('priority').annotate(count=Count('id'))
    priority_dict = {item['priority']: item['count'] for item in priority_counts}

    # Time-based statistics
    now = timezone.now()
    today = now.date()
    this_week = now - timedelta(weeks=1)
    this_month = now - timedelta(days=30)

    complaints_today = UserComplaint.objects.filter(created_at__date=today).count()
    complaints_this_week = UserComplaint.objects.filter(created_at__gte=this_week).count()
    complaints_this_month = UserComplaint.objects.filter(created_at__gte=this_month).count()

    # Average resolution time
    resolved_complaints = UserComplaint.objects.filter(status='resolved', resolved_at__isnull=False)
    avg_resolution_days = 0
    if resolved_complaints.exists():
        total_days = sum(
            (complaint.resolved_at - complaint.created_at).days
            for complaint in resolved_complaints
        )
        avg_resolution_days = total_days / resolved_complaints.count()

    # Prepare statistics
    stats = {
        'total_complaints': UserComplaint.objects.count(),
        'pending_complaints': status_dict.get('pending', 0),
        'in_progress_complaints': status_dict.get('in_progress', 0),
        'resolved_complaints': status_dict.get('resolved', 0),
        'closed_complaints': status_dict.get('closed', 0),

        'wrong_information_complaints': type_dict.get('wrong_information', 0),
        'fake_credentials_complaints': type_dict.get('fake_credentials', 0),
        'unprofessional_behavior_complaints': type_dict.get('unprofessional_behavior', 0),
        'pricing_issue_complaints': type_dict.get('pricing_issue', 0),
        'other_complaints': type_dict.get('other', 0),

        'urgent_complaints': priority_dict.get('urgent', 0),
        'high_complaints': priority_dict.get('high', 0),
        'medium_complaints': priority_dict.get('medium', 0),
        'low_complaints': priority_dict.get('low', 0),

        'complaints_today': complaints_today,
        'complaints_this_week': complaints_this_week,
        'complaints_this_month': complaints_this_month,
        'average_resolution_days': round(avg_resolution_days, 2)
    }

    serializer = UserComplaintStatisticsSerializer(stats)
    return Response(serializer.data)
