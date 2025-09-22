"""
Admin Panel Serializers for DRF
Comprehensive serializers for hospital and doctor management
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.hospitals.models import Hospital
from apps.doctors.models import Doctor, DoctorTranslation
from apps.consultations.models import Consultation
from .models import DoctorComplaint, DoctorComplaintFile
from ..doctors.services.translation_service import TranslationConfig

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for user information in admin panel"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'email', 'user_type', 'user_type_display',
            'is_active', 'is_verified', 'is_approved_by_admin',
            'created_at', 'last_login', 'region', 'district'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class AdminHospitalSerializer(serializers.ModelSerializer):
    """Serializer for hospital management in admin panel"""

    # Statistics fields
    doctor_count = serializers.SerializerMethodField()
    active_doctor_count = serializers.SerializerMethodField()
    total_consultations = serializers.SerializerMethodField()

    district = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    services = serializers.SerializerMethodField()


    # Display fields
    hospital_type_display = serializers.CharField(
        source='get_hospital_type_display',
        read_only=True
    )

    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'phone', 'email',
            'hospital_type', 'hospital_type_display',
            'region', 'district', 'website', 'description',
            'is_active',
            'doctor_count', 'active_doctor_count', 'total_consultations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_doctor_count(self, obj):
        """Get total number of doctors in hospital"""
        return obj.doctors.count()

    def get_active_doctor_count(self, obj):
        """Get number of active doctors in hospital"""
        return obj.doctors.filter(is_available=True).count()

    def get_total_consultations(self, obj):
        """Get total consultations for this hospital"""
        return Consultation.objects.filter(doctor__hospital=obj).count()

    def validate_phone(self, value):
        """Validate phone number format"""
        if value and not value.startswith('+998'):
            raise serializers.ValidationError(
                "Telefon raqam +998 bilan boshlanishi kerak"
            )
        return value

    def validate_email(self, value):
        """Validate email uniqueness"""
        if value:
            # Check if email exists for other hospitals
            if Hospital.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
                raise serializers.ValidationError("Bu email allaqachon ishlatilgan")
        return value

    def get_region(self, obj):
        """Get region name"""
        data = {
            'id': obj.region.id,
            'name': obj.region.name,
            'name_en': obj.region.name_en,
            'name_ru': obj.region.name_ru,
            'name_kr': obj.region.name_kr,
        } if obj.region else None
        return data

    def get_district(self, obj):
        """Get district name"""
        data = {
            'id': obj.district.id,
            'name': obj.district.name,
            'name_en': obj.district.name_en,
            'name_ru': obj.district.name_ru,
            'name_kr': obj.district.name_kr,
        } if obj.district else None
        return data

    def get_services(self, obj):
        """Get list of services offered by the hospital"""
        return [service.name for service in obj.services.all()]


class AdminDoctorSerializer(serializers.ModelSerializer):
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

    # Hospital information
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, allow_null=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True, allow_null=True)

    # Display fields
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    verification_status_display = serializers.CharField(
        source='get_verification_status_display',
        read_only=True
    )

    # Statistics
    consultation_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()

    # Approval information
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    rejected_by_name = serializers.CharField(
        source='rejected_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    region_name = serializers.CharField(source='user.region', read_only=True)
    region_name_en = serializers.CharField(source='user.region.name_en', read_only=True)
    region_name_ru = serializers.CharField(source='user.region.name_ru', read_only=True)
    region_name_kr = serializers.CharField(source='user.region.name_kr', read_only=True)
    region_id = serializers.IntegerField(source='user.region_id', read_only=True)

    district_name = serializers.CharField(source='user.district', read_only=True)
    district_name_en = serializers.CharField(source='user.district.name_en', read_only=True)
    district_name_ru = serializers.CharField(source='user.district.name_ru', read_only=True)
    district_name_kr = serializers.CharField(source='user.district.name_kr', read_only=True)
    district_id = serializers.IntegerField(source='user.district_id', read_only=True)

    translations = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            # Basic info
            'id', 'user_id', 'first_name', 'last_name', 'full_name',
            'phone', 'email', 'avatar', 'user_is_active', 'user_is_verified',
            'user_created_at',

            # Doctor specific
            'specialty', 'specialty_display', 'experience', 'degree',
            'license_number', 'workplace', 'workplace_address',
            'consultation_price', 'bio', 'achievements',
            'rating', 'total_reviews', 'total_consultations',

            # Hospital
            'hospital', 'hospital_name', 'hospital_id',

            # Availability
            'is_available', 'is_online_consultation',
            'work_start_time', 'work_end_time', 'work_days',

            # Verification
            'verification_status', 'verification_status_display',
            'approved_by_name',
            'rejected_by_name',

            # Statistics
            'consultation_count', 'success_rate',

            # Timestamps
            'created_at', 'updated_at',

            # location
            'latitude', 'longitude', 'region_name', 'region_name_en', 'region_name_ru', 'region_name_kr', 'region_id',
            'district_name', 'district_name_en', 'district_name_ru', 'district_name_kr', 'district_id',

            # Translations
            'translations'
        ]
        read_only_fields = [
            'id', 'user_id', 'rating', 'total_reviews', 'total_consultations',
            'created_at', 'updated_at'
        ]

    def get_translations(self, obj):
        """Get translations for bio and achievements"""
        try:
            return DoctorTranslation.objects.get(doctor=obj).translations
        except DoctorTranslation.DoesNotExist:
            return {
                'bio': {TranslationConfig.LANGUAGES[lang_item]:"" for lang_item in TranslationConfig.LANGUAGES},
                'achievements': {TranslationConfig.LANGUAGES[lang_item]:"" for lang_item in TranslationConfig.LANGUAGES},
                'education': {TranslationConfig.LANGUAGES[lang_item]:"" for lang_item in TranslationConfig.LANGUAGES},
                'workplace':{TranslationConfig.LANGUAGES[lang_item]:"" for lang_item in TranslationConfig.LANGUAGES},
                'workplace_address': {TranslationConfig.LANGUAGES[lang_item]:"" for lang_item in TranslationConfig.LANGUAGES}
            }

    def get_consultation_count(self, obj):
        """Get total consultation count"""
        return Consultation.objects.filter(doctor=obj).count()

    def get_success_rate(self, obj):
        """Calculate success rate based on completed consultations"""
        total = Consultation.objects.filter(doctor=obj).count()
        completed = Consultation.objects.filter(
            doctor=obj,
            status='completed'
        ).count()

        if total == 0:
            return 0
        return round((completed / total) * 100, 2)

    def validate_license_number(self, value):
        """Validate license number uniqueness"""
        if value:
            existing_doctor = Doctor.objects.filter(license_number=value)
            if self.instance:
                existing_doctor = existing_doctor.exclude(id=self.instance.id)

            if existing_doctor.exists():
                raise serializers.ValidationError(
                    "Bu litsenziya raqami allaqachon ishlatilgan"
                )
        return value

    def validate_consultation_price(self, value):
        """Validate consultation price"""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Konsultatsiya narxi 0 dan kichik bo'lishi mumkin emas"
            )
        return value

    def validate_experience(self, value):
        """Validate experience years"""
        if value is not None and (value < 0 or value > 60):
            raise serializers.ValidationError(
                "Tajriba 0 dan 60 yil orasida bo'lishi kerak"
            )
        return value


class AdminDoctorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new doctors from admin panel"""

    # User fields
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Doctor
        fields = [
            # User fields
            'first_name', 'last_name', 'middle_name', 'phone', 'email', 'password',

            # Doctor fields
            'specialty', 'experience', 'degree', 'license_number',
            'workplace', 'workplace_address', 'consultation_price',
            'bio', 'hospital', 'is_available', 'is_online_consultation',
            'work_start_time', 'work_end_time', 'work_days'
        ]

    def validate_phone(self, value):
        """Validate phone number"""
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon ro'yxatdan o'tgan"
            )
        return value

    def validate_email(self, value):
        """Validate email"""
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Bu email allaqachon ishlatilgan"
            )
        return value

    def create(self, validated_data):
        """Create new doctor with user account"""
        # Extract user data
        user_data = {
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'middle_name': validated_data.pop('middle_name', ''),
            'phone': validated_data.pop('phone'),
            'email': validated_data.pop('email', ''),
            'password': validated_data.pop('password'),
            'user_type': 'doctor',
            'is_approved_by_admin': True,  # Auto-approve admin created doctors
        }

        # Create user
        user = User.objects.create_user(**user_data)

        # Create doctor profile
        doctor = Doctor.objects.create(
            user=user,
            verification_status='approved',  # Auto-approve
            **validated_data
        )

        return doctor


class AdminStatisticsSerializer(serializers.Serializer):
    """Serializer for admin dashboard statistics"""

    # User statistics
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    patients = serializers.IntegerField()
    doctors = serializers.IntegerField()
    approved_doctors = serializers.IntegerField()
    pending_doctors = serializers.IntegerField()
    hospital_admins = serializers.IntegerField()

    # Hospital statistics
    total_hospitals = serializers.IntegerField()
    active_hospitals = serializers.IntegerField()
    hospitals_with_doctors = serializers.IntegerField()

    # Doctor statistics
    verified_doctors = serializers.IntegerField()
    rejected_doctors = serializers.IntegerField()
    available_doctors = serializers.IntegerField()

    # Consultation statistics
    total_consultations = serializers.IntegerField()
    completed_consultations = serializers.IntegerField()
    pending_consultations = serializers.IntegerField()
    cancelled_consultations = serializers.IntegerField()


class AdminHospitalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new hospitals from admin panel"""

    class Meta:
        model = Hospital
        fields = [
            'name', 'address', 'phone', 'email', 'hospital_type',
            'region', 'district', 'website', 'description',
            'license_number', 'established_date', 'bed_capacity',
            'emergency_services', 'is_active'
        ]

    def validate_name(self, value):
        """Validate hospital name uniqueness"""
        if Hospital.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli shifoxona allaqachon mavjud"
            )
        return value

    def validate_license_number(self, value):
        """Validate license number uniqueness"""
        if value and Hospital.objects.filter(license_number=value).exists():
            raise serializers.ValidationError(
                "Bu litsenziya raqami allaqachon ishlatilgan"
            )
        return value


class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions"""

    action = serializers.ChoiceField(choices=[
        ('approve', 'Tasdiqlash'),
        ('reject', 'Rad etish'),
        ('delete', 'O\'chirish'),
        ('activate', 'Faollashtirish'),
        ('deactivate', 'Faolsizlashtirish'),
    ])
    type = serializers.ChoiceField(choices=[
        ('doctors', 'Shifokorlar'),
        ('hospitals', 'Shifoxonalar'),
        ('users', 'Foydalanuvchilar'),
    ])
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate bulk action data"""
        action = data.get('action')
        item_type = data.get('type')

        # Check if reason is required for certain actions
        if action == 'reject' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Rad etish uchun sabab ko\'rsatish majburiy'
            })

        return data


class ExportDataSerializer(serializers.Serializer):
    """Serializer for data export"""

    type = serializers.ChoiceField(choices=[
        ('users', 'Foydalanuvchilar'),
        ('doctors', 'Shifokorlar'),
        ('hospitals', 'Shifoxonalar'),
        ('consultations', 'Konsultatsiyalar'),
    ])
    format = serializers.ChoiceField(choices=[
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('excel', 'Excel'),
    ])
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    filters = serializers.DictField(required=False)


class AdminDoctorUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating doctor information from admin panel"""

    # Allow updating some user fields
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    middle_name = serializers.CharField(source='user.middle_name', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', required=False, allow_blank=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)

    class Meta:
        model = Doctor
        fields = [
            # User fields
            'first_name', 'last_name', 'middle_name', 'email', 'is_active',

            # Doctor fields
            'specialty', 'experience', 'degree', 'license_number',
            'workplace', 'workplace_address', 'consultation_price',
            'bio', 'achievements', 'hospital', 'is_available',
            'is_online_consultation', 'work_start_time', 'work_end_time',
            'work_days', 'verification_status'
        ]

    def update(self, instance, validated_data):
        """Update doctor and related user information"""
        # Extract user data
        user_data = {}
        for field in ['first_name', 'last_name', 'middle_name', 'email', 'is_active']:
            if f'user.{field}' in validated_data:
                user_data[field] = validated_data.pop(f'user.{field}')

        # Update user fields
        if user_data:
            user = instance.user
            for field, value in user_data.items():
                setattr(user, field, value)
            user.save()

        # Update doctor fields
        return super().update(instance, validated_data)


class AdminFilterOptionsSerializer(serializers.Serializer):
    """Serializer for admin panel filter options"""

    specialties = serializers.DictField()
    verification_statuses = serializers.DictField()
    hospital_types = serializers.DictField()
    user_types = serializers.DictField()
    regions = serializers.ListField(child=serializers.CharField())


class AdminRecentActivitySerializer(serializers.Serializer):
    """Serializer for recent activity in admin dashboard"""

    activity_type = serializers.CharField()
    description = serializers.CharField()
    user_name = serializers.CharField()
    timestamp = serializers.DateTimeField()
    details = serializers.DictField(required=False)


class DoctorComplaintFileSerializer(serializers.ModelSerializer):
    """Serializer for DoctorComplaintFile model"""
    
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DoctorComplaintFile
        fields = [
            'id', 'file', 'file_url', 'file_name', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_file_url(self, obj):
        """Get file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        """Get original file name"""
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None


class DoctorComplaintSerializer(serializers.ModelSerializer):
    """Serializer for DoctorComplaint model with nested files"""
    
    # Doctor information
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_phone = serializers.CharField(source='doctor.user.phone', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.get_specialty_display', read_only=True)
    
    # Display fields
    complaint_type_display = serializers.CharField(source='get_complaint_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    # Files related to this complaint
    files = DoctorComplaintFileSerializer(many=True, read_only=True)
    files_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DoctorComplaint
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_phone', 'doctor_specialty',
            'subject', 'description', 'complaint_type', 'complaint_type_display',
            'status', 'status_display', 'priority', 'priority_display',
            'files', 'files_count', 'created_at', 'updated_at', 'resolution_notes'
        ]
        read_only_fields = ['id', 'priority', 'created_at', 'updated_at']
    
    def get_files_count(self, obj):
        """Get number of files attached to this complaint"""
        return obj.files.count()
    
    def validate_subject(self, value):
        """Validate complaint subject"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Shikoyat sarlavhasi kamida 5 ta belgidan iborat bo'lishi kerak"
            )
        return value.strip()
    
    def validate_description(self, value):
        """Validate complaint description"""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Shikoyat tavsifi kamida 10 ta belgidan iborat bo'lishi kerak"
            )
        return value.strip() if value else value


class AdminDoctorComplaintSerializer(DoctorComplaintSerializer):
    """Extended serializer for admin panel with additional fields"""
    
    # Hospital information
    hospital_name = serializers.CharField(
        source='doctor.hospital.name', 
        read_only=True, 
        allow_null=True
    )
    
    # Admin actions
    can_be_resolved = serializers.SerializerMethodField()
    days_since_created = serializers.SerializerMethodField()
    
    class Meta(DoctorComplaintSerializer.Meta):
        fields = DoctorComplaintSerializer.Meta.fields + [
            'hospital_name', 'can_be_resolved', 'days_since_created'
        ]
    
    def get_can_be_resolved(self, obj):
        """Check if complaint can be resolved"""
        return obj.status == 'in_progress'
    
    def get_days_since_created(self, obj):
        """Calculate days since complaint was created"""
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        return delta.days


class DoctorComplaintCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating doctor complaints"""
    
    class Meta:
        model = DoctorComplaint
        fields = [
            'doctor', 'subject', 'description', 'complaint_type', 'priority'
        ]
    
    def validate_doctor(self, value):
        """Validate doctor exists and is verified"""
        if not hasattr(value, 'verification_status'):
            raise serializers.ValidationError("Shifokor topilmadi")
        
        if value.verification_status != 'approved':
            raise serializers.ValidationError(
                "Faqat tasdiqlangan shifokorlar shikoyat yubora oladi"
            )
        return value
    
    def create(self, validated_data):
        """Create complaint with automatic priority setting"""
        complaint = super().create(validated_data)
        # Priority is automatically set by the model's save method
        return complaint


class DoctorComplaintUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating complaint status (admin only)"""
    
    resolution_notes = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Notes about complaint resolution"
    )
    
    class Meta:
        model = DoctorComplaint
        fields = ['status', 'resolution_notes']
    
    def validate_status(self, value):
        """Validate status transition"""
        if self.instance and self.instance.status == 'closed':
            raise serializers.ValidationError(
                "Yopilgan shikoyat holatini o'zgartirib bo'lmaydi"
            )
        return value
    
    def validate(self, data):
        """Validate status change"""
        status = data.get('status')
        if status == 'resolved' and not data.get('resolution_notes'):
            raise serializers.ValidationError({
                'resolution_notes': 'Shikoyatni yechish uchun izoh qoldirish majburiy'
            })
        return data


class DoctorComplaintStatisticsSerializer(serializers.Serializer):
    """Serializer for complaint statistics"""
    
    total_complaints = serializers.IntegerField()
    in_progress_complaints = serializers.IntegerField()
    resolved_complaints = serializers.IntegerField()
    closed_complaints = serializers.IntegerField()
    
    # By type
    general_complaints = serializers.IntegerField()
    service_complaints = serializers.IntegerField()
    billing_complaints = serializers.IntegerField()
    
    # By priority
    urgent_complaints = serializers.IntegerField()
    high_complaints = serializers.IntegerField()
    medium_complaints = serializers.IntegerField()
    low_complaints = serializers.IntegerField()
    
    # Time-based
    complaints_this_month = serializers.IntegerField()
    complaints_this_week = serializers.IntegerField()
    average_resolution_days = serializers.FloatField()