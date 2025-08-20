from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserMedicalHistory, UserPreferences


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'get_full_name', 'phone', 'email', 'is_active',
        'is_profile_complete', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'gender',
        'blood_type', 'is_profile_complete', 'created_at'
    ]
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'username']
    readonly_fields = ['created_at', 'updated_at', 'last_login_ip', 'is_profile_complete']

    fieldsets = (
        ('Kirish ma\'lumotlari', {
            'fields': ('username', 'password', 'phone')
        }),
        ('Shaxsiy ma\'lumotlar', {
            'fields': (
                'first_name', 'last_name', 'email', 'birth_date',
                'gender', 'avatar', 'language'
            )
        }),
        ('Tibbiy ma\'lumotlar', {
            'fields': (
                'blood_type', 'height', 'weight', 'allergies',
                'chronic_diseases', 'current_medications'
            ),
            'classes': ('collapse',)
        }),
        ('Favqulodda aloqa', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relation'
            ),
            'classes': ('collapse',)
        }),
        ('Manzil', {
            'fields': ('region', 'district', 'address'),
            'classes': ('collapse',)
        }),
        ('Sozlamalar', {
            'fields': (
                'notifications_enabled', 'email_notifications',
                'sms_notifications'
            ),
            'classes': ('collapse',)
        }),
        ('Ruxsatlar', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', "user_type"),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at', 'last_login', 'last_login_ip', 'is_profile_complete',
                       "is_approved_by_admin", ),
            'classes': ('collapse',)
        })
    )

    add_fieldsets = (
        ('Yangi foydalanuvchi', {
            'classes': ('wide',),
            'fields': ('username', 'phone', 'password1', 'password2'),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone

    get_full_name.short_description = 'F.I.Sh'


@admin.register(UserMedicalHistory)
class UserMedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'record_type', 'title', 'date_recorded', 'is_active']
    list_filter = ['record_type', 'date_recorded', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'title', 'doctor_name']
    date_hierarchy = 'date_recorded'


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_language', 'preferred_doctor_gender', 'max_consultation_price']
    list_filter = ['preferred_language', 'preferred_doctor_gender', 'preferred_consultation_time']
