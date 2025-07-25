from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language
from rest_framework import serializers, status
from rest_framework.response import Response

from .models import Doctor, DoctorSchedule, DoctorSpecialization, DoctorTranslation
from .services.translation_service import TahrirchiTranslationService

User = get_user_model()


class DoctorSerializer(serializers.ModelSerializer):
    """Shifokor serializer (ro'yxat uchun)"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    short_name = serializers.CharField(source='get_short_name', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    age = serializers.SerializerMethodField()

    # Add these fields to access User model fields properly
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    region = serializers.CharField(source='user.region', read_only=True)
    district = serializers.CharField(source='user.district', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    language = serializers.CharField(source='user.language', read_only=True)


    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'short_name', 'first_name', 'last_name',
            'specialty', 'specialty_display', 'experience', 'degree',
            'rating', 'total_reviews', 'consultation_price',
            'workplace', 'region', 'district', 'phone', 'email',
            'is_available', 'is_online_consultation', 'avatar',
            'work_start_time', 'work_end_time', 'language', 'age', 'verification_status'
        ]

    def get_age(self, obj):
        """Calculate age based on experience or birth date"""
        if hasattr(obj.user, 'birth_date') and obj.user.birth_date:
            today = timezone.now().date()
            return today.year - obj.user.birth_date.year
        return obj.experience + 25  # Approximate age based on experience

class DoctorDetailSerializer(DoctorSerializer):
    """Shifokor batafsil serializer"""

    schedules = serializers.SerializerMethodField()
    specializations = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    middle_name = serializers.CharField(source='user.middle_name', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)

    class Meta(DoctorSerializer.Meta):
        fields = DoctorSerializer.Meta.fields + [
            'middle_name', 'bio', 'education', 'achievements',
            'address', 'workplace_address', 'work_days',
            'schedules', 'specializations', 'recent_reviews'
        ]

    def get_schedules(self, obj):
        schedules = obj.schedules.filter(is_available=True).order_by('weekday')
        return DoctorScheduleSerializer(schedules, many=True).data

    def get_specializations(self, obj):
        specializations = obj.specializations.all()
        return DoctorSpecializationSerializer(specializations, many=True).data

    def get_recent_reviews(self, obj):
        # Import here to avoid circular imports
        from apps.consultations.models import Review
        reviews = Review.objects.filter(doctor=obj, is_active=True, is_verified=True).order_by('-created_at')[:3]
        return [{
            'id': review.id,
            'patient_name': review.patient.get_full_name() or 'Anonim',
            'overall_rating': review.overall_rating,
            'title': review.title,
            'comment': review.comment[:100] + '...' if len(review.comment or '') > 100 else review.comment,
            'created_at': review.created_at.strftime('%d.%m.%Y')
        } for review in reviews]


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """Doctor profile update serializer"""

    class Meta:
        model = Doctor
        fields = [
            'bio', 'education', 'achievements', 'consultation_price',
            'is_available', 'is_online_consultation', 'work_start_time',
            'work_end_time', 'work_days', 'languages', 'photo'
        ]

    def validate_consultation_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Konsultatsiya narxi manfiy bo'lishi mumkin emas")
        if value > 10000000:  # 10 million
            raise serializers.ValidationError("Konsultatsiya narxi juda yuqori")
        return value


class DoctorStatisticsSerializer(serializers.Serializer):
    """Doctor statistics serializer"""

    # Basic stats
    total_consultations = serializers.IntegerField()
    completed_consultations = serializers.IntegerField()
    cancelled_consultations = serializers.IntegerField()
    pending_consultations = serializers.IntegerField()

    # Ratings and reviews
    overall_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    five_star_reviews = serializers.IntegerField()
    four_star_reviews = serializers.IntegerField()
    three_star_reviews = serializers.IntegerField()
    two_star_reviews = serializers.IntegerField()
    one_star_reviews = serializers.IntegerField()

    # View statistics
    profile_views = serializers.IntegerField()
    weekly_views = serializers.IntegerField()
    monthly_views = serializers.IntegerField()

    # Financial stats
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    weekly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)

    # Time-based stats
    avg_consultation_duration = serializers.FloatField()
    avg_response_time = serializers.FloatField()

    # Success rates
    success_rate = serializers.FloatField()
    patient_satisfaction = serializers.FloatField()

    # Monthly consultation trends (last 6 months)
    monthly_consultation_trends = serializers.ListField(
        child=serializers.DictField()
    )

    # Specialty-specific stats
    specialty_ranking = serializers.IntegerField()
    specialty_total_doctors = serializers.IntegerField()


class DoctorProfileSerializer(serializers.ModelSerializer):
    """Doctor profile serializer for users app"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, allow_null=True)

    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialty', 'specialty_display',
            'experience', 'degree', 'rating', 'total_reviews',
            'consultation_price', 'is_available', 'is_online_consultation',
            'hospital_name', 'workplace', 'verification_status',
            'total_consultations', 'success_rate', 'avatar'
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
        fields = ['id', 'name', 'description', 'certificate']


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
        help_text='Username must be unique and can only contain letters, numbers, and underscores.',
    )

    # Doctor-specific fields
    specialty = serializers.ChoiceField(choices=Doctor.SPECIALTIES, required=True)
    degree = serializers.ChoiceField(choices=Doctor.DEGREES, required=True)
    license_number = serializers.CharField(max_length=50)
    experience = serializers.IntegerField(min_value=0, max_value=60, required=True)
    education = serializers.CharField(required=True)
    workplace = serializers.CharField(max_length=200, required=True)
    workplace_address = serializers.CharField(max_length=500, required=False)
    consultation_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    achievements = serializers.CharField(required=False, allow_blank=True)

    # Working hours
    work_start_time = serializers.TimeField(required=False)
    work_end_time = serializers.TimeField(required=False)
    work_days = serializers.CharField(max_length=100, required=False)

    # Options
    is_online_consultation = serializers.BooleanField(default=False)

    # File uploads
    diploma_image = serializers.ImageField(required=True)
    license_image = serializers.ImageField(required=False)

    avatar = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = [
            # User fields
            'phone', 'password', 'password_confirm', 'username', 'avatar',
            'first_name', 'last_name', 'middle_name',
            'email', 'birth_date', 'gender',
            'region', 'district', 'address',
            'language',
            # Doctor fields
            'specialty', 'degree', 'license_number',
            'experience', 'education', 'workplace',
            'workplace_address', 'consultation_price',
            'bio', 'achievements', 'work_start_time',
            'work_end_time', 'work_days', 'is_online_consultation',
            'diploma_image', 'license_image'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birth_date': {'required': True},
            'gender': {'required': True},
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

    def validate_username(self, value):
        """Check if username already exists"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Username already exists. Please choose a different one."
            )
        return value

    def validate_license_number(self, value):
        """Check if license number already exists"""
        if value and Doctor.objects.filter(license_number=value).exists() :
            raise serializers.ValidationError(
                "Doctor with this license number already exists."
            )
        return value

    def create(self, validated_data):
        """Create user and doctor profile"""
        # Extract doctor-specific data
        doctor_data = {
            'specialty': validated_data.pop('specialty'),
            'degree': validated_data.pop('degree'),
            'license_number': validated_data.pop('license_number'),
            'experience': validated_data.pop('experience'),
            'education': validated_data.pop('education'),
            'workplace': validated_data.pop('workplace'),
            'workplace_address': validated_data.pop('workplace_address', ''),
            'consultation_price': validated_data.pop('consultation_price'),
            'bio': validated_data.pop('bio', ''),
            'achievements': validated_data.pop('achievements', ''),
            'work_start_time': validated_data.pop('work_start_time', None),
            'work_end_time': validated_data.pop('work_end_time', None),
            'work_days': validated_data.pop('work_days', ''),
            'is_online_consultation': validated_data.pop('is_online_consultation', False),
            'diploma_image': validated_data.pop('diploma_image'),
            'license_image': validated_data.pop('license_image', None),
        }

        # Remove password fields
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        username = validated_data.pop('username')

        # Create user and doctor profile in transaction
        with transaction.atomic():
            # Create user with doctor type
            user = User.objects.create(
                username=username,  # Use phone as username
                user_type='doctor',
                **validated_data
            )
            user.set_password(password)  # Set password
            user.save()

            # Create doctor profile
            doctor = Doctor.objects.create(
                user=user,
                **doctor_data
            )

            # Create user preferences
            from apps.users.models import UserPreferences
            UserPreferences.objects.get_or_create(
                user=user,
                defaults={'preferred_language': validated_data.get('language', 'uz')}
            )

        return user


class DoctorLoginSerializer(serializers.Serializer):
    """Doctor login serializer"""

    username = serializers.CharField(
        required=True,
        max_length=150,
        help_text='Username must be unique and can only contain letters, numbers, and underscores.',
        style={'input_type': 'text'}
    )
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate credentials and check if user is a doctor"""
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Try to authenticate
            user = User.objects.filter(username=username).first()

            if not user:
                raise serializers.ValidationError('Invalid phone number or password.')

            if not user.check_password(password):
                raise serializers.ValidationError('Invalid phone number or password.')

            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')

            # Check if user is a doctor
            if user.user_type != 'doctor':
                raise serializers.ValidationError('This account is not registered as a doctor.')

            # Check if doctor profile exists
            if not hasattr(user, 'doctor_profile'):
                raise serializers.ValidationError('Doctor profile not found.')

            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include "username" and "password".')

        return attrs


class DoctorProfileUpdateSerializer(serializers.ModelSerializer):
    """Update doctor profile information"""

    # User fields that can be updated
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    middle_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False)

    # Doctor fields
    workplace = serializers.CharField(required=False)
    workplace_address = serializers.CharField(required=False)
    consultation_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    achievements = serializers.CharField(required=False, allow_blank=True)
    is_available = serializers.BooleanField(required=False)
    is_online_consultation = serializers.BooleanField(required=False)
    work_start_time = serializers.TimeField(required=False)
    work_end_time = serializers.TimeField(required=False)
    work_days = serializers.CharField(required=False)

    class Meta:
        model = Doctor
        fields = [
            # User fields
            'first_name', 'last_name', 'middle_name', 'email', 'avatar',
            # Doctor fields
            'workplace', 'workplace_address', 'consultation_price',
            'bio', 'achievements', 'is_available', 'is_online_consultation',
            'work_start_time', 'work_end_time', 'work_days'
        ]

    def update(self, instance, validated_data):
        """Update doctor and user information"""
        # Extract user fields
        user_fields = ['first_name', 'last_name', 'middle_name', 'email', 'avatar']
        user_data = {}

        for field in user_fields:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)

        # Update user fields if any
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        # Update doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class DoctorTranslationSerializer(serializers.ModelSerializer):
    """Doctor translation serializer"""

    available_languages = serializers.SerializerMethodField()
    translation_stats = serializers.SerializerMethodField()

    class Meta:
        model = DoctorTranslation
        fields = [
            'id', 'doctor', 'translations', 'source_language',
            'last_updated', 'is_auto_translated', 'is_verified',
            'verified_by', 'created_at', 'available_languages',
            'translation_stats'
        ]

    def get_available_languages(self, obj):
        """Get list of available languages"""
        return obj.get_available_languages()

    def get_translation_stats(self, obj):
        """Get translation statistics"""
        stats = {
            'total_fields': 0,
            'translated_fields': 0,
            'languages': {},
        }

        for field_name, field_translations in obj.translations.items():
            stats['total_fields'] += 1
            if isinstance(field_translations, dict):
                for lang, translation in field_translations.items():
                    if translation and translation.strip():
                        stats['translated_fields'] += 1
                        if lang not in stats['languages']:
                            stats['languages'][lang] = 0
                        stats['languages'][lang] += 1

        return stats


class TranslatedDoctorSerializer(DoctorSerializer):
    """Doctor serializer with translation support"""

    # Translated fields
    bio_translated = serializers.SerializerMethodField()
    education_translated = serializers.SerializerMethodField()
    achievements_translated = serializers.SerializerMethodField()
    workplace_translated = serializers.SerializerMethodField()
    workplace_address_translated = serializers.SerializerMethodField()

    # Translation metadata
    has_translations = serializers.SerializerMethodField()
    available_languages = serializers.SerializerMethodField()

    class Meta(DoctorSerializer.Meta):
        fields = DoctorSerializer.Meta.fields + [
            'bio_translated', 'education_translated', 'achievements_translated',
            'workplace_translated', 'workplace_address_translated',
            'has_translations', 'available_languages'
        ]

    def _get_language(self):
        """Get language from request or default"""
        request = self.context.get('request')
        if request:
            return request.query_params.get('language', get_language())
        return get_language()

    def get_bio_translated(self, obj):
        language = self._get_language()
        return obj.get_bio_translated(language)

    def get_education_translated(self, obj):
        language = self._get_language()
        return obj.get_education_translated(language)

    def get_achievements_translated(self, obj):
        language = self._get_language()
        return obj.get_achievements_translated(language)

    def get_workplace_translated(self, obj):
        language = self._get_language()
        return obj.get_workplace_translated(language)

    def get_workplace_address_translated(self, obj):
        language = self._get_language()
        return obj.get_translated_field('workplace_address', self._get_language())

    def get_has_translations(self, obj):
        return obj.has_translations()

    def get_available_languages(self, obj):
        return obj.get_translation_languages()


class TextTranslationSerializer(serializers.Serializer):
    """Serializer for text translation requests"""

    text = serializers.CharField(required=True, max_length=5000)
    source_lang = serializers.CharField(default='uzn_Latn', max_length=10)
    target_lang = serializers.CharField(default='rus_Cyrl', max_length=10)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Text cannot be empty")
        return value

    def validate_source_lang(self, value):
        from .services.translation_service import TranslationConfig
        config = TranslationConfig()
        if value not in config.LANGUAGES.values():
            raise serializers.ValidationError(f"Unsupported source language: {value}")
        return value

    def validate_target_lang(self, value):
        from .services.translation_service import TranslationConfig
        config = TranslationConfig()
        if value not in config.LANGUAGES.values():
            raise serializers.ValidationError(f"Unsupported target language: {value}")
        return value


class BatchTranslationSerializer(serializers.Serializer):
    """Serializer for batch translation requests"""

    texts = serializers.ListField(
        child=serializers.CharField(max_length=5000),
        max_length=100,
        min_length=1
    )
    source_lang = serializers.CharField(default='uzn_Latn', max_length=10)
    target_lang = serializers.CharField(default='rus_Cyrl', max_length=10)

    def validate_texts(self, value):
        if not value:
            raise serializers.ValidationError("At least one text is required")

        # Check for empty texts
        for i, text in enumerate(value):
            if not text.strip():
                raise serializers.ValidationError(f"Text at index {i} cannot be empty")

        return value

def translate_text_api(request):
    """API endpoint for translating arbitrary text"""

    text = request.data.get('text')
    source_lang = request.data.get('source_lang', 'uzn_Latn')
    target_lang = request.data.get('target_lang', 'rus_Cyrl')

    if not text:
        return Response(
            {'error': 'Text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        translator = TahrirchiTranslationService()
        translated_text = translator.translate_text(text, source_lang, target_lang)

        if translated_text:
            return Response({
                'original_text': text,
                'translated_text': translated_text,
                'source_language': source_lang,
                'target_language': target_lang
            })
        else:
            return Response(
                {'error': 'Translation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        return Response(
            {'error': f'Translation error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )