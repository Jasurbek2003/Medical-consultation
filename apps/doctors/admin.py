from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.utils.html import format_html

from .models import Doctor, DoctorSchedule, DoctorSpecialization, DoctorTranslation
from .services.translation_service import DoctorTranslationService


class DoctorTranslationInline(admin.StackedInline):
    model = DoctorTranslation
    extra = 0
    readonly_fields = ['created_at',  'get_translation_summary']
    fields = ['get_translation_summary', 'translations', 'created_at']

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

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'get_photo_thumbnail', 'get_full_name_with_emoji', 'specialty_badge', 'rating_stars',
        'experience_years', 'consultation_price_formatted',
        'availability_status', 'total_reviews', 'region_info'
    ]
    list_filter = [
        'specialty', 'degree', 'is_available', 'verification_status',
        # 'is_online_consultation', 'created_at', 'user__region'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__phone', 'user__email',
        'license_number', 'workplace'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'rating', 'total_reviews', 'get_diploma_preview',
        'total_consultations', 'profile_views', 'weekly_views', 'monthly_views'
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'
    autocomplete_fields = ['user']

    inlines = [DoctorTranslationInline]

    fieldsets = (
        ('👤 Foydalanuvchi Ma\'lumotlari', {
            'fields': ('user', 'get_diploma_preview'),
            'classes': ('wide',),
            'description': 'Shifokorga biriktirilgan foydalanuvchi'
        }),
        ('📷 Hujjatlar', {
            'fields': ('diploma_image', 'license_image'),
            'classes': ('wide',)
        }),
        ('🏥 Professional Ma\'lumotlar', {
            'fields': (
                'specialty', 'degree', 'experience', 'license_number',
                'education', 'achievements', 'bio', 'verification_status'
            ),
            'classes': ('wide',),
            'description': 'Professional malaka va tajriba'
        }),
        ('🏥 Ish Joyi', {
            'fields': ('hospital', 'workplace', 'workplace_address'),
            'classes': ('wide',)
        }),
        ('💼 Ish va Narx', {
            'fields': (
                'consultation_price', 'is_available', 'is_online_consultation',
                'work_start_time', 'work_end_time', 'work_days'
            ),
            'classes': ('wide',)
        }),
        ('📊 Statistika', {
            'fields': ('rating', 'total_reviews', 'total_consultations',
                       'profile_views', 'weekly_views', 'monthly_views'),
            'classes': ('collapse',),
            'description': 'Avtomatik hisoblanadigan statistika'
        }),
        ('📅 Vaqt', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['make_available', 'make_unavailable', 'approve_doctors', 'reject_doctors', 'send_notification',
               'translate_selected_doctors']

    def translate_selected_doctors(self, request, queryset):
        """Translate selected doctors"""
        translation_service = DoctorTranslationService()
        success_count = 0

        for doctor in queryset:
            try:
                translations = translation_service.translate_doctor_profile(doctor)
                translation_service.save_doctor_translations(doctor, translations)
                success_count += 1
            except Exception:
                pass

        messages.success(request, f'✅ Translated {success_count} doctors')

    translate_selected_doctors.short_description = '🌐 Translate selected doctors'

    def get_photo_thumbnail(self, obj):
        if obj.user.avatar:
            return format_html(
                '<img src="{}" style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover; border: 3px solid #667eea;">',
                obj.user.avatar.url
            )
        else:
            initials = f"{obj.user.first_name[0] if obj.user.first_name else ''}{obj.user.last_name[0] if obj.user.last_name else ''}"
            return format_html(
                '<div style="width: 45px; height: 45px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 16px;">{}</div>',
                initials.upper()
            )

    get_photo_thumbnail.short_description = '📷'

    def get_full_name_with_emoji(self, obj):
        full_name = obj.user.get_full_name()
        phone = obj.user.phone
        gender_emoji = '👨‍⚕️' if obj.user.gender == 'M' else '👩‍⚕️'

        return format_html(
            '<div>'
            '<strong style="color: #333; font-size: 14px;">{} {}</strong>'
            '<br><small style="color: #666;">📱 {}</small>'
            '</div>',
            gender_emoji, full_name, phone
        )

    get_full_name_with_emoji.short_description = '👨‍⚕️ F.I.O'

    def get_diploma_preview(self, obj):
        if obj.diploma_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 200px; max-height: 150px; border: 2px solid #ddd; border-radius: 8px;">'
                '</a>',
                obj.diploma_image.url,
                obj.diploma_image.url
            )
        return '❌ Diplom yuklanmagan'

    get_diploma_preview.short_description = '📜 Diplom'

    def specialty_badge(self, obj):
        specialty_colors = {
            'terapevt': '#007bff',
            'stomatolog': '#28a745',
            'kardiolog': '#dc3545',
            'urolog': '#ffc107',
            'ginekolog': '#e83e8c',
            'pediatr': '#20c997',
            'dermatolog': '#6f42c1',
            'nevrolog': '#fd7e14',
            'oftalmolog': '#17a2b8',
            'lor': '#6610f2',
            'ortoped': '#495057',
            'psixiatr': '#6c757d',
            'endokrinolog': '#343a40',
            'gastroenterolog': '#007bff',
            'pulmonolog': '#28a745',
        }

        color = specialty_colors.get(obj.specialty, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 6px 14px; border-radius: 15px; font-size: 12px; font-weight: 600; display: inline-block; white-space: nowrap;">{}</span>',
            color, obj.get_specialty_display()
        )

    specialty_badge.short_description = '🩺 Mutaxassis'

    def experience_years(self, obj):
        if obj.experience >= 20:
            badge_color = '#dc3545'
            badge_text = 'Expert'
        elif obj.experience >= 10:
            badge_color = '#28a745'
            badge_text = 'Senior'
        elif obj.experience >= 5:
            badge_color = '#ffc107'
            badge_text = 'Mid'
        else:
            badge_color = '#17a2b8'
            badge_text = 'Junior'

        return format_html(
            '<div style="text-align: center;">'
            '<div style="background: {}; color: white; padding: 4px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-bottom: 2px;">{}</div>'
            '<div style="font-weight: 600; color: #333; font-size: 13px;">{} yil</div>'
            '</div>',
            badge_color, badge_text, obj.experience
        )

    experience_years.short_description = '📅 Tajriba'

    def consultation_price_formatted(self, obj):
        if obj.consultation_price:
            return format_html(
                '<div style="text-align: center; background: #f8f9fa; padding: 8px; border-radius: 10px; border-left: 4px solid #28a745;">'
                '<span style="color: #28a745; font-weight: 600; font-size: 14px;">💰 {} so\'m</span>'
                '</div>',
                int(obj.consultation_price)
            )
        return format_html('<span style="color: #6c757d;">💰 Belgilanmagan</span>')

    consultation_price_formatted.short_description = '💰 Narx'

    def rating_stars(self, obj):
        if obj.rating:
            full_stars = int(obj.rating)
            half_star = 1 if obj.rating - full_stars >= 0.5 else 0
            empty_stars = 5 - full_stars - half_star

            stars_html = '⭐' * full_stars
            if half_star:
                stars_html += '⭐'
            stars_html += '☆' * empty_stars

            return format_html(
                '<div style="text-align: center;">'
                '<div style="font-size: 16px; line-height: 1;">{}</div>'
                '<small style="color: #666; font-weight: 600;">{:.1f}/5</small>'
                '</div>',
                stars_html, obj.rating
            )
        return format_html('<span style="color: #6c757d;">☆☆☆☆☆</span>')

    rating_stars.short_description = '⭐ Reyting'

    def availability_status(self, obj):
        if obj.is_available:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 6px 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
                '🟢 Mavjud</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 6px 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
            '🔴 Band</span>'
        )

    availability_status.short_description = '🟢 Holat'

    def region_info(self, obj):
        if obj.user.region:
            return format_html(
                '<div style="text-align: center; background: #e3f2fd; padding: 6px 10px; border-radius: 8px; border-left: 3px solid #2196f3;">'
                '<small style="color: #1565c0; font-weight: 600;">📍 {}</small>'
                '</div>',
                obj.user.region
            )
        return format_html('<span style="color: #6c757d;">📍 Noma\'lum</span>')

    region_info.short_description = '📍 Hudud'

    def make_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(
            request,
            format_html('✅ <strong>{}</strong> ta shifokor mavjud qilindi.', updated),
            level='SUCCESS'
        )

    make_available.short_description = "✅ Mavjud qilish"

    def make_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(
            request,
            format_html('❌ <strong>{}</strong> ta shifokor band qilindi.', updated),
            level='INFO'
        )

    make_unavailable.short_description = "❌ Band qilish"

    def approve_doctors(self, request, queryset):
        updated = queryset.update(verification_status='approved')
        self.message_user(
            request,
            format_html('✅ <strong>{}</strong> ta shifokor tasdiqlandi.', updated),
            level='SUCCESS'
        )

    approve_doctors.short_description = "✅ Shifokorlarni tasdiqlash"

    def reject_doctors(self, request, queryset):
        updated = queryset.update(verification_status='rejected')
        self.message_user(
            request,
            format_html('❌ <strong>{}</strong> ta shifokor rad etildi.', updated),
            level='WARNING'
        )

    reject_doctors.short_description = "❌ Shifokorlarni rad etish"

    def send_notification(self, request, queryset):
        count = queryset.count()
        self.message_user(
            request,
            format_html('📧 <strong>{}</strong> ta shifokorga bildirishnoma yuborildi.', count),
            level='INFO'
        )

    send_notification.short_description = "📧 Bildirishnoma yuborish"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'hospital').prefetch_related('specializations', 'schedules')


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor_info', 'weekday_badge', 'time_range', 'availability_status']
    list_filter = ['weekday', 'is_available', 'doctor__specialty']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name', 'doctor__license_number']
    list_per_page = 20
    autocomplete_fields = ['doctor']

    fieldsets = (
        ('👨‍⚕️ Shifokor', {
            'fields': ('doctor',),
        }),
        ('📅 Vaqt Jadvali', {
            'fields': ('weekday', 'start_time', 'end_time', 'is_available'),
            'classes': ('wide',)
        }),
    )

    def doctor_info(self, obj):
        # Fixed: Removed f-string from inside format_html
        doctor_name = "Dr. {} {}".format(obj.doctor.user.first_name, obj.doctor.user.last_name)
        specialty = obj.doctor.get_specialty_display()

        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px;">👨‍⚕️</div>'
            '<div>'
            '<strong style="color: #333;">{}</strong>'
            '<br><small style="color: #666;">{}</small>'
            '</div>'
            '</div>',
            doctor_name,
            specialty
        )

    doctor_info.short_description = '👨‍⚕️ Shifokor'

    def weekday_badge(self, obj):
        weekday_colors = {
            1: '#007bff',  # Dushanba
            2: '#28a745',  # Seshanba
            3: '#ffc107',  # Chorshanba
            4: '#17a2b8',  # Payshanba
            5: '#6f42c1',  # Juma
            6: '#fd7e14',  # Shanba
            7: '#dc3545',  # Yakshanba
        }

        weekday_emojis = {
            1: '📅', 2: '📅', 3: '📅', 4: '📅', 5: '🕌', 6: '🎯', 7: '🏠'
        }

        color = weekday_colors.get(obj.weekday, '#6c757d')
        emoji = weekday_emojis.get(obj.weekday, '📅')

        return format_html(
            '<span style="background: {}; color: white; padding: 6px 12px; border-radius: 15px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
            '{} {}</span>',
            color, emoji, obj.get_weekday_display()
        )

    weekday_badge.short_description = '📅 Kun'

    def time_range(self, obj):
        start_time = obj.start_time.strftime('%H:%M')
        end_time = obj.end_time.strftime('%H:%M')

        return format_html(
            '<div style="text-align: center; background: #f8f9fa; padding: 8px 12px; border-radius: 10px; border: 2px solid #e9ecef;">'
            '<span style="color: #667eea; font-weight: 600; font-size: 13px;">🕐 {} - {}</span>'
            '</div>',
            start_time,
            end_time
        )

    time_range.short_description = '🕐 Vaqt'

    def availability_status(self, obj):
        if obj.is_available:
            return format_html('<span style="color: #28a745; font-weight: 600;">✅ Mavjud</span>')
        return format_html('<span style="color: #dc3545; font-weight: 600;">❌ Band</span>')

    availability_status.short_description = '🟢 Holat'


@admin.register(DoctorSpecialization)
class DoctorSpecializationAdmin(admin.ModelAdmin):
    list_display = ['doctor_name', 'specialization_name', 'has_certificate', 'certificate_info']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name', 'name']
    list_filter = ['doctor__specialty']
    autocomplete_fields = ['doctor']

    fieldsets = (
        ('👨‍⚕️ Shifokor', {
            'fields': ('doctor',),
        }),
        ('🎓 Mutaxassislik', {
            'fields': ('name', 'description'),
            'classes': ('wide',)
        }),
        ('📜 Sertifikat', {
            'fields': ('certificate',),
            'classes': ('wide',)
        }),
    )

    def doctor_name(self, obj):
        doctor_name = "Dr. {} {}".format(obj.doctor.user.first_name, obj.doctor.user.last_name)
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<span style="font-size: 18px;">👨‍⚕️</span>'
            '<strong>{}</strong>'
            '</div>',
            doctor_name
        )

    doctor_name.short_description = '👨‍⚕️ Shifokor'

    def specialization_name(self, obj):
        return format_html(
            '<span style="background: #007bff; color: white; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;">'
            '🎓 {}</span>',
            obj.name
        )

    specialization_name.short_description = '🎓 Mutaxassislik'

    def has_certificate(self, obj):
        if obj.certificate:
            return format_html('<span style="color: #28a745; font-weight: 600;">✅ Bor</span>')
        return format_html('<span style="color: #dc3545; font-weight: 600;">❌ Yo\'q</span>')

    has_certificate.short_description = '📜 Sertifikat'

    def certificate_info(self, obj):
        if obj.certificate:
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff; text-decoration: none;">'
                '📄 Sertifikatni ko\'rish</a>',
                obj.certificate.url
            )
        return format_html('<span style="color: #6c757d;">📄 Mavjud emas</span>')

    certificate_info.short_description = '📄 Fayl'


# Register DoctorTranslation separately
@admin.register(DoctorTranslation)
class DoctorTranslationAdmin(admin.ModelAdmin):
    list_display = [
        'get_doctor_info', 'get_translation_status', 'get_supported_languages',
        'last_updated', 'get_translation_actions'
    ]
    list_filter = ['doctor__specialty', 'doctor__verification_status']
    search_fields = [
        'doctor__user__first_name', 'doctor__user__last_name',
        'doctor__license_number'
    ]
    readonly_fields = [
        'doctor', 'created_at', 'get_translation_preview'
    ]

    fieldsets = (
        ('👨‍⚕️ Doctor Information', {
            'fields': ('doctor', 'get_translation_preview'),
            'classes': ('wide',)
        }),
        ('🌐 Translation Data', {
            'fields': ('translations',),
            'classes': ('wide', 'collapse'),
            'description': 'Raw translation JSON data'
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_doctor_info(self, obj):
        doctor = obj.doctor
        photo_html = ''

        if doctor.user.avatar:
            photo_html = f'<img src="{doctor.user.avatar.url}" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">'
        else:
            initials = f"{doctor.user.first_name[0] if doctor.user.first_name else ''}{doctor.user.last_name[0] if doctor.user.last_name else ''}"
            photo_html = f'<div style="width: 40px; height: 40px; border-radius: 50%; background: #667eea; color: white; display: inline-flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;">{initials.upper()}</div>'

        return format_html(
            '<div style="display: flex; align-items: center;">'
            '{}'
            '<div>'
            '<strong>Dr. {} {}</strong>'
            '<br><small style="color: #666;">📱 {} | 🩺 {}</small>'
            '</div>'
            '</div>',
            photo_html,
            doctor.user.first_name,
            doctor.user.last_name,
            doctor.user.phone,
            doctor.get_specialty_display()
        )

    get_doctor_info.short_description = '👨‍⚕️ Doctor'

    def get_translation_status(self, obj):
        total_fields = len(obj.translations) if obj.translations else 0

        if total_fields == 0:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '❌ No Translations</span>'
            )

        # Count fields with actual translations
        translated_fields = 0
        for field_name, lang_translations in obj.translations.items():
            if any(text.strip() for text in lang_translations.values()):
                translated_fields += 1

        if translated_fields == total_fields:
            status_html = '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">✅ Complete</span>'
        elif translated_fields > 0:
            status_html = '<span style="background: #ffc107; color: black; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">⚠️ Partial</span>'
        else:
            status_html = '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">❌ Empty</span>'

        return format_html(
            '{}<br><small style="color: #666;">{}/{} fields</small>',
            status_html, translated_fields, total_fields
        )

    get_translation_status.short_description = '📊 Status'

    def get_supported_languages(self, obj):
        if not obj.translations:
            return format_html('<span style="color: #6c757d;">None</span>')

        languages = set()
        for field_translations in obj.translations.values():
            languages.update(field_translations.keys())

        language_badges = []
        language_names = {
            'uzn_Latn': '🇺🇿 UZ',
            'rus_Cyrl': '🇷🇺 RU',
            'eng_Latn': '🇬🇧 EN',
            'uzn_Cyrl': '🇺🇿 УЗ'
        }

        for lang in sorted(languages):
            display_name = language_names.get(lang, lang)
            language_badges.append(
                f'<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px; margin: 1px;">{display_name}</span>'
            )

        return format_html(''.join(language_badges))

    get_supported_languages.short_description = '🌐 Languages'

    def last_updated(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<strong style="color: #333;">{}</strong>'
            '<br><small style="color: #666;">{}</small>'
            '</div>',
            obj.updated_at.strftime('%Y-%m-%d'),
            obj.updated_at.strftime('%H:%M')
        )

    last_updated.short_description = '📅 Updated'

    def get_translation_actions(self, obj):
        doctor_id = obj.doctor.id
        translate_url = reverse('admin:translate_doctor_profile', args=[doctor_id])
        refresh_url = reverse('admin:refresh_doctor_translation', args=[doctor_id])

        return format_html(
            '<div style="display: flex; gap: 5px; flex-direction: column;">'
            '<a href="{}" style="background: #28a745; color: white; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 11px; text-align: center;">🔄 Retranslate</a>'
            '<a href="{}" style="background: #17a2b8; color: white; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 11px; text-align: center;">🔄 Refresh</a>'
            '</div>',
            translate_url, refresh_url
        )

    get_translation_actions.short_description = '⚡ Actions'

    def get_translation_preview(self, obj):
        if not obj.translations:
            return format_html('<p style="color: #6c757d;">No translations available</p>')

        preview_html = '<div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f8f9fa;">'

        for field_name, lang_translations in obj.translations.items():
            preview_html += f'<h4 style="color: #495057; margin-top: 15px; margin-bottom: 8px;">📝 {field_name.title()}</h4>'

            for lang_code, text in lang_translations.items():
                lang_names = {
                    'uzn_Latn': '🇺🇿 Uzbek (Latin)',
                    'rus_Cyrl': '🇷🇺 Russian',
                    'eng_Latn': '🇬🇧 English',
                    'uzn_Cyrl': '🇺🇿 Uzbek (Cyrillic)'
                }
                lang_display = lang_names.get(lang_code, lang_code)

                text_preview = (text[:100] + '...') if len(text) > 100 else text
                preview_html += f'<p style="margin: 5px 0; padding: 8px; background: white; border-left: 3px solid #007bff; border-radius: 4px;"><strong>{lang_display}:</strong><br>{text_preview}</p>'

        preview_html += '</div>'
        return format_html(preview_html)

    get_translation_preview.short_description = '👁️ Preview'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'translate-doctor/<uuid:doctor_id>/',
                self.admin_site.admin_view(self.translate_doctor_view),
                name='translate_doctor_profile'
            ),
            path(
                'refresh-translation/<uuid:doctor_id>/',
                self.admin_site.admin_view(self.refresh_translation_view),
                name='refresh_doctor_translation'
            ),
        ]
        return custom_urls + urls

    def translate_doctor_view(self, request, doctor_id):
        """Admin action to translate a specific doctor"""
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            translation_service = DoctorTranslationService()

            # Translate doctor profile
            translations = translation_service.translate_doctor_profile(doctor)

            # Save translations
            translation_service.save_doctor_translations(doctor, translations)

            messages.success(
                request,
                f'✅ Successfully translated profile for Dr. {doctor.user.get_full_name()}'
            )

        except Doctor.DoesNotExist:
            messages.error(request, '❌ Doctor not found')
        except Exception as e:
            messages.error(request, f'❌ Translation failed: {str(e)}')

        return HttpResponseRedirect(reverse('admin:doctors_doctortranslation_changelist'))

    def refresh_translation_view(self, request, doctor_id):
        """Admin action to refresh/update existing translation"""
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            translation_service = DoctorTranslationService()

            # Get fresh translations
            translations = translation_service.translate_doctor_profile(doctor)

            # Update existing translation object
            translation_obj, created = DoctorTranslation.objects.get_or_create(doctor=doctor)
            translation_obj.translations = translations
            translation_obj.save()

            action = 'Created' if created else 'Updated'
            messages.success(
                request,
                f'🔄 {action} translations for Dr. {doctor.user.get_full_name()}'
            )

        except Doctor.DoesNotExist:
            messages.error(request, '❌ Doctor not found')
        except Exception as e:
            messages.error(request, f'❌ Refresh failed: {str(e)}')

        return HttpResponseRedirect(reverse('admin:doctors_doctortranslation_changelist'))

    actions = ['bulk_translate_doctors', 'bulk_refresh_translations']

    def bulk_translate_doctors(self, request, queryset):
        """Bulk action to translate multiple doctors"""
        translation_service = DoctorTranslationService()
        success_count = 0
        error_count = 0

        for translation_obj in queryset:
            try:
                doctor = translation_obj.doctor
                translations = translation_service.translate_doctor_profile(doctor)
                translation_service.save_doctor_translations(doctor, translations)
                success_count += 1
            except Exception as e:
                error_count += 1

        if success_count > 0:
            messages.success(request, f'✅ Successfully translated {success_count} doctor profiles')
        if error_count > 0:
            messages.warning(request, f'⚠️ Failed to translate {error_count} doctor profiles')

    bulk_translate_doctors.short_description = '🌐 Bulk translate selected doctors'

    def bulk_refresh_translations(self, request, queryset):
        """Bulk action to refresh translations for multiple doctors"""
        translation_service = DoctorTranslationService()
        success_count = 0

        for translation_obj in queryset:
            try:
                translations = translation_service.translate_doctor_profile(translation_obj.doctor)
                translation_obj.translations = translations
                translation_obj.save()
                success_count += 1
            except Exception:
                pass

        messages.success(request, f'🔄 Refreshed {success_count} translation records')

    bulk_refresh_translations.short_description = '🔄 Bulk refresh selected translations'