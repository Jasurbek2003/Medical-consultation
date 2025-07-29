from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Hospital


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'hospital_type',
        'region',
        'district',
        'phone',
        'email',
        'is_active',
        'doctor_count',
        'created_at'
    ]

    list_filter = [
        'hospital_type',
        'is_active',
        'region',
        'district',
        'created_at'
    ]

    search_fields = [
        'name',
        'short_name',
        'email',
        'phone',
        'address',
        'description'
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'doctor_count',
        'logo_preview',
        'total_doctors',
        'total_patients'
    ]

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': (
                'name',
                'short_name',
                'hospital_type',
                'description',
                'logo',
                'logo_preview'
            )
        }),
        ('Joylashuv ma\'lumotlari', {
            'fields': (
                'region',
                'district',
                'address',
                # 'latitude',
                # 'longitude'
            )
        }),
        ('Aloqa ma\'lumotlari', {
            'fields': (
                'phone',
                'email',
                'website',
                # 'social_media'
            )
        }),
        ('Xizmatlar va ish vaqti', {
            'fields': (
                'services',
                'working_hours',
                # 'emergency_services'
            )
        }),
        ('Holat', {
            'fields': (
                'is_active',
                # 'is_featured'
            )
        }),
        ('Statistika', {
            'fields': (
                'total_doctors',
                'total_patients',
                'rating',
                # 'total_reviews'
            ),
            'classes': ('collapse',)
        }),
        ('Tizim ma\'lumotlari', {
            'fields': (
                'id',
                'created_at',
                'updated_at',
                'doctor_count'
            ),
            'classes': ('collapse',)
        })
    )

    list_per_page = 25
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def doctor_count(self, obj):
        """Display number of doctors in hospital"""
        from apps.doctors.models import Doctor
        count = Doctor.objects.filter(hospital=obj).count()
        if count > 0:
            url = reverse('admin:doctors_doctor_changelist') + f'?hospital__id__exact={obj.id}'
            return format_html('<a href="{}">{} ta</a>', url, count)
        return '0 ta'

    doctor_count.short_description = 'Shifokorlar soni'

    def logo_preview(self, obj):
        """Display logo preview"""
        if obj.logo:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 8px;" />',
                obj.logo.url
            )
        return 'Logo mavjud emas'

    logo_preview.short_description = 'Logo ko\'rinishi'

    def get_queryset(self, request):
        """Optimize queryset"""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('departments')

    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        super().save_model(request, obj, form, change)

        # Update statistics after saving
        if hasattr(obj, 'update_statistics'):
            obj.update_statistics()

    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)

        # Hospital admins can only edit their own hospital
        if hasattr(request.user, 'is_hospital_admin') and request.user.is_hospital_admin():
            if obj and obj != request.user.managed_hospital:
                # Make all fields readonly for other hospitals
                for field_name in form.base_fields:
                    form.base_fields[field_name].disabled = True

        return form

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete hospitals"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Hospital admins can only edit their own hospital"""
        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'is_hospital_admin') and request.user.is_hospital_admin():
            if obj:
                return obj == request.user.managed_hospital
            return False

        return False

    def has_view_permission(self, request, obj=None):
        """Hospital admins can only view their own hospital"""
        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'is_hospital_admin') and request.user.is_hospital_admin():
            if obj:
                return obj == request.user.managed_hospital
            return True

        return False

    # Custom actions
    actions = ['activate_hospitals', 'deactivate_hospitals']

    def activate_hospitals(self, request, queryset):
        """Activate selected hospitals"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} ta shifoxona faollashtirildi.'
        )

    activate_hospitals.short_description = 'Tanlangan shifoxonalarni faollashtirish'

    def deactivate_hospitals(self, request, queryset):
        """Deactivate selected hospitals"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} ta shifoxona faoliyatdan chiqarildi.'
        )

    deactivate_hospitals.short_description = 'Tanlangan shifoxonalarni faoliyatdan chiqarish'

    # def feature_hospitals(self, request, queryset):
    #     """Feature selected hospitals"""
    #     updated = queryset.update(is_featured=True)
    #     self.message_user(
    #         request,
    #         f'{updated} ta shifoxona ajratildi.'
    #     )
    #
    # feature_hospitals.short_description = 'Tanlangan shifoxonalarni ajratish'

