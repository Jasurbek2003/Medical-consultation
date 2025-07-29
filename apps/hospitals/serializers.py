from rest_framework import serializers

from apps.hospitals.models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    # Custom read-only field
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = ['id', 'name', "short_name", 'hospital_type', 'address', 'phone', 'email', 'full_address', 'website',
                  'logo', 'created_at', 'updated_at', 'is_active', 'is_verified', 'description', 'services',
                  'working_hours', 'total_doctors', 'total_patients', 'rating']

    def get_full_address(self, obj):
        # Custom method to format address
        return f"{obj.address}"

    def validate_phone(self, value):
        # Custom validation for phone field
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must include country code")
        return value