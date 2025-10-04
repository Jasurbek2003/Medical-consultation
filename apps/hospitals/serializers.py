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


class HospitalSearchLimitSerializer(serializers.ModelSerializer):
    """Serializer for managing hospital's daily search limit"""

    class Meta:
        model = Hospital
        fields = ['id', 'daily_search_limit']
        read_only_fields = ['id']

    def validate_daily_search_limit(self, value):
        """Validate search limit is not negative"""
        if value < 0:
            raise serializers.ValidationError("Daily search limit cannot be negative. Use 0 for unlimited.")
        return value


class HospitalSearchStatsSerializer(serializers.Serializer):
    """Serializer for hospital search statistics"""

    total_searches = serializers.IntegerField(read_only=True)
    unique_ips = serializers.IntegerField(read_only=True)
    authenticated_searches = serializers.IntegerField(read_only=True)
    unauthenticated_searches = serializers.IntegerField(read_only=True)
    period_days = serializers.IntegerField(read_only=True)
    by_date = serializers.ListField(read_only=True)
    current_limit = serializers.IntegerField(read_only=True)