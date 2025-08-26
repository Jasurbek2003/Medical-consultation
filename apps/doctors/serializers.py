from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model

from .models import (
    Doctor, DoctorFiles, DoctorSchedule, DoctorSpecialization, DoctorService,
)
from ..hospitals.models import Regions, Districts

User = get_user_model()


class DoctorFilesSerializer(serializers.ModelSerializer):
    """Shifokor hujjatlari serializer"""

    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DoctorFiles
        fields = [
            'id', 'file_type', 'file_type_display', 'file', 'file_url',
            'uploaded_at'
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class RegionSerializer(serializers.ModelSerializer):
    """Viloyat serializer"""

    class Meta:
        model = Regions
        fields = ['id', 'name']


class DistrictSerializer(serializers.ModelSerializer):
    """Tuman serializer"""

    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = Districts
        fields = ['id', 'name', 'region', 'region_name']


class DoctorServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorService
        fields = ['id', 'description', 'price']


class DoctorSerializer(serializers.ModelSerializer):
    """Basic doctor serializer"""

    # User information
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )

    # Location information with nested objects
    region_name = serializers.CharField(source='user.region', read_only=True)
    region_id = serializers.IntegerField(source='user.region_id', read_only=True)
    district_name = serializers.CharField(source='user.district', read_only=True)
    district_id = serializers.IntegerField(source='user.district_id', read_only=True)

    # Hospital information
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, allow_null=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    files = DoctorFilesSerializer(many=True, read_only=True)
    services = DoctorServiceSerializer(many=True, read_only=True)



    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialty', 'specialty_display',
            'experience', 'degree', 'rating', 'total_reviews',
            'consultation_price', 'is_available', 'is_online_consultation',
            'hospital_name', 'workplace', 'verification_status',
            'verification_status_display', 'total_consultations',
            'success_rate', 'avatar', 'region_name',
             'district_name', 'region_id', 'district_id', 'files', 'services'
        ]



class DoctorScheduleSerializer(serializers.ModelSerializer):
    """Shifokor ish jadvali serializer"""

    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = ['id', 'weekday', 'weekday_display', 'start_time', 'end_time', 'is_available']


class DoctorSpecializationSerializer(serializers.ModelSerializer):
    """Qo'shimcha mutaxassisliklar serializer"""

    class Meta:
        model = DoctorSpecialization
        fields = ['id', 'specialty_name', 'description', 'certificate_image']


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    """Complete doctor registration serializer"""

    # User fields
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    phone = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+998\d{9}$',
                message='Phone number must be in format: +998901234567'
            )
        ]
    )
    username = serializers.CharField(
        required=True,
        max_length=150,
        help_text='Username must be unique and can only contain letters, numbers, and underscores.'
    )
    first_name = serializers.CharField(required=True, max_length=30)
    last_name = serializers.CharField(required=True, max_length=150)
    birth_date = serializers.DateField(required=True)
    gender = serializers.ChoiceField(
        choices=["M", "F"], required=True
    )

    # Region and District
    region_id = serializers.IntegerField(required=True)
    district_id = serializers.IntegerField(required=True)

    class Meta:
        model = Doctor
        fields = [
            # User fields
            'username', 'password', 'password_confirm', 'phone',
            'first_name', 'last_name', 'birth_date', 'gender',

            # Doctor fields
            'specialty', 'experience', 'degree', 'license_number',
            'education', 'bio', 'consultation_price',
            'workplace', 'workplace_address',
            'region_id', 'district_id',
        ]

    def validate(self, attrs):
        """Custom validation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")

        # Validate region and district relationship
        region = attrs.get('region_id')
        district = attrs.get('district_id')
        print(Districts.objects.get(id=district).region.id==region)
        print(type(Districts.objects.get(id=district).region.id), type(region))
        if Districts.objects.get(id=district).region.id != region:
            raise serializers.ValidationError(
                "Selected district does not belong to the selected region"
            )
        return attrs

    def create(self, validated_data):
        """Create doctor with user and files"""
        from django.db import transaction
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        phone = validated_data.pop('phone')
        username = validated_data.pop('username')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        birth_date = validated_data.pop('birth_date')
        gender = validated_data.pop('gender')

        with transaction.atomic():
            # Create user
            user = User.objects.create(
                username=username,
                phone=phone,
                password=password,
                user_type='doctor',
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender,
            )
            region = Regions.objects.get(id=validated_data.pop('region_id'))
            district = Districts.objects.get(id=validated_data.pop('district_id'))
            user.region = region
            user.district = district
            user.set_password(password)
            user.save()

            # Create doctor
            doctor = Doctor.objects.create(user=user, **validated_data)

        return doctor


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """Serializer for doctor management in admin panel"""

    # User information
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    user_is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    user_is_verified = serializers.BooleanField(source='user.is_verified', read_only=True)
    user_created_at = serializers.DateTimeField(source='user.created_at', read_only=True)


    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True, allow_null=True)


    class Meta:
        model = Doctor
        fields = [
            'user_id', 'first_name', 'last_name', 'full_name',
            'phone', 'email', 'avatar', 'user_is_active', 'user_is_verified',
            'user_created_at',

            # Doctor specific
            'specialty', 'experience', 'degree',
            'license_number', 'education', 'bio', 'achievements',
            'consultation_price', 'is_available', 'is_online_consultation',
            'workplace', 'workplace_address', 'verification_status',


            # Hospital
            'hospital_id',

            # Statistics
            'rating', 'total_reviews', 'total_consultations',
            'success_rate', 'profile_views',
            'weekly_views', 'monthly_views',
        ]

    def get_consultation_count(self, obj):
        """Get consultation count from related consultations"""
        return obj.consultations.count()

    def get_success_rate(self, obj):
        """Calculate success rate based on completed consultations"""
        total = obj.consultations.count()
        if total == 0:
            return 0
        completed = obj.consultations.filter(status='completed').count()
        return round((completed / total) * 100, 1)



class DoctorProfileSerializer(serializers.ModelSerializer):
    """Detailed doctor profile serializer for public view"""

    # User information
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    # Display fields
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    degree_display = serializers.CharField(source='get_degree_display', read_only=True)
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )

    region_name = serializers.CharField(source='user.region', read_only=True)
    region_id = serializers.IntegerField(source='user.region_id', read_only=True)
    district_name = serializers.CharField(source='user.district', read_only=True)
    district_id = serializers.IntegerField(source='user.district_id', read_only=True)

    # Hospital information
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, allow_null=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)

    # Related data
    schedules = DoctorScheduleSerializer(many=True, read_only=True)
    specializations = DoctorSpecializationSerializer(many=True, read_only=True)
    files = DoctorFilesSerializer(read_only=True, many=True)
    profile_views = serializers.IntegerField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    services = DoctorServiceSerializer(many=True, read_only=True)
    translation_fields = ['bio', 'education', 'achievements']

    # Statistics
    average_rating = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'first_name','last_name', 'middle_name', 'work_days',
            'avatar', 'specialty', 'specialty_display',
            'degree', 'degree_display', 'experience', 'education', 'bio',
            'achievements', 'consultation_price', 'is_available',
            'is_online_consultation', 'workplace', 'workplace_address',
            'region_name', 'district_name', 'hospital_name', 'region_id', 'district_id',
            'verification_status', 'verification_status_display',
            'rating', 'total_reviews', 'total_consultations',
            'average_rating', 'recent_reviews', 'schedules',
            'specializations', 'files', 'profile_views', 'services', 'hospital_id', 'license_number', 'work_start_time',
            'work_end_time',
        ]

    def get_average_rating(self, obj):
        """Get average rating from reviews"""
        # This would need to be implemented based on your review model
        return obj.rating

    def get_recent_reviews(self, obj):
        """Get recent reviews (last 5)"""
        # This would need to be implemented based on your review model
        return []


class DoctorFileUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading doctor files separately"""

    class Meta:
        model = DoctorFiles
        fields = ['file_type', 'file']

    def create(self, validated_data):
        # The doctor should be set in the view
        return super().create(validated_data)


class DoctorLocationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating doctor location"""

    region_name = serializers.CharField(source='region.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = Doctor
        fields = ['region', 'district', 'region_name', 'district_name', 'workplace_address']

    def validate(self, attrs):
        """Validate region and district relationship"""
        region = attrs.get('region')
        district = attrs.get('district')

        if district and region and district.region != region:
            raise serializers.ValidationError(
                "Selected district does not belong to the selected region"
            )

        return attrs

