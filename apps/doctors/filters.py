import django_filters
from django.db.models import Q
from .models import Doctor


class DoctorFilter(django_filters.FilterSet):
    """Doctor filtering for API endpoints"""

    # Basic filters
    specialty = django_filters.ChoiceFilter(
        field_name='specialty',
        choices=Doctor.SPECIALTIES if hasattr(Doctor, 'SPECIALTIES') else [],
        help_text="Mutaxassislik bo'yicha filtr"
    )

    verification_status = django_filters.ChoiceFilter(
        field_name='verification_status',
        choices=Doctor.VERIFICATION_STATUS if hasattr(Doctor, 'VERIFICATION_STATUS') else [
            ('pending', 'Kutilayotgan'),
            ('approved', 'Tasdiqlangan'),
            ('rejected', 'Rad etilgan'),
        ],
        help_text="Tasdiqlash holati"
    )

    is_available = django_filters.BooleanFilter(
        field_name='is_available',
        help_text="Mavjudlik holati"
    )

    is_online_consultation = django_filters.BooleanFilter(
        field_name='is_online_consultation',
        help_text="Onlayn konsultatsiya"
    )

    # Location filters
    region = django_filters.CharFilter(
        field_name='region',
        lookup_expr='icontains',
        help_text="Viloyat bo'yicha qidiruv"
    )

    district = django_filters.CharFilter(
        field_name='district',
        lookup_expr='icontains',
        help_text="Tuman bo'yicha qidiruv"
    )

    # Experience filters
    min_experience = django_filters.NumberFilter(
        field_name='experience',
        lookup_expr='gte',
        help_text="Minimal tajriba (yil)"
    )

    max_experience = django_filters.NumberFilter(
        field_name='experience',
        lookup_expr='lte',
        help_text="Maksimal tajriba (yil)"
    )

    # Price filters
    min_price = django_filters.NumberFilter(
        field_name='consultation_price',
        lookup_expr='gte',
        help_text="Minimal narx"
    )

    max_price = django_filters.NumberFilter(
        field_name='consultation_price',
        lookup_expr='lte',
        help_text="Maksimal narx"
    )

    # Rating filters
    min_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte',
        help_text="Minimal reyting"
    )

    # Search filters
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="Ism, familya, mutaxassislik bo'yicha qidiruv"
    )

    name = django_filters.CharFilter(
        method='filter_name',
        help_text="Ism va familya bo'yicha qidiruv"
    )

    # Hospital filter
    hospital = django_filters.NumberFilter(
        field_name='hospital__id',
        help_text="Shifoxona ID si"
    )

    hospital_name = django_filters.CharFilter(
        field_name='hospital__name',
        lookup_expr='icontains',
        help_text="Shifoxona nomi"
    )

    # Languages filter
    languages = django_filters.CharFilter(
        field_name='languages',
        lookup_expr='icontains',
        help_text="Tillar"
    )

    # Work time filters
    available_now = django_filters.BooleanFilter(
        method='filter_available_now',
        help_text="Hozir ishlayotgan shifokorlar"
    )

    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Shu sanadan keyin ro'yxatdan o'tgan"
    )

    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Shu sanadan oldin ro'yxatdan o'tgan"
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
        """Umumiy qidiruv - ism, familya, mutaxassislik"""
        if value:
            return queryset.filter(
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value) |
                Q(specialty__icontains=value) |
                Q(workplace__icontains=value) |
                Q(bio__icontains=value)
            )
        return queryset

    def filter_name(self, queryset, name, value):
        """Ism va familya bo'yicha qidiruv"""
        if value:
            return queryset.filter(
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value)
            )
        return queryset

    def filter_available_now(self, queryset, name, value):
        """Hozir ishlayotgan shifokorlarni filtrini"""
        if value:
            from datetime import datetime
            current_time = datetime.now().time()
            current_weekday = datetime.now().weekday()

            return queryset.filter(
                is_available=True,
                verification_status='approved',
                work_start_time__lte=current_time,
                work_end_time__gte=current_time,
                work_days__contains=str(current_weekday)
            )
        return queryset


class DoctorAdminFilter(DoctorFilter):
    """Admin panel uchun kengaytirilgan filtrlar"""

    # Admin specific filters
    user_type = django_filters.ChoiceFilter(
        field_name='user__user_type',
        choices=[
            ('doctor', 'Shifokor'),
            ('patient', 'Bemor'),
            ('admin', 'Admin'),
            ('hospital_admin', 'Shifoxona admin'),
        ],
        help_text="Foydalanuvchi turi"
    )

    is_active = django_filters.BooleanFilter(
        field_name='user__is_active',
        help_text="Faol foydalanuvchi"
    )

    is_verified = django_filters.BooleanFilter(
        field_name='user__is_verified',
        help_text="Tasdiqlangan telefon"
    )

    is_approved_by_admin = django_filters.BooleanFilter(
        field_name='user__is_approved_by_admin',
        help_text="Admin tomonidan tasdiqlangan"
    )

    # Statistics filters
    min_total_reviews = django_filters.NumberFilter(
        field_name='total_reviews',
        lookup_expr='gte',
        help_text="Minimal sharhlar soni"
    )

    min_total_consultations = django_filters.NumberFilter(
        field_name='total_consultations',
        lookup_expr='gte',
        help_text="Minimal konsultatsiyalar soni"
    )

    min_profile_views = django_filters.NumberFilter(
        field_name='profile_views',
        lookup_expr='gte',
        help_text="Minimal profil ko'rishlar soni"
    )

    class Meta(DoctorFilter.Meta):
        fields = DoctorFilter.Meta.fields + [
            'user_type', 'is_active', 'is_verified',
            'is_approved_by_admin', 'min_total_reviews',
            'min_total_consultations', 'min_profile_views'
        ]