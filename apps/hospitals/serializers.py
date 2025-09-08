from rest_framework import serializers

from apps.hospitals.models import Hospital, Regions, Districts


class HospitalSerializer(serializers.ModelSerializer):
    # Custom read-only field
    full_address = serializers.SerializerMethodField()


    class Meta:
        model = Hospital
        fields = ['id', 'name', "short_name", 'hospital_type', 'address', 'phone', 'email', 'full_address', 'website',
                  'logo', 'created_at', 'updated_at', 'is_active', 'is_verified', 'description','founded_year',
                  'working_hours', 'total_doctors', 'total_patients', 'rating', 'latitude', 'longitude',
                  'working_days']



class RegionSerializer(serializers.ModelSerializer):
    """Viloyat serializer"""

    class Meta:
        model = Regions
        fields = ['id', 'name', 'name_en', 'name_ru', 'name_kr']


class DistrictSerializer(serializers.ModelSerializer):
    """Tuman serializer"""

    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = Districts
        fields = ['id', 'name', 'region', 'region_name', 'name_en', 'name_ru', 'name_kr']