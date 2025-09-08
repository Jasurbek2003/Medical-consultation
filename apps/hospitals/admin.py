from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Hospital, HospitalService, HospitalTranslation, Regions, Districts
from ..doctors.services.translation_service import HospitalTranslationService, DefaultTranslationService


class HospitalTranslationInline(admin.StackedInline):
    model = HospitalTranslation
    extra = 0
    readonly_fields = ['created_at', 'updated_at', 'get_translation_summary']
    fields = ['get_translation_summary', 'created_at', 'updated_at']

    def get_translation_summary(self, obj):
        if not obj.translations:
            return format_html(
                '<p style="color: #6c757d;">No translations yet. Use the "Translate Profile" action to generate translations.</p>')

        summary_html = '<div style="background: #f8f9fa; padding: 10px; border-radius: 6px; margin-bottom: 10px;">'
        summary_html += '<h4 style="margin-top: 0; color: #495057;">🌐 Translation Summary</h4>'

        for field_name, lang_translations in obj.translations.items():
            lang_count = len([text for text in lang_translations.values() if text.strip()])
            total_langs = len(lang_translations)

            status_color = '#28a745' if lang_count == total_langs else '#ffc107' if lang_count > 0 else '#dc3545'
            summary_html += f'<p style="margin: 5px 0;"><strong>{field_name.title()}:</strong> <span style="color: {status_color};">{lang_count}/{total_langs} languages</span></p>'

        summary_html += '</div>'
        return format_html(summary_html)

    get_translation_summary.short_description = '📊 Summary'







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
                'founded_year'
                # 'social_media'
            )
        }),
        ('Xizmatlar va ish vaqti', {
            'fields': (
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

    inlines = [HospitalTranslationInline]

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
    actions = ['activate_hospitals', 'deactivate_hospitals', 'translate_selected_hospitals']

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

    def translate_selected_hospitals(self, request, queryset):
        """Translate selected hospitals"""
        translation_service = HospitalTranslationService()
        success_count = 0
        for hospital in queryset:
            # try:
                translations = translation_service.translate_hospital_profile(hospital)
                print(translations)

                translation_service.save_hospital_translations(hospital, translations)
                success_count += 1
            # except Exception as e:
            #     self.message_user(
            #         request,
            #         f'Xatolik yuz berdi {hospital.name} shifoxonasini tarjima qilishda: {str(e)}',
            #         level='error'
            #     )
    translate_selected_hospitals.short_description = 'Tanlangan shifoxonalarni tarjima qilish'



@admin.register(HospitalService)
class HospitalServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'hospital',
        'description',
        'is_active',
        'created_at'
    ]

    list_filter = [
        'hospital',
        'is_active',
        'created_at'
    ]

    search_fields = [
        'name',
        'description'
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': (
                'name',
                'hospital',
                'description'
            )
        }),
        ('Holat', {
            'fields': (
                'is_active',
            )
        }),
        ('Tizim ma\'lumotlari', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    list_per_page = 25
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        """Optimize queryset"""
        queryset = super().get_queryset(request)
        return queryset.select_related('hospital')


@admin.register(Regions)
class RegionsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name_en', 'name_ru', 'name_kr']
    search_fields = ['name']
    readonly_fields = ['id']
    ordering = ['name']
    list_per_page = 50

    actions = ['translate_selected_regions']

    def translate_selected_regions(self, request, queryset):
        """Translate selected regions"""
        translation_service = DefaultTranslationService()
        success_count = 0
        for region in queryset:
            try:
                translations = translation_service.translate_to_all_languages(region.name)
                region.name =translations.get('uzn_Latn', region.name)
                region.name_en = translations.get('eng_Latn', '')
                region.name_ru = translations.get('rus_Cyrl', '')
                region.name_kr = translations.get('uzn_Cyrl', '')
                region.save()
                success_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Xatolik yuz berdi {region.name} hududini tarjima qilishda: {str(e)}',
                    level='error'
                )
        self.message_user(
            request,
            f'{success_count} ta hudud muvaffaqiyatli tarjima qilindi.'
        )

    translate_selected_regions.short_description = 'Tanlangan hududlarni tarjima qilish'

@admin.register(Districts)
class DistrictsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'region', 'name_en', 'name_ru', 'name_kr']
    search_fields = ['name', 'region__name']
    readonly_fields = ['id']
    ordering = ['region__name', 'name']
    list_filter = ['region']
    list_per_page = 50

    actions = ['translate_selected_districts']

    def translate_selected_districts(self, request, queryset):
        """Translate selected districts"""
        translation_service = DefaultTranslationService()
        success_count = 0
        for district in queryset:
            try:
                translations = translation_service.translate_to_all_languages(district.name)
                district.name =translations.get('uzn_Latn', district.name)
                district.name_en = translations.get('eng_Latn', '')
                district.name_ru = translations.get('rus_Cyrl', '')
                district.name_kr = translations.get('uzn_Cyrl', '')
                district.save()
                success_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Xatolik yuz berdi {district.name} tumani tarjima qilishda: {str(e)}',
                    level='error'
                )
        self.message_user(
            request,
            f'{success_count} ta tuman muvaffaqiyatli tarjima qilindi.'
        )

    translate_selected_districts.short_description = 'Tanlangan tumanlarni tarjima qilish'