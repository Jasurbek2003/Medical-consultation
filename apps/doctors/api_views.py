from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Doctor, DoctorSchedule
from .serializers import (
    DoctorSerializer, DoctorDetailSerializer, DoctorUpdateSerializer,
)
from .filters import DoctorFilter


class DoctorProfileUpdateView(generics.UpdateAPIView):
    """Update doctor profile"""
    serializer_class = DoctorUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

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


class DoctorAvailabilityToggleView(APIView):
    """Toggle doctor availability"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        doctor.is_available = not doctor.is_available
        doctor.save()

        return Response({
            'success': True,
            'is_available': doctor.is_available,
            'message': 'Mavjudlik holati yangilandi'
        })


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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Monthly analytics endpoint'})


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

# Add more view implementations as needed...