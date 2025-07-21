from django.core.validators import RegexValidator
from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserMedicalHistory, UserPreferences

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    phone = serializers.CharField(max_length=13)
    password = serializers.CharField(max_length=128, write_only=True)


class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'phone', 'password', 'password_confirm',
            'first_name', 'last_name', 'email',
            'user_type', 'birth_date', 'gender'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Parollar mos kelmaydi")
        return attrs

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan")
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    """Doctor registration serializer"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    # Doctor-specific fields
    specialty = serializers.CharField(max_length=50)
    license_number = serializers.CharField(max_length=50)
    experience = serializers.IntegerField(min_value=0, max_value=60)
    education = serializers.CharField()
    workplace = serializers.CharField(max_length=200)
    consultation_price = serializers.IntegerField(min_value=0)

    # Document uploads
    diploma_image = serializers.ImageField(required=False)
    license_image = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = [
            'phone', 'password', 'password_confirm',
            'first_name', 'last_name', 'middle_name', 'email',
            'birth_date', 'gender', 'region', 'district', 'address',
            'specialty', 'license_number', 'experience', 'education',
            'workplace', 'consultation_price', 'diploma_image', 'license_image'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Parollar mos kelmaydi")
        return attrs

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan")
        return value

    def validate_license_number(self, value):
        from apps.doctors.models import Doctor
        if Doctor.objects.filter(license_number=value).exists():
            raise serializers.ValidationError("Bu litsenziya raqami allaqachon ishlatilgan")
        return value

    def create(self, validated_data):
        # Extract doctor-specific data
        doctor_data = {
            'specialty': validated_data.pop('specialty'),
            'license_number': validated_data.pop('license_number'),
            'experience': validated_data.pop('experience'),
            'education': validated_data.pop('education'),
            'workplace': validated_data.pop('workplace'),
            'consultation_price': validated_data.pop('consultation_price'),
        }

        # Handle file uploads
        diploma_image = validated_data.pop('diploma_image', None)
        license_image = validated_data.pop('license_image', None)

        if diploma_image:
            doctor_data['diploma_image'] = diploma_image
        if license_image:
            doctor_data['license_image'] = license_image

        # Create user
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        validated_data['user_type'] = 'doctor'

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        # Create doctor profile
        from apps.doctors.models import Doctor
        Doctor.objects.create(
            user=user,
            **doctor_data
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    bmi = serializers.FloatField(source='get_bmi', read_only=True)
    bmi_category = serializers.CharField(source='get_bmi_category', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'middle_name', 'full_name',
            'email', 'phone', 'birth_date', 'age', 'gender', 'user_type',
            'blood_type', 'height', 'weight', 'bmi', 'bmi_category',
            'allergies', 'chronic_diseases', 'current_medications',
            'region', 'district', 'address', 'avatar', 'language',
            'notifications_enabled', 'is_profile_complete', 'is_verified',
            'is_approved_by_admin', 'created_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserProfileSerializer(UserSerializer):
    """Extended user profile serializer"""

    medical_history = serializers.SerializerMethodField()
    preferences = serializers.SerializerMethodField()
    doctor_profile = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'email_notifications',
            'sms_notifications', 'medical_history', 'preferences',
            'doctor_profile', 'approval_date', 'last_login_ip'
        ]

    def get_medical_history(self, obj):
        if obj.is_patient():
            history = obj.medical_history.filter(is_active=True).order_by('-date_recorded')[:5]
            return UserMedicalHistorySerializer(history, many=True).data
        return None

    def get_preferences(self, obj):
        try:
            return UserPreferencesSerializer(obj.preferences).data
        except UserPreferences.DoesNotExist:
            return None

    def get_doctor_profile(self, obj):
        if obj.is_doctor() and hasattr(obj, 'doctor_profile'):
            from apps.doctors.serializers import DoctorProfileSerializer
            return DoctorProfileSerializer(obj.doctor_profile).data
        return None


class UserMedicalHistorySerializer(serializers.ModelSerializer):
    """Medical history serializer"""

    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)

    class Meta:
        model = UserMedicalHistory
        fields = [
            'id', 'record_type', 'record_type_display', 'title',
            'description', 'date_recorded', 'doctor_name',
            'hospital_name', 'attachment', 'is_active', 'created_at'
        ]


class UserPreferencesSerializer(serializers.ModelSerializer):
    """User preferences serializer"""

    class Meta:
        model = UserPreferences
        fields = [
            'preferred_language', 'preferred_doctor_gender',
            'max_consultation_price', 'preferred_consultation_time',
            'auto_save_history', 'share_data_for_research'
        ]


class UserStatisticsSerializer(serializers.Serializer):
    """User statistics serializer"""

    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    patients = serializers.IntegerField()
    doctors = serializers.IntegerField()
    approved_doctors = serializers.IntegerField()
    pending_doctors = serializers.IntegerField()
    hospital_admins = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()


class AdminUserManagementSerializer(serializers.ModelSerializer):
    """Admin user management serializer"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    doctor_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email', 'user_type',
            'is_active', 'is_verified', 'is_approved_by_admin',
            'created_at', 'last_login', 'doctor_profile'
        ]

    def get_doctor_profile(self, obj):
        if obj.is_doctor() and hasattr(obj, 'doctor_profile'):
            return {
                'specialty': obj.doctor_profile.get_specialty_display(),
                'license_number': obj.doctor_profile.license_number,
                'experience': obj.doctor_profile.experience,
                'verification_status': obj.doctor_profile.verification_status,
                'rating': obj.doctor_profile.rating,
                'total_consultations': obj.doctor_profile.total_consultations
            }
        return None


class HospitalAdminUserSerializer(serializers.ModelSerializer):
    """Hospital admin view of users"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    doctor_stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email',
            'is_active', 'is_verified', 'created_at',
            'doctor_stats'
        ]

    def get_doctor_stats(self, obj):
        if obj.is_doctor() and hasattr(obj, 'doctor_profile'):
            doctor = obj.doctor_profile
            return {
                'specialty': doctor.get_specialty_display(),
                'experience': doctor.experience,
                'rating': doctor.rating,
                'total_consultations': doctor.total_consultations,
                'total_reviews': doctor.total_reviews,
                'profile_views': doctor.profile_views,
                'weekly_views': doctor.weekly_views,
                'monthly_views': doctor.monthly_views,
                'is_available': doctor.is_available
            }
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """User update serializer"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'middle_name', 'email',
            'birth_date', 'gender', 'blood_type', 'height', 'weight',
            'allergies', 'chronic_diseases', 'current_medications',
            'region', 'district', 'address', 'avatar', 'language',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'notifications_enabled',
            'email_notifications', 'sms_notifications'
        ]

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Bu email allaqachon ishlatilgan")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Password change serializer"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Yangi parollar mos kelmaydi")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Eski parol noto'g'ri")
        return value


class UserApprovalSerializer(serializers.Serializer):
    """User approval serializer"""

    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs['action'] == 'reject' and not attrs.get('reason'):
            raise serializers.ValidationError("Rad etish uchun sabab ko'rsatish kerak")
        return attrs


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Enhanced user registration serializer"""

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

    class Meta:
        model = User
        fields = [
            'phone', 'password', 'password_confirm',
            'first_name', 'last_name', 'middle_name',
            'email', 'birth_date', 'gender',
            'blood_type', 'height', 'weight',
            'region', 'district', 'address',
            'allergies', 'chronic_diseases', 'current_medications',
            'language'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': False},
        }

    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs

    def validate_phone(self, value):
        """Check if phone number already exists"""
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "User with this phone number already exists."
            )
        return value

    def create(self, validated_data):
        """Create user with validated data"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        # Set username as phone number if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data['phone']

        # Create user
        with transaction.atomic():
            user = User.objects.create_user(
                password=password,
                **validated_data
            )

            # Create user preferences
            from .models import UserPreferences
            UserPreferences.objects.create(
                user=user,
                preferred_language=validated_data.get('language', 'uz')
            )

        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    bmi = serializers.FloatField(source='get_bmi', read_only=True)
    bmi_category = serializers.CharField(source='get_bmi_category', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'middle_name',
            'full_name', 'birth_date', 'age', 'gender', 'avatar',
            'blood_type', 'height', 'weight', 'bmi', 'bmi_category',
            'allergies', 'chronic_diseases', 'current_medications',
            'region', 'district', 'address', 'language',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'notifications_enabled',
            'email_notifications', 'sms_notifications',
            'is_profile_complete', 'is_verified'
        ]
        read_only_fields = [
            'id', 'phone', 'is_profile_complete', 'is_verified',
            'full_name', 'age', 'bmi', 'bmi_category'
        ]
        extra_kwargs = {
            'avatar': {'required': False},
        }

    def update(self, instance, validated_data):
        """Update user profile with automatic profile completeness check"""

        # Update user instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Check and update profile completeness
        instance.check_profile_completeness()
        instance.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""

    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password": "New password fields didn't match."
            })
        return attrs

    def validate_old_password(self, value):
        """Validate old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "Old password is not correct."
            )
        return value