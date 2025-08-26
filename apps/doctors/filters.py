import django_filters
from django.db.models import Q
from .models import Doctor, DoctorFiles
from ..hospitals.models import Regions, Districts


class DoctorFilter(django_filters.FilterSet):
    """Enhanced doctor filtering with location support"""

    # Basic filters
    specialty = django_filters.ChoiceFilter(
        choices=Doctor.SPECIALTIES,
        help_text="Filter by specialty"
    )

    verification_status = django_filters.ChoiceFilter(
        choices=Doctor.VERIFICATION_STATUS,
        help_text="Filter by verification status"
    )

    is_available = django_filters.BooleanFilter(
        help_text="Filter by availability"
    )

    is_online_consultation = django_filters.BooleanFilter(
        help_text="Filter by online consultation availability"
    )

    # Location filters - Now using ForeignKey relationships
    region = django_filters.ModelChoiceFilter(
        queryset=Regions.objects.all(),
        field_name='region',
        help_text="Filter by region"
    )

    district = django_filters.ModelChoiceFilter(
        queryset=Districts.objects.all(),
        field_name='district',
        help_text="Filter by district"
    )

    # Experience filters
    min_experience = django_filters.NumberFilter(
        field_name='experience',
        lookup_expr='gte',
        help_text="Minimum years of experience"
    )

    max_experience = django_filters.NumberFilter(
        field_name='experience',
        lookup_expr='lte',
        help_text="Maximum years of experience"
    )

    # Price filters
    min_price = django_filters.NumberFilter(
        field_name='consultation_price',
        lookup_expr='gte',
        help_text="Minimum consultation price"
    )

    max_price = django_filters.NumberFilter(
        field_name='consultation_price',
        lookup_expr='lte',
        help_text="Maximum consultation price"
    )

    # Rating filter
    min_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte',
        help_text="Minimum rating"
    )

    # Hospital filter
    hospital = django_filters.NumberFilter(
        field_name='hospital',
        help_text="Filter by hospital ID"
    )

    # Language filter (assuming this field exists in Doctor model)
    languages = django_filters.CharFilter(
        method='filter_languages',
        help_text="Filter by supported languages"
    )

    # Search filters
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="Search by name, specialty, workplace, or bio"
    )

    name = django_filters.CharFilter(
        method='filter_name',
        help_text="Search by doctor name"
    )

    # Availability filters
    available_now = django_filters.BooleanFilter(
        method='filter_available_now',
        help_text="Filter doctors available right now"
    )

    has_schedule = django_filters.BooleanFilter(
        method='filter_has_schedule',
        help_text="Filter doctors with defined schedules"
    )

    # Experience level filter
    experience_level = django_filters.ChoiceFilter(
        method='filter_experience_level',
        choices=[
            ('junior', 'Junior (0-5 years)'),
            ('mid', 'Mid-level (6-15 years)'),
            ('senior', 'Senior (16+ years)'),
        ],
        help_text="Filter by experience level"
    )

    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter doctors registered after this date"
    )

    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter doctors registered before this date"
    )

    class Meta:
        model = Doctor
        fields = [
            'specialty', 'verification_status', 'is_available',
            'is_online_consultation', 'region', 'district',
            'min_experience', 'max_experience', 'min_price',
            'max_price', 'min_rating', 'hospital', 'languages'
        ]

    def filter_search(self, queryset, name, value):
        """General search - name, specialty, workplace, bio, location"""
        if value:
            return queryset.filter(
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value) |
                Q(specialty__icontains=value) |
                Q(workplace__icontains=value) |
                Q(bio__icontains=value) |
                Q(region__name__icontains=value) |
                Q(district__name__icontains=value)
            )
        return queryset

    def filter_name(self, queryset, name, value):
        """Search by first and last name"""
        if value:
            return queryset.filter(
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value)
            )
        return queryset

    def filter_languages(self, queryset, name, value):
        """Filter by supported languages"""
        if value:
            # Assuming languages is stored as JSON or comma-separated
            return queryset.filter(languages__icontains=value)
        return queryset

    def filter_available_now(self, queryset, name, value):
        """Filter doctors available right now"""
        if value:
            from datetime import datetime
            current_time = datetime.now().time()
            current_weekday = datetime.now().weekday()

            # Map Python weekday to your schedule weekday format
            weekday_map = {
                0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday',
                4: 'friday', 5: 'saturday', 6: 'sunday'
            }
            current_weekday_str = weekday_map[current_weekday]

            return queryset.filter(
                is_available=True,
                verification_status='approved',
                schedules__weekday=current_weekday_str,
                schedules__start_time__lte=current_time,
                schedules__end_time__gte=current_time,
                schedules__is_available=True
            ).distinct()
        return queryset

    def filter_has_schedule(self, queryset, name, value):
        """Filter doctors with defined schedules"""
        if value:
            return queryset.filter(schedules__isnull=False).distinct()
        return queryset

    def filter_experience_level(self, queryset, name, value):
        """Filter by experience level"""
        if value == 'junior':
            return queryset.filter(experience__lte=5)
        elif value == 'mid':
            return queryset.filter(experience__gte=6, experience__lte=15)
        elif value == 'senior':
            return queryset.filter(experience__gte=16)
        return queryset


class DoctorLocationFilter(django_filters.FilterSet):
    """Specialized filter for location-based doctor search"""

    region = django_filters.ModelChoiceFilter(
        queryset=Regions.objects.all(),
        field_name='region'
    )

    district = django_filters.ModelChoiceFilter(
        queryset=Districts.objects.all(),
        field_name='district'
    )

    # Custom method to filter districts by region
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If region is provided, filter districts accordingly
        if 'region' in self.data:
            try:
                region_id = int(self.data['region'])
                self.filters['district'].queryset = Districts.objects.filter(
                    region_id=region_id
                )
            except (ValueError, TypeError):
                pass

    class Meta:
        model = Doctor
        fields = ['region', 'district']


class DoctorFileFilter(django_filters.FilterSet):
    """Filter for doctor files"""

    from .models import DoctorFiles

    doctor = django_filters.NumberFilter(
        field_name='doctor__id',
        help_text="Filter by doctor ID"
    )

    file_type = django_filters.ChoiceFilter(
        choices=DoctorFiles.FILE_TYPES,
        help_text="Filter by file type"
    )

    uploaded_after = django_filters.DateTimeFilter(
        field_name='uploaded_at',
        lookup_expr='gte',
        help_text="Filter files uploaded after this date"
    )

    uploaded_before = django_filters.DateTimeFilter(
        field_name='uploaded_at',
        lookup_expr='lte',
        help_text="Filter files uploaded before this date"
    )

    class Meta:
        model = DoctorFiles
        fields = ['doctor', 'file_type']


class RegionFilter(django_filters.FilterSet):
    """Filter for regions"""

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text="Search by region name"
    )

    class Meta:
        model = Regions
        fields = ['name']


class DistrictFilter(django_filters.FilterSet):
    """Filter for districts"""

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text="Search by district name"
    )

    region = django_filters.ModelChoiceFilter(
        queryset=Regions.objects.all(),
        field_name='region',
        help_text="Filter by region"
    )

    region_name = django_filters.CharFilter(
        field_name='region__name',
        lookup_expr='icontains',
        help_text="Search by region name"
    )

    class Meta:
        model = Districts
        fields = ['name', 'region']