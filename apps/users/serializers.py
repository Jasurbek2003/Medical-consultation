from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserMedicalHistory, UserPreferences

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Foydalanuvchi serializer"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    bmi = serializers.FloatField(source='get_bmi', read_only=True)
    bmi_category = serializers.CharField(source='get_bmi_category', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'birth_date', 'age', 'gender',
            'blood_type', 'height', 'weight', 'bmi', 'bmi_category',
            'allergies', 'chronic_diseases', 'current_medications',
            'region', 'district', 'address', 'avatar', 'language',
            'notifications_enabled', 'is_profile_complete', 'created_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserProfileSerializer(UserSerializer):
    """Foydalanuvchi profil serializer (kengaytirilgan)"""

    medical_history = serializers.SerializerMethodField()
    preferences = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'email_notifications',
            'sms_notifications', 'medical_history', 'preferences'
        ]

    def get_medical_history(self, obj):
        history = obj.medical_history.filter(is_active=True).order_by('-date_recorded')[:5]
        return UserMedicalHistorySerializer(history, many=True).data

    def get_preferences(self, obj):
        try:
            return UserPreferencesSerializer(obj.preferences).data
        except UserPreferences.DoesNotExist:
            return None


class UserMedicalHistorySerializer(serializers.ModelSerializer):
    """Tibbiy tarix serializer"""

    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)

    class Meta:
        model = UserMedicalHistory
        fields = [
            'id', 'record_type', 'record_type_display', 'title',
            'description', 'date_recorded', 'doctor_name',
            'hospital_name', 'attachment', 'is_active', 'created_at'
        ]


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Foydalanuvchi parametrlari serializer"""

    class Meta:
        model = UserPreferences
        fields = [
            'preferred_language', 'preferred_doctor_gender',
            'max_consultation_price', 'preferred_consultation_time',
            'auto_save_history', 'share_data_for_research'
        ]
