from django.contrib import admin
from .models import Doctor, DoctorSchedule, DoctorSpecialization


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'get_full_name', 'specialty', 'experience', 'rating',
        'consultation_price', 'is_available', 'region'
    ]
    list_filter = [
        'specialty', 'degree', 'is_available', 'region',
        'is_online_consultation', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'phone', 'email',
        'license_number', 'workplace'
    ]
    readonly_fields = ['created_at', 'updated_at', 'rating', 'total_reviews']

    fieldsets = (
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('first_name', 'last_name', 'middle_name', 'photo')
        }),
        ('Professional ma\'lumotlar', {
            'fields': (
                'specialty', 'degree', 'experience', 'license_number',
                'education', 'achievements', 'bio'
            )
        }),
        ('Kontakt', {
            'fields': ('phone', 'email', 'languages')
        }),
        ('Manzil', {
            'fields': ('region', 'district', 'address', 'workplace', 'workplace_address')
        }),
        ('Ish ma\'lumotlari', {
            'fields': (
                'consultation_price', 'is_available', 'is_online_consultation',
                'work_start_time', 'work_end_time', 'work_days'
            )
        }),
        ('Statistika', {
            'fields': ('rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = 'F.I.Sh'

    actions = ['make_available', 'make_unavailable']

    def make_available(self, request, queryset):
        queryset.update(is_available=True)
        self.message_user(request, f"{queryset.count()} ta shifokor mavjud qilindi.")

    make_available.short_description = "Tanlangan shifokorlarni mavjud qilish"

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)
        self.message_user(request, f"{queryset.count()} ta shifokor mavjud emas qilindi.")

    make_unavailable.short_description = "Tanlangan shifokorlarni mavjud emas qilish"


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'get_weekday_display', 'start_time', 'end_time', 'is_available']
    list_filter = ['weekday', 'is_available']
    search_fields = ['doctor__first_name', 'doctor__last_name']


@admin.register(DoctorSpecialization)
class DoctorSpecializationAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'name', 'description']
    search_fields = ['doctor__first_name', 'doctor__last_name', 'name']

