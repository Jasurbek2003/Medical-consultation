from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView

from .models import Doctor, DoctorFiles, DoctorSchedule, DoctorSpecialization, DoctorService, DoctorServiceName, DoctorCharge, ChargeLog
from .serializers import (
    DoctorSerializer, DoctorRegistrationSerializer, DoctorUpdateSerializer,
    DoctorProfileSerializer, DoctorFilesSerializer, DoctorFileUploadSerializer,
    DoctorLocationUpdateSerializer, RegionSerializer, DistrictSerializer,
    DoctorScheduleSerializer, DoctorSpecializationSerializer, DoctorServiceSerializer,
    DoctorChargeSerializer, DoctorChargeUpdateSerializer, ChargeLogSerializer
)
from .filters import DoctorFilter
from apps.core.utils import get_client_ip, is_valid_ip, is_private_ip
from apps.core.throttling import FileUploadThrottle
from .services.translation_service import DoctorTranslationService
from ..admin_panel.models import DoctorComplaint, DoctorComplaintFile
from ..admin_panel.serializers import DoctorComplaintFileSerializer
from ..hospitals.models import Districts, Regions


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
            # Public access - only show approved and non-blocked doctors
            return queryset.filter(verification_status='approved', is_blocked=False)

        if user.is_admin():
            # Admin can see all doctors
            return queryset
        elif user.is_hospital_admin():
            print(queryset.filter(hospital=user.managed_hospital))
            # Hospital admin can see their hospital's doctors
            return queryset.filter(hospital=user.managed_hospital)
        elif user.is_doctor():
            # Doctors can see their own profile and approved non-blocked doctors
            return queryset.filter(
                Q(user=user) | Q(verification_status='approved', is_blocked=False)
            )
        else:
            # Patients can only see approved and non-blocked doctors
            return queryset.filter(verification_status='approved', is_blocked=False)

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

    queryset = Doctor.objects.filter(
        verification_status='approved',
        is_blocked=False
    ).select_related(
        'user', 'hospital', 'charges'
    ).prefetch_related('files')

    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DoctorFilter
    search_fields = [
        'user__first_name', 'user__last_name', 'specialty',
        'workplace', 'bio', 'region__name', 'district__name'
    ]
    ordering_fields = ['rating', 'total_reviews', 'consultation_price', 'experience', 'charges__search_charge']
    ordering = ['-charges__search_charge', '-rating']


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
        serializer = DoctorUpdateSerializer(doctor, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data)

class DoctorProfileTranslationAPIView(APIView):
    """Translate doctor details (NEW in v3)"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """Translate doctor details to specified language"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        service = DoctorTranslationService()
        translations = service.translate_doctor_profile(doctor)
        service.save_doctor_translations(doctor, translations)
        return Response({
            'success': True,
            'message': 'Doctor profile translated successfully',
            'translations': translations
        })


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


class DoctorServiceCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create a service for a doctor"""
        doctor_id = request.user.doctor_profile.id if request.user.is_doctor() else None
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

        service_name_id = request.data.get('service_name')
        description = request.data.get('description', '')
        price = request.data.get('price', 0)
        duration = request.data.get('duration', 0)

        if not service_name_id:
            return Response(
                {'error': 'Service name ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            service_name = DoctorServiceName.objects.get(id=service_name_id)
        except DoctorServiceName.DoesNotExist:
            return Response(
                {'error': 'Service name not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        service = DoctorService.objects.create(
            doctor=doctor,
            name=service_name,
            description=description,
            price=price,
            duration=duration
        )
        return Response(
            DoctorServiceSerializer(service).data,
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        """Get all services for the authenticated doctor"""
        doctor_id = request.user.doctor_profile.id if request.user.is_doctor() else None
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

        services = DoctorService.objects.filter(doctor=doctor)
        serializer = DoctorServiceSerializer(services, many=True)
        return Response(serializer.data)

    def delete(self, request):
        """Delete a service for a doctor"""
        doctor_id = request.user.doctor_profile.id if request.user.is_doctor() else None
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

        service_id = request.data.get('service_id')
        if not service_id:
            return Response(
                {'error': 'Service ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            service = DoctorService.objects.get(id=service_id, doctor=doctor)
        except DoctorService.DoesNotExist:
            return Response(
                {'error': 'Service not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DoctorServiceNameAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        service_names = DoctorServiceName.objects.all()
        return JsonResponse(
            {'services': [{'id': service.id, 'name': service.name} for service in service_names]},
            safe=False
        )



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
    ordering_fields = ['rating', 'total_reviews', 'consultation_price', 'experience', 'charges__search_charge']

    def get_queryset(self):
        """Custom queryset with location filtering"""
        queryset = Doctor.objects.filter(
            verification_status='approved',
            is_blocked=False
        ).select_related(
            'user', 'hospital', 'region', 'district', 'charges'
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

        # Default ordering by search charge (higher charge = higher ranking)
        return queryset.order_by('-charges__search_charge', '-rating', '-total_reviews')


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


class DoctorSpecialtiesView(APIView):
    """Get all available specialties"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get(request):
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


class DoctorComplaintFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing complaint files
    Provides CRUD operations for DoctorComplaintFile model
    """
    queryset = DoctorComplaintFile.objects.select_related('complaint').all()
    serializer_class = DoctorComplaintFileSerializer
    permission_classes = [permissions.IsAuthenticated]

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


class DoctorPhoneNumberView(APIView):
    """View doctor phone number with charge"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get_client_ip(request):
        """
        Get client IP address from request with enhanced security
        Handles multiple proxy scenarios and validates IP addresses
        """
        # List of headers to check in order of preference
        ip_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_FORWARDED',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
            'REMOTE_ADDR'
        ]
        for header in ip_headers:
            ip_list = request.META.get(header)
            if ip_list:
                # Handle comma-separated IPs (first one is usually the original client)
                ip = ip_list.split(',')[0].strip()

                # Basic IP validation and private IP filtering
                if is_valid_ip(ip) and not is_private_ip(ip):
                    return ip

        # Fallback to REMOTE_ADDR even if it might be private
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def post(self, request, pk):
        """View doctor phone number with charge deduction"""
        try:
            doctor = Doctor.objects.get(id=pk)
        except Doctor.DoesNotExist:
            return Response(
                {'error': 'Shifokor topilmadi'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if doctor is blocked
        if doctor.is_blocked:
            return Response(
                {'error': 'Shifokor bloklangan'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get or create charge settings
        charge_settings, created = DoctorCharge.objects.get_or_create(doctor=doctor)
        user = doctor.user

        # Charge the doctor
        success, message = doctor.charge_wallet(
            amount=charge_settings.view_phone_charge,
            charge_type='view_phone',
            user=user,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={
                'doctor_id': doctor.id,
                'viewer_id': request.user.id
            }
        )

        if not success:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'success': True,
            'phone': doctor.user.phone,
            'charged_amount': charge_settings.view_phone_charge,
            'remaining_balance': doctor.user.wallet.balance if hasattr(doctor.user, 'wallet') else 0
        })


class DoctorChargeSettingsView(APIView):
    """Get and update doctor charge settings"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get charge settings for authenticated doctor"""
        if request.user.user_type != 'doctor':
            return Response(
                {'error': 'Faqat shifokorlar uchun'},
                status=status.HTTP_403_FORBIDDEN
            )

        doctor = request.user.doctor_profile
        charge_settings, created = DoctorCharge.objects.get_or_create(doctor=doctor)

        serializer = DoctorChargeSerializer(charge_settings)
        return Response(serializer.data)

    def patch(self, request):
        """Update customizable charge settings"""
        if request.user.user_type != 'doctor':
            return Response(
                {'error': 'Faqat shifokorlar uchun'},
                status=status.HTTP_403_FORBIDDEN
            )

        doctor = request.user.doctor_profile
        charge_settings, created = DoctorCharge.objects.get_or_create(doctor=doctor)

        serializer = DoctorChargeUpdateSerializer(
            charge_settings,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(DoctorChargeSerializer(charge_settings).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorChargeLogsView(APIView):
    """View doctor charge logs"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get charge logs for authenticated doctor"""
        if request.user.user_type != 'doctor':
            return Response(
                {'error': 'Faqat shifokorlar uchun'},
                status=status.HTTP_403_FORBIDDEN
            )

        doctor = request.user.doctor_profile
        logs = ChargeLog.objects.filter(doctor=doctor).order_by('-created_at')

        # Filter by charge type if provided
        charge_type = request.query_params.get('charge_type')
        if charge_type:
            logs = logs.filter(charge_type=charge_type)

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        result_page = paginator.paginate_queryset(logs, request)

        serializer = ChargeLogSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class DoctorWalletView(APIView):
    """View doctor wallet balance"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get wallet balance for authenticated doctor"""
        if request.user.user_type != 'doctor':
            return Response(
                {'error': 'Faqat shifokorlar uchun'},
                status=status.HTTP_403_FORBIDDEN
            )

        doctor = request.user.doctor_profile
        wallet_balance = request.user.wallet.balance if hasattr(request.user, 'wallet') else 0

        return Response({
            'wallet_balance': wallet_balance,
            'is_blocked': doctor.is_blocked,
            'warning': 'Hamyon balansi 5000 dan kam bo\'lsa, profilingiz bloklanadi' if wallet_balance <= 10000 else None
        })
