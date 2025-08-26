from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView

from .models import Doctor, DoctorFiles, DoctorSchedule, DoctorSpecialization, DoctorService
from .serializers import (
    DoctorSerializer, DoctorRegistrationSerializer, DoctorUpdateSerializer,
    DoctorProfileSerializer, DoctorFilesSerializer, DoctorFileUploadSerializer,
    DoctorLocationUpdateSerializer, RegionSerializer, DistrictSerializer,
    DoctorScheduleSerializer, DoctorSpecializationSerializer, DoctorServiceSerializer
)
from .filters import DoctorFilter
from ..hospitals.models import Districts, Regions
from ..users.serializers import UserUpdateSerializer, DoctorUserUpdateSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    """Complete CRUD operations for doctors"""

    queryset = Doctor.objects.select_related(
        'user', 'hospital', 'translations',
    ).prefetch_related('files', 'schedules', 'specializations')

    serializer_class = DoctorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DoctorFilter
    search_fields = [
        'user__first_name', 'user__last_name', 'specialty',
        'workplace', 'bio', 'region__name', 'district__name'
    ]
    ordering_fields = [
        'rating', 'total_reviews', 'consultation_price',
        'experience', 'created_at', 'total_consultations'
    ]
    ordering = ['-rating', '-total_reviews']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return DoctorRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return DoctorUpdateSerializer
        elif self.action == 'retrieve':
            return DoctorProfileSerializer
        elif self.action == 'upload_file':
            return DoctorFileUploadSerializer
        elif self.action == 'update_location':
            return DoctorLocationUpdateSerializer
        return DoctorSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = self.queryset
        user = self.request.user

        if not user.is_authenticated:
            # Public access - only show approved doctors
            return queryset.filter(verification_status='approved')

        if user.is_admin():
            # Admin can see all doctors
            return queryset
        elif user.is_hospital_admin():
            print(queryset.filter(hospital=user.managed_hospital))
            # Hospital admin can see their hospital's doctors
            return queryset.filter(hospital=user.managed_hospital)
        elif user.is_doctor():
            # Doctors can see their own profile and approved doctors
            return queryset.filter(
                Q(user=user) | Q(verification_status='approved')
            )
        else:
            # Patients can only see approved doctors
            return queryset.filter(verification_status='approved')

    def perform_create(self, serializer):
        """Handle doctor creation with file uploads"""
        doctor = serializer.save()

        # Track profile view for the creator
        if hasattr(doctor, 'profile_views'):
            doctor.profile_views += 1
            doctor.save(update_fields=['profile_views'])

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_file(self, request, pk=None):
        """Upload a file for a doctor"""
        doctor = self.get_object()

        # Check permissions
        if not (request.user.is_admin() or
                (request.user.is_doctor() and request.user.doctor_profile == doctor) or
                (request.user.is_hospital_admin() and doctor.hospital == request.user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            # Check if file type already exists
            file_type = serializer.validated_data['file_type']
            existing_file = DoctorFiles.objects.filter(
                doctor=doctor,
                file_type=file_type
            ).first()

            if existing_file:
                # Update existing file
                existing_file.file = serializer.validated_data['file']
                existing_file.save()
                return Response(
                    DoctorFilesSerializer(existing_file, context={'request': request}).data
                )
            else:
                # Create new file
                file_obj = serializer.save(doctor=doctor)
                return Response(
                    DoctorFilesSerializer(file_obj, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, pk=None):
        """Delete a doctor's file"""
        doctor = self.get_object()
        file_type = request.query_params.get('file_type')

        if not file_type:
            return Response(
                {'error': 'file_type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check permissions
        if not (request.user.is_admin() or
                (request.user.is_doctor() and request.user.doctor_profile == doctor)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            file_obj = DoctorFiles.objects.get(doctor=doctor, file_type=file_type)
            file_obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DoctorFiles.DoesNotExist:
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['patch'])
    def update_location(self, request, pk=None):
        """Update doctor's location (region/district)"""
        doctor = self.get_object()

        # Check permissions
        if not (request.user.is_admin() or
                (request.user.is_doctor() and request.user.doctor_profile == doctor) or
                (request.user.is_hospital_admin() and doctor.hospital == request.user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorLocationUpdateSerializer(
            doctor,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get all files for a doctor"""
        doctor = self.get_object()
        files = DoctorFiles.objects.filter(doctor=doctor)
        serializer = DoctorFilesSerializer(
            files,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_by_location(self, request):
        """Search doctors by region and district"""
        region_id = request.query_params.get('region')
        district_id = request.query_params.get('district')

        queryset = self.get_queryset()

        if region_id:
            queryset = queryset.filter(region_id=region_id)

        if district_id:
            queryset = queryset.filter(district_id=district_id)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def track_view(self, request, pk=None):
        """Track profile view"""
        doctor = self.get_object()

        # Update view counts
        doctor.profile_views += 1

        # Update weekly and monthly views (you can implement more sophisticated tracking)
        doctor.weekly_views += 1
        doctor.monthly_views += 1

        doctor.save(update_fields=['profile_views', 'weekly_views', 'monthly_views'])

        return Response({'message': 'View tracked successfully'})


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """Regions API"""

    queryset = Regions.objects.all().order_by('name')
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def districts(self, request, pk=None):
        """Get districts for a region"""
        region = self.get_object()
        districts = Districts.objects.filter(region=region).order_by('name')
        serializer = DistrictSerializer(districts, many=True)
        return Response(serializer.data)


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """Districts API"""

    queryset = Districts.objects.select_related('region').all().order_by('name')
    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['region']


class DoctorFilesViewSet(viewsets.ModelViewSet):
    """Doctor Files management"""

    serializer_class = DoctorFilesSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Filter files based on user permissions"""
        user = self.request.user

        if user.is_admin():
            return DoctorFiles.objects.all()
        elif user.is_doctor():
            return DoctorFiles.objects.filter(doctor__user=user)
        elif user.is_hospital_admin():
            return DoctorFiles.objects.filter(doctor__hospital=user.managed_hospital)
        else:
            return DoctorFiles.objects.none()

    def perform_create(self, serializer):
        """Set doctor when creating file"""
        doctor_id = self.request.data.get('doctor')
        if doctor_id:
            doctor = get_object_or_404(Doctor, id=doctor_id)

            # Check permissions
            user = self.request.user
            if not (user.is_admin() or
                    (user.is_doctor() and user.doctor_profile == doctor) or
                    (user.is_hospital_admin() and doctor.hospital == user.managed_hospital)):
                raise PermissionError("You don't have permission to upload files for this doctor")

            serializer.save(doctor=doctor)
        else:
            raise ValueError("Doctor ID is required")


class DoctorScheduleViewSet(viewsets.ModelViewSet):
    """Doctor Schedule management"""

    serializer_class = DoctorScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter schedules based on user permissions"""
        user = self.request.user

        if user.is_admin():
            return DoctorSchedule.objects.all()
        elif user.is_doctor():
            return DoctorSchedule.objects.filter(doctor__user=user)
        elif user.is_hospital_admin():
            return DoctorSchedule.objects.filter(doctor__hospital=user.managed_hospital)
        else:
            # Patients can see all approved doctor schedules
            return DoctorSchedule.objects.filter(
                doctor__verification_status='approved'
            )


class DoctorSpecializationViewSet(viewsets.ModelViewSet):
    """Doctor Specialization management"""

    serializer_class = DoctorSpecializationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter specializations based on user permissions"""
        user = self.request.user

        if user.is_admin():
            return DoctorSpecialization.objects.all()
        elif user.is_doctor():
            return DoctorSpecialization.objects.filter(doctor__user=user)
        elif user.is_hospital_admin():
            return DoctorSpecialization.objects.filter(doctor__hospital=user.managed_hospital)
        else:
            # Patients can see all verified specializations
            return DoctorSpecialization.objects.filter(is_verified=True)


# Legacy API Views for backward compatibility
class DoctorListView(generics.ListAPIView):
    """List all approved doctors"""

    queryset = Doctor.objects.filter(verification_status='approved').select_related(
        'user', 'hospital',
    ).prefetch_related('files')

    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DoctorFilter
    search_fields = [
        'user__first_name', 'user__last_name', 'specialty',
        'workplace', 'bio', 'region__name', 'district__name'
    ]
    ordering_fields = ['rating', 'total_reviews', 'consultation_price', 'experience']
    ordering = ['-rating']


class DoctorDetailView(generics.RetrieveAPIView):
    """Doctor detail view"""

    queryset = Doctor.objects.select_related(
        'user', 'hospital'
    ).prefetch_related('files', 'specializations', 'translations', 'services')

    serializer_class = DoctorProfileSerializer
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        print("retrieve called")
        """Override retrieve to track views"""
        instance = self.get_object()

        # Track profile view if user is authenticated
        if request.user.is_authenticated:
            instance.profile_views += 1
            instance.weekly_views += 1
            instance.monthly_views += 1
            instance.save(update_fields=['profile_views', 'weekly_views', 'monthly_views'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DoctorProfileView(APIView):
    """Get or update doctor profile"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get the authenticated doctor's profile"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        print("doctor profile")
        serializer = DoctorProfileSerializer(doctor)
        return Response(serializer.data)


    def put(self, request):
        """Update the authenticated doctor's profile"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorUpdateSerializer(doctor, data=request.data, partial=True)
        print(request.data)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        print(request.data.get('district'))
        user = request.user
        user.first_name = request.data.get('first_name') if request.data.get('first_name') else user.first_name
        user.last_name = request.data.get('last_name') if request.data.get('last_name') else user.last_name
        user.email = request.data.get('email') if request.data.get('email') else user.email
        user.region = Regions.objects.get(id=request.data.get('region')) if request.data.get('region') else user.region
        user.district = Districts.objects.get(id=request.data.get('district')) if request.data.get('district') else user.district
        user.phone = request.data.get('phone') if request.data.get('phone') else user.phone
        user.address = request.data.get('address') if request.data.get('address') else user.address
        user.gender = request.data.get('gender') if request.data.get('gender') else user.gender
        user.birth_date = request.data.get('birth_date') if request.data.get('birth_date') else user.birth_date
        user.save()
        return Response(serializer.data)





class DoctorRegistrationView(generics.CreateAPIView):
    """Doctor registration endpoint"""

    serializer_class = DoctorRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        print("create called")
        """Custom create with file handling"""
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            doctor = serializer.save()

            return Response({
                'message': 'Doctor registered successfully',
                'doctor_id': doctor.id,
                'verification_status': doctor.verification_status
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorLocationUpdateView(generics.UpdateAPIView):
    """Update doctor location"""

    queryset = Doctor.objects.all()
    serializer_class = DoctorLocationUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Get doctor object with permission check"""
        obj = super().get_object()
        user = self.request.user

        if not (user.is_admin() or
                (user.is_doctor() and user.doctor_profile == obj) or
                (user.is_hospital_admin() and obj.hospital == user.managed_hospital)):
            raise PermissionError("You don't have permission to update this doctor")

        return obj


class DoctorFileUploadView(generics.CreateAPIView):
    """Upload doctor files"""

    serializer_class = DoctorFileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        """Create or update doctor file"""
        doctor_id = request.data.get('doctor')

        if not doctor_id:
            return Response(
                {'error': 'Doctor ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if not (user.is_admin() or
                (user.is_doctor() and user.doctor_profile == doctor) or
                (user.is_hospital_admin() and doctor.hospital == user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():

            file_obj = serializer.save(doctor=doctor)

            return Response(
                DoctorFilesSerializer(file_obj, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorServiceCreateView(generics.CreateAPIView):
    """Create doctor service"""

    serializer_class = DoctorServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        """Create a service for a doctor"""
        doctor_id = request.data.get('doctor')
        if not doctor_id:
            return Response(
                {'error': 'Doctor ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        # Check permissions
        user = request.user
        if not (user.is_admin() or
                (user.is_doctor() and user.doctor_profile == doctor) or
                (user.is_hospital_admin() and doctor.hospital == user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            service = serializer.save(doctor=doctor)
            return Response(
                {'message': 'Service created successfully', 'service_id': service.id},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DoctorFileDeleteView(generics.DestroyAPIView):
    """Delete doctor file"""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        """Delete a doctor's file"""
        file_id = request.data.get('file')
        if not file_id:
            return Response(
                {'error': 'File ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            file_obj = DoctorFiles.objects.get(id=file_id)
        except DoctorFiles.DoesNotExist:
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        doctor = file_obj.doctor
        # Check permissions
        user = request.user
        if not (user.is_admin() or
                (user.is_doctor() and user.doctor_profile == doctor) or
                (user.is_hospital_admin() and doctor.hospital == user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class DoctorSearchView(generics.ListAPIView):
    """Advanced doctor search with location filtering"""

    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DoctorFilter
    search_fields = [
        'user__first_name', 'user__last_name', 'specialty',
        'workplace', 'bio', 'region__name', 'district__name'
    ]
    ordering_fields = ['rating', 'total_reviews', 'consultation_price', 'experience']

    def get_queryset(self):
        """Custom queryset with location filtering"""
        queryset = Doctor.objects.filter(
            verification_status='approved'
        ).select_related(
            'user', 'hospital', 'region', 'district'
        ).prefetch_related('files')

        # Location filtering
        region_id = self.request.query_params.get('region')
        district_id = self.request.query_params.get('district')

        if region_id:
            queryset = queryset.filter(region_id=region_id)

        if district_id:
            queryset = queryset.filter(district_id=district_id)

        # Specialty filtering
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty=specialty)

        # Availability filtering
        available_only = self.request.query_params.get('available_only', 'false').lower()
        if available_only == 'true':
            queryset = queryset.filter(is_available=True)

        # Online consultation filtering
        online_only = self.request.query_params.get('online_only', 'false').lower()
        if online_only == 'true':
            queryset = queryset.filter(is_online_consultation=True)

        # Price range filtering
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price:
            queryset = queryset.filter(consultation_price__gte=min_price)

        if max_price:
            queryset = queryset.filter(consultation_price__lte=max_price)

        # Experience filtering
        min_experience = self.request.query_params.get('min_experience')
        if min_experience:
            queryset = queryset.filter(experience__gte=min_experience)

        # Rating filtering
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)

        return queryset


class DoctorStatsView(generics.RetrieveAPIView):
    """Doctor statistics view"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Get doctor statistics"""
        try:
            doctor = Doctor.objects.get(id=pk)
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if not (user.is_admin() or
                (user.is_doctor() and user.doctor_profile == doctor) or
                (user.is_hospital_admin() and doctor.hospital == user.managed_hospital)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Calculate statistics
        stats = {
            'profile_views': doctor.profile_views,
            'weekly_views': doctor.weekly_views,
            'monthly_views': doctor.monthly_views,
            'total_consultations': doctor.total_consultations,
            'completed_consultations': doctor.consultations.filter(status='completed').count(),
            'pending_consultations': doctor.consultations.filter(status='pending').count(),
            'rating': doctor.rating,
            'total_reviews': doctor.total_reviews,
            'success_rate': doctor.success_rate if hasattr(doctor, 'success_rate') else 0,
            'files_count': doctor.files.count(),
            'schedules_count': doctor.schedules.count(),
            'specializations_count': doctor.specializations.count()
        }

        return Response(stats)


class LocationAPIView(generics.GenericAPIView):
    """Location management API"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Get regions and districts"""
        regions = Regions.objects.all().order_by('name')
        districts = Districts.objects.select_related('region').all().order_by('name')

        regions_data = RegionSerializer(regions, many=True).data
        districts_data = DistrictSerializer(districts, many=True).data

        return Response({
            'regions': regions_data,
            'districts': districts_data
        })


class RegionDistrictsView(generics.ListAPIView):
    """Get districts for a specific region"""

    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        region_id = self.kwargs['region_id']
        return Districts.objects.filter(region_id=region_id).order_by('name')

    def list(self, request, *args, **kwargs):
        """Custom list response"""
        try:
            region = Regions.objects.get(id=self.kwargs['region_id'])
        except Regions.DoesNotExist:
            return Response(
                {'error': 'Region not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'region': RegionSerializer(region).data,
            'districts': serializer.data
        })

class DoctorAvailabilityToggleView(APIView):
    """
    Toggle Doctor Availability

    POST /api/v1/doctors/auth/toggle-availability/
    """
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
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