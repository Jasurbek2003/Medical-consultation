from rest_framework import serializers

from apps.hospitals.models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    # Custom read-only field
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = ['id', 'name', 'address', 'phone', 'email', 'full_address']

    def get_full_address(self, obj):
        # Custom method to format address
        return f"{obj.address}"

    def validate_phone(self, value):
        # Custom validation for phone field
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must include country code")
        return value