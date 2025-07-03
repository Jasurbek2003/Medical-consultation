from django.contrib import admin
from django.utils.html import format_html

from .models import Doctor, DoctorSchedule, DoctorSpecialization


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'get_photo_thumbnail', 'get_full_name_with_emoji', 'specialty_badge',
        'experience_years', 'rating_stars', 'consultation_price_formatted',
        'availability_status', 'total_reviews', 'region_info'
    ]
    list_filter = [
        'specialty', 'degree', 'is_available', 'region',
        'is_online_consultation', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'phone', 'email',
        'license_number', 'workplace'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'rating', 'total_reviews', 'get_photo_preview'
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = (
        ('👤 Shaxsiy Ma\'lumotlar', {
            'fields': ('get_photo_preview', 'photo', 'first_name', 'last_name', 'middle_name'),
            'classes': ('wide',),
            'description': 'Shifokorning shaxsiy ma\'lumotlari'
        }),
        ('🏥 Professional Ma\'lumotlar', {
            'fields': (
                'specialty', 'degree', 'experience', 'license_number',
                'education', 'achievements', 'bio'
            ),
            'classes': ('wide',),
            'description': 'Professional malaka va tajriba'
        }),
        ('📞 Kontakt Ma\'lumotlar', {
            'fields': ('phone', 'email', 'languages'),
            'classes': ('wide',)
        }),
        ('📍 Manzil va Ish Joyi', {
            'fields': ('region', 'district', 'address', 'workplace', 'workplace_address'),
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
            'fields': ('rating', 'total_reviews'),
            'classes': ('collapse',),
            'description': 'Avtomatik hisoblanadigan statistikalar'
        }),
        ('⏰ Meta Ma\'lumotlar', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['make_available', 'make_unavailable', 'send_notification', 'export_selected']

    def get_photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 3px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">',
                obj.photo.url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">👨‍⚕️</div>'
        )

    get_photo_thumbnail.short_description = '📷'

    def get_full_name_with_emoji(self, obj):
        return format_html(
            '<strong style="color: #333; font-size: 14px;">Dr. {} {}</strong><br>'
            '<small style="color: #666; font-size: 12px;">🆔 {}</small>',
            obj.first_name, obj.last_name, obj.license_number
        )

    get_full_name_with_emoji.short_description = '👨‍⚕️ Shifokor'

    def get_photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<div style="text-align: center;"><img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);"><br><small style="color: #666; margin-top: 10px; display: block;">Fayl hajmi: {} KB</small></div>',
                obj.photo.url,
                round(obj.photo.size / 1024, 1) if obj.photo.size else 0
            )
        return format_html(
            '<div style="text-align: center; padding: 50px; background: #f8f9fa; border-radius: 15px; border: 2px dashed #dee2e6;">'
            '<div style="font-size: 48px; color: #6c757d; margin-bottom: 15px;">📷</div>'
            '<p style="color: #6c757d; margin: 0;">Rasm yuklanmagan</p></div>'
        )

    get_photo_preview.short_description = '🖼️ Rasm Preview'

    def specialty_badge(self, obj):
        specialty_colors = {
            'terapevt': '#007bff',
            'stomatolog': '#28a745',
            'kardiolog': '#dc3545',
            'urolog': '#6f42c1',
            'ginekolog': '#e83e8c',
            'pediatr': '#fd7e14',
            'dermatolog': '#20c997',
            'nevrolog': '#6c757d',
            'oftalmolog': '#17a2b8',
            'lor': '#ffc107',
            'ortoped': '#795548',
            'psixiatr': '#9c27b0',
            'endokrinolog': '#ff5722',
            'gastroenterolog': '#607d8b',
            'pulmonolog': '#3f51b5',
        }

        specialty_emojis = {
            'terapevt': '🩺',
            'stomatolog': '🦷',
            'kardiolog': '❤️',
            'urolog': '🩺',
            'ginekolog': '👩‍⚕️',
            'pediatr': '👶',
            'dermatolog': '🧴',
            'nevrolog': '🧠',
            'oftalmolog': '👁️',
            'lor': '👂',
            'ortoped': '🦴',
            'psixiatr': '🧠',
            'endokrinolog': '⚕️',
            'gastroenterolog': '🫃',
            'pulmonolog': '🫁',
        }

        color = specialty_colors.get(obj.specialty, '#6c757d')
        emoji = specialty_emojis.get(obj.specialty, '⚕️')

        return format_html(
            '<span style="background: {}; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px;">'
            '{} {}</span>',
            color, emoji, obj.get_specialty_display()
        )

    specialty_badge.short_description = '🏥 Mutaxassislik'

    def experience_years(self, obj):
        if obj.experience >= 10:
            icon = '🥇'
            color = '#ffd700'
        elif obj.experience >= 5:
            icon = '🥈'
            color = '#c0c0c0'
        else:
            icon = '🥉'
            color = '#cd7f32'

        return format_html(
            '<span style="color: {}; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
            '{} {} yil</span>',
            color, icon, obj.experience
        )

    experience_years.short_description = '🎯 Tajriba'

    def rating_stars(self, obj):
        full_stars = int(obj.rating)
        half_star = obj.rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)

        stars_html = '⭐' * full_stars
        if half_star:
            stars_html += '⭐'
        stars_html += '☆' * empty_stars

        rating_color = '#ffc107' if obj.rating >= 4.0 else '#17a2b8' if obj.rating >= 3.0 else '#6c757d'

        return format_html(
            '<div style="display: flex; flex-direction: column; align-items: center;">'
            '<span style="font-size: 16px; letter-spacing: 1px;" title="{}/5">{}</span>'
            '<small style="color: {}; font-weight: 600; margin-top: 2px;">{:.1f}/5</small>'
            '</div>',
            obj.rating, stars_html, rating_color, obj.rating
        )

    rating_stars.short_description = '⭐ Reyting'

    def consultation_price_formatted(self, obj):
        price = int(obj.consultation_price)
        if price >= 1000000:
            display_price = f"{price / 1000000:.1f}M"
        elif price >= 1000:
            display_price = f"{price / 1000:.0f}K"
        else:
            display_price = str(price)

        return format_html(
            '<div style="text-align: center;">'
            '<span style="color: #28a745; font-weight: 700; font-size: 14px;">💰 {}</span>'
            '<br><small style="color: #666; font-size: 11px;">{:,} so\'m</small>'
            '</div>',
            display_price, price
        )

    consultation_price_formatted.short_description = '💰 Narx'

    def availability_status(self, obj):
        if obj.is_available:
            status_html = '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">✅ Mavjud</span>'
            if obj.is_online_consultation:
                status_html += '<br><span style="background: #17a2b8; color: white; padding: 2px 8px; border-radius: 8px; font-size: 10px; margin-top: 4px; display: inline-block;">💻 Online</span>'
        else:
            status_html = '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">❌ Band</span>'
        return format_html(status_html)

    availability_status.short_description = '🟢 Holat'

    def region_info(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<strong style="color: #667eea; font-size: 13px;">📍 {}</strong>'
            '<br><small style="color: #666; font-size: 11px;">{}</small>'
            '</div>',
            obj.region, obj.district
        )

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
            level='WARNING'
        )

    make_unavailable.short_description = "❌ Band qilish"

    def send_notification(self, request, queryset):
        count = queryset.count()
        self.message_user(
            request,
            format_html('📧 <strong>{}</strong> ta shifokorga bildirishnoma yuborildi.', count),
            level='INFO'
        )

    send_notification.short_description = "📧 Bildirishnoma yuborish"

    def export_selected(self, request, queryset):
        count = queryset.count()
        self.message_user(
            request,
            format_html('📊 <strong>{}</strong> ta shifokor ma\'lumotlari eksport qilindi.', count),
            level='SUCCESS'
        )

    export_selected.short_description = "📊 Eksport qilish"

    # Custom view uchun
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related().prefetch_related('specializations', 'schedules')


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor_info', 'weekday_badge', 'time_range', 'availability_status']
    list_filter = ['weekday', 'is_available', 'doctor__specialty']
    search_fields = ['doctor__first_name', 'doctor__last_name']
    list_per_page = 20

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
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px;">👨‍⚕️</div>'
            '<div>'
            '<strong style="color: #333;">{}</strong>'
            '<br><small style="color: #666;">{}</small>'
            '</div>'
            '</div>',
            obj.doctor.get_short_name(),
            obj.doctor.get_specialty_display()
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
        return format_html(
            '<div style="text-align: center; background: #f8f9fa; padding: 8px 12px; border-radius: 10px; border: 2px solid #e9ecef;">'
            '<span style="color: #667eea; font-weight: 600; font-size: 13px;">🕐 {} - {}</span>'
            '</div>',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M')
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
    search_fields = ['doctor__first_name', 'doctor__last_name', 'name']
    list_filter = ['doctor__specialty']

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
        return format_html(
            '<strong style="color: #667eea;">{}</strong>',
            obj.doctor.get_short_name()
        )

    doctor_name.short_description = '👨‍⚕️ Shifokor'

    def specialization_name(self, obj):
        return format_html(
            '<div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 8px 15px; border-radius: 12px; display: inline-block; font-weight: 600;">'
            '🎓 {}</div>',
            obj.name
        )

    specialization_name.short_description = '🎓 Mutaxassislik'

    def has_certificate(self, obj):
        if obj.certificate:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;">📜 Mavjud</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;">❌ Yo\'q</span>'
        )

    has_certificate.short_description = '📜 Sertifikat'

    def certificate_info(self, obj):
        if obj.certificate:
            file_size = round(obj.certificate.size / 1024, 1) if obj.certificate.size else 0
            return format_html(
                '<small style="color: #666;">📁 {} KB</small>',
                file_size
            )
        return format_html('<small style="color: #999;">-</small>')

    certificate_info.short_description = '📁 Fayl'

