from django.utils import timezone
from rest_framework import generics, status, permissions, serializers
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Doctor, DoctorSchedule
from .serializers import (
    DoctorSerializer, DoctorDetailSerializer, DoctorUpdateSerializer, DoctorRegistrationSerializer,
    DoctorLoginSerializer, DoctorProfileUpdateSerializer,
)
from .filters import DoctorFilter
from ..users.serializers import UserSerializer


class DoctorProfileUpdateView(generics.UpdateAPIView):
    """Update doctor profile"""
    serializer_class = DoctorUpdateSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_object_or_404(Doctor, user=self.request.user)


class DoctorPhotoUploadView(APIView):
    """Upload doctor photo"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)

        if 'photo' not in request.FILES:
            return Response({'error': 'Rasm fayli kerak'}, status=status.HTTP_400_BAD_REQUEST)

        doctor.photo = request.FILES['photo']
        doctor.save()

        return Response({
            'success': True,
            'photo_url': doctor.photo.url if doctor.photo else None
        })


class DoctorDocumentUploadView(APIView):
    """Upload doctor documents"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)

        if 'diploma_image' in request.FILES:
            doctor.diploma_image = request.FILES['diploma_image']

        if 'license_image' in request.FILES:
            doctor.license_image = request.FILES['license_image']

        doctor.save()

        return Response({'success': True, 'message': 'Hujjatlar yuklandi'})


class DoctorScheduleBulkUpdateView(APIView):
    """Bulk update doctor schedule"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        schedules_data = request.data.get('schedules', [])

        # Delete existing schedules
        doctor.schedules.all().delete()

        # Create new schedules
        for schedule_data in schedules_data:
            DoctorSchedule.objects.create(
                doctor=doctor,
                **schedule_data
            )

        return Response({'success': True, 'message': 'Jadval yangilandi'})


class AvailableSlotsView(APIView):
    """Get available time slots for a doctor"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        doctor_id = request.query_params.get('doctor_id')
        date = request.query_params.get('date')

        if not doctor_id or not date:
            return Response({'error': 'doctor_id va date parametrlari kerak'},
                            status=status.HTTP_400_BAD_REQUEST)

        doctor = get_object_or_404(Doctor, id=doctor_id)

        # Here you would implement the logic to get available slots
        # This is a simplified example
        available_slots = [
            {'time': '09:00', 'available': True},
            {'time': '10:00', 'available': False},
            {'time': '11:00', 'available': True},
            # Add more slots based on doctor's schedule
        ]

        return Response({
            'doctor_id': doctor_id,
            'date': date,
            'available_slots': available_slots
        })


class DoctorStatisticsOverviewView(APIView):
    """Get doctor statistics overview"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)

        # Calculate statistics
        stats = {
            'total_consultations': doctor.total_consultations,
            'completed_consultations': doctor.successful_consultations,
            'overall_rating': doctor.rating,
            'total_reviews': doctor.total_reviews,
            'profile_views': doctor.profile_views,
            'monthly_views': doctor.monthly_views,
            'success_rate': doctor.success_rate,
        }

        return Response(stats)


class DoctorDetailedStatisticsView(APIView):
    """Get detailed doctor statistics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)

        # Here you would implement detailed statistics calculation
        # This is a placeholder implementation
        detailed_stats = {
            'consultation_trends': [],
            'rating_breakdown': {},
            'monthly_earnings': 0,
            'patient_satisfaction': 0,
        }

        return Response(detailed_stats)


class DoctorPerformanceView(APIView):
    """Get doctor performance metrics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)

        performance_data = {
            'response_time': 0,  # Average response time
            'cancellation_rate': 0,  # Consultation cancellation rate
            'patient_retention': 0,  # Patient retention rate
            'revenue_growth': 0,  # Revenue growth percentage
        }

        return Response(performance_data)


class DoctorSearchView(generics.ListAPIView):
    """Search doctors"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = DoctorFilter

    def get_queryset(self):
        queryset = Doctor.objects.filter(
            verification_status='approved',
            is_available=True,
            user__is_active=True
        )

        search_query = self.request.query_params.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(specialty__icontains=search_query) |
                Q(workplace__icontains=search_query)
            )

        return queryset


class DoctorAdvancedSearchView(DoctorSearchView):
    """Advanced search with multiple filters"""

    def get_queryset(self):
        queryset = super().get_queryset()

        # Add more advanced filtering logic here
        specialty = self.request.query_params.get('specialty')
        min_rating = self.request.query_params.get('min_rating')
        max_price = self.request.query_params.get('max_price')
        region = self.request.query_params.get('region')

        if specialty:
            queryset = queryset.filter(specialty=specialty)
        if min_rating:
            queryset = queryset.filter(rating__gte=float(min_rating))
        if max_price:
            queryset = queryset.filter(consultation_price__lte=float(max_price))
        if region:
            queryset = queryset.filter(region__icontains=region)

        return queryset


class DoctorsBySpecialtyView(generics.ListAPIView):
    """Get doctors by specialty"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        specialty = self.kwargs.get('specialty') or self.request.query_params.get('specialty')
        return Doctor.objects.filter(
            specialty=specialty,
            verification_status='approved',
            is_available=True
        )


class DoctorsByLocationView(generics.ListAPIView):
    """Get doctors by location"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        region = self.request.query_params.get('region')
        district = self.request.query_params.get('district')

        queryset = Doctor.objects.filter(
            verification_status='approved',
            is_available=True
        )

        if region:
            queryset = queryset.filter(region__icontains=region)
        if district:
            queryset = queryset.filter(district__icontains=district)

        return queryset


class PublicDoctorListView(generics.ListAPIView):
    """Public doctor list (no authentication required)"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = DoctorFilter

    def get_queryset(self):
        return Doctor.objects.filter(
            verification_status='approved',
            is_available=True,
            user__is_active=True
        ).order_by('-rating', '-total_reviews')


class PublicDoctorDetailView(generics.RetrieveAPIView):
    """Public doctor detail (no authentication required)"""
    serializer_class = DoctorDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return Doctor.objects.filter(
            verification_status='approved',
            user__is_active=True
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)

        # Increment profile views
        doctor = self.get_object()
        doctor.profile_views += 1
        doctor.save(update_fields=['profile_views'])

        return response


class PublicDoctorSearchView(DoctorSearchView):
    """Public doctor search"""
    pass


class PublicSpecialtiesView(APIView):
    """Get all available specialties"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        specialties = []
        if hasattr(Doctor, 'SPECIALTIES'):
            for code, name in Doctor.SPECIALTIES:
                count = Doctor.objects.filter(
                    specialty=code,
                    verification_status='approved',
                    is_available=True
                ).count()
                specialties.append({
                    'code': code,
                    'name': name,
                    'doctor_count': count
                })

        return Response(specialties)


class FeaturedDoctorsView(generics.ListAPIView):
    """Get featured doctors"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Doctor.objects.filter(
            verification_status='approved',
            is_available=True,
            rating__gte=4.0
        ).order_by('-rating', '-total_reviews')[:10]


class TopRatedDoctorsView(generics.ListAPIView):
    """Get top rated doctors"""
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Doctor.objects.filter(
            verification_status='approved',
            is_available=True,
            total_reviews__gte=5
        ).order_by('-rating', '-total_reviews')[:20]


# Additional placeholder views for the remaining endpoints
# You can implement these based on your specific requirements

class DoctorMonthlyAnalyticsView(APIView):
    def get(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        # Implement actual analytics logic
        return Response({
            'consultations_this_month': doctor.consultations.filter(
                created_at__month=timezone.now().month
            ).count(),
            # Add more analytics
        })


class DoctorYearlyAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Yearly analytics endpoint'})


class DoctorsByRatingView(generics.ListAPIView):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        min_rating = self.request.query_params.get('min_rating', 4.0)
        return Doctor.objects.filter(
            verification_status='approved',
            rating__gte=float(min_rating)
        ).order_by('-rating')


class DoctorsByPriceView(generics.ListAPIView):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        max_price = self.request.query_params.get('max_price')
        queryset = Doctor.objects.filter(verification_status='approved')

        if max_price:
            queryset = queryset.filter(consultation_price__lte=float(max_price))

        return queryset.order_by('consultation_price')


class DoctorRegistrationView(generics.CreateAPIView):
    """
    Doctor Registration API

    POST /api/v1/doctors/auth/register/
    """
    serializer_class = DoctorRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user and doctor profile
        user = serializer.save()

        # Note: Doctor needs admin approval before they can login
        # So we don't create a token immediately

        return Response({
            'success': True,
            'message': 'Doctor registration successful. Please wait for admin approval.',
            'user': UserSerializer(user).data,
            'doctor_id': user.doctor_profile.id,
            'verification_status': user.doctor_profile.verification_status,
            'approval_required': True
        }, status=status.HTTP_201_CREATED)


class DoctorLoginView(APIView):
    """
    Doctor Login API

    POST /api/v1/doctors/auth/login/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = DoctorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        doctor = user.doctor_profile

        # Check if doctor is approved
        if doctor.verification_status != 'approved':
            return Response({
                'success': False,
                'error': 'Your account is pending approval. Please wait for admin verification.',
                'verification_status': doctor.verification_status
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if user is approved by admin
        print(user.is_approved_by_admin, "User approval status")
        if not user.is_approved_by_admin:
            return Response({
                'success': False,
                'error': 'Your account needs admin approval before you can login.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])

        # Create or get token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': 'Login successful',
            'token': token.key,
            'user': UserSerializer(user).data,
            'doctor': {
                'id': doctor.id,
                'specialty': doctor.get_specialty_display(),
                'rating': doctor.rating,
                'total_consultations': doctor.total_consultations,
                'is_available': doctor.is_available,
                'hospital': doctor.hospital.name if doctor.hospital else None
            }
        })


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and Update Doctor Profile

    GET /api/v1/doctors/auth/profile/
    PUT/PATCH /api/v1/doctors/auth/profile/
    """
    serializer_class = DoctorProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        """Get the doctor profile of the authenticated user"""
        print("Fetching doctor profile for user:", self.request.user)
        user = self.request.user

        if user.user_type != 'doctor':
            raise serializers.ValidationError('User is not a doctor')

        return user.doctor_profile

    def retrieve(self, request, *args, **kwargs):
        """Get doctor profile with additional info"""
        doctor = self.get_object()

        # Prepare detailed response
        data = {
            'success': True,
            'user': UserSerializer(doctor.user).data,
            'doctor': {
                'id': doctor.id,
                'specialty': doctor.specialty,
                'specialty_display': doctor.get_specialty_display(),
                'degree': doctor.degree,
                'degree_display': doctor.get_degree_display(),
                'license_number': doctor.license_number,
                'experience': doctor.experience,
                'education': doctor.education,
                'workplace': doctor.workplace,
                'workplace_address': doctor.workplace_address,
                'consultation_price': str(doctor.consultation_price),
                'bio': doctor.bio,
                'achievements': doctor.achievements,
                'rating': doctor.rating,
                'total_reviews': doctor.total_reviews,
                'total_consultations': doctor.total_consultations,
                'is_available': doctor.is_available,
                'is_online_consultation': doctor.is_online_consultation,
                'work_start_time': doctor.work_start_time,
                'work_end_time': doctor.work_end_time,
                'work_days': doctor.work_days,
                'verification_status': doctor.verification_status,
                'hospital': {
                    'id': doctor.hospital.id,
                    'name': doctor.hospital.name,
                    'address': doctor.hospital.address
                } if doctor.hospital else None,
                'diploma_image': doctor.diploma_image.url if doctor.diploma_image else None,
                'license_image': doctor.license_image.url if doctor.license_image else None,
            }
        }

        return Response(data)


class DoctorChangePasswordView(APIView):
    """
    Change Doctor Password

    POST /api/v1/doctors/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'doctor':
            return Response({
                'success': False,
                'error': 'User is not a doctor'
            }, status=status.HTTP_403_FORBIDDEN)

        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        if not all([old_password, new_password, new_password_confirm]):
            return Response({
                'success': False,
                'error': 'All password fields are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password_confirm:
            return Response({
                'success': False,
                'error': 'New passwords do not match'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.check_password(old_password):
            return Response({
                'success': False,
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        request.user.set_password(new_password)
        request.user.save()

        # Create new token
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)

        return Response({
            'success': True,
            'message': 'Password changed successfully',
            'token': token.key
        })


class DoctorAvailabilityToggleView(APIView):
    """
    Toggle Doctor Availability

    POST /api/v1/doctors/auth/toggle-availability/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'doctor':
            return Response({
                'success': False,
                'error': 'User is not a doctor'
            }, status=status.HTTP_403_FORBIDDEN)

        doctor = request.user.doctor_profile
        doctor.is_available = not doctor.is_available
        doctor.save()

        return Response({
            'success': True,
            'message': f'Availability {"enabled" if doctor.is_available else "disabled"}',
            'is_available': doctor.is_available
        })


# Quick endpoints for easy integration
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@parser_classes([MultiPartParser, FormParser])
def quick_doctor_register(request):
    """
    Quick doctor registration endpoint with file upload
    """
    serializer = DoctorRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        return Response({
            'success': True,
            'message': 'Registration successful. Waiting for approval.',
            'doctor_id': user.doctor_profile.id,
            'user_id': user.id,
            'phone': user.phone,
            'verification_status': 'pending'
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_doctor_login(request):
    """
    Quick doctor login endpoint
    """
    serializer = DoctorLoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        doctor = user.doctor_profile

        # Check approval status
        if doctor.verification_status != 'approved' or not user.is_approved_by_admin:
            return Response({
                'success': False,
                'error': 'Account pending approval',
                'verification_status': doctor.verification_status
            }, status=status.HTTP_403_FORBIDDEN)

        # Create token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'token': token.key,
            'doctor_id': doctor.id,
            'user_id': user.id,
            'specialty': doctor.get_specialty_display(),
            'full_name': user.get_full_name()
        })

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip