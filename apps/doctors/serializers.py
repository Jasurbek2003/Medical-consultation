from rest_framework import serializers
from .models import Doctor, DoctorSchedule, DoctorSpecialization


class DoctorSerializer(serializers.ModelSerializer):
    """Shifokor serializer (ro'yxat uchun)"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    short_name = serializers.CharField(source='get_short_name', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    age = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'short_name', 'first_name', 'last_name',
            'specialty', 'specialty_display', 'experience', 'degree',
            'rating', 'total_reviews', 'consultation_price',
            'workplace', 'region', 'district', 'phone', 'email',
            'is_available', 'is_online_consultation', 'photo',
            'work_start_time', 'work_end_time', 'languages', 'age'
        ]

    def get_age(self, obj):
        """Tajribaga asoslangan yosh"""
        return obj.experience + 25  # Taxminiy yosh


class DoctorDetailSerializer(DoctorSerializer):
    """Shifokor batafsil serializer"""

    schedules = serializers.SerializerMethodField()
    specializations = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()

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
        reviews = obj.reviews.filter(is_active=True, is_verified=True).order_by('-created_at')[:3]
        return [{
            'id': review.id,
            'patient_name': review.patient.get_full_name() or 'Anonim',
            'overall_rating': review.overall_rating,
            'title': review.title,
            'comment': review.comment[:100] + '...' if len(review.comment or '') > 100 else review.comment,
            'created_at': review.created_at.strftime('%d.%m.%Y')
        } for review in reviews]


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

