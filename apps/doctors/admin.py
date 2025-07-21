from django.contrib import admin
from django.utils.html import format_html

from .models import Doctor, DoctorSchedule, DoctorSpecialization


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

    actions = ['make_available', 'make_unavailable', 'approve_doctors', 'reject_doctors', 'send_notification']

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
            badge_text = 'Middle'
        else:
            badge_color = '#17a2b8'
            badge_text = 'Junior'

        return format_html(
            '<div style="text-align: center;">'
            '<strong style="font-size: 18px; color: #333;">{}</strong> yil'
            '<br><span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-top: 2px; display: inline-block;">{}</span>'
            '</div>',
            obj.experience, badge_color, badge_text
        )

    experience_years.short_description = '🎯 Tajriba'

    def rating_stars(self, obj):
        return format_html(
            '<div style="display: flex; flex-direction: column; align-items: center;">'
            '<span style="font-size: 14px; letter-spacing: 1px;" title="{}/5">{}</span>'
            '</div>',
            obj.rating, obj.rating
        )

    rating_stars.short_description = '⭐ Reyting'

    def consultation_price_formatted(self, obj):
        price = int(obj.consultation_price)
        if price >= 1000000:
            display_price = "{:.1f}M".format(price / 1000000)
        elif price >= 1000:
            display_price = "{:.0f}K".format(price / 1000)
        else:
            display_price = str(price)

        return format_html(
            '<div style="text-align: center;"><span style="color: #28a745; font-weight: 700; font-size: 14px;">💰 {}</span><br><small style="color: #666; font-size: 11px;">{} so\'m</small></div>',
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

        # Verification status
        if obj.verification_status == 'approved':
            status_html += '<br><span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 8px; font-size: 10px; margin-top: 2px; display: inline-block;">✅ Tasdiqlangan</span>'
        elif obj.verification_status == 'pending':
            status_html += '<br><span style="background: #ffc107; color: black; padding: 2px 8px; border-radius: 8px; font-size: 10px; margin-top: 2px; display: inline-block;">⏳ Kutilmoqda</span>'
        elif obj.verification_status == 'rejected':
            status_html += '<br><span style="background: #dc3545; color: white; padding: 2px 8px; border-radius: 8px; font-size: 10px; margin-top: 2px; display: inline-block;">❌ Rad etilgan</span>'

        return format_html(status_html)

    availability_status.short_description = '🟢 Holat'

    def region_info(self, obj):
        region = obj.user.region if obj.user.region else 'Belgilanmagan'
        district = obj.user.district if obj.user.district else 'Belgilanmagan'

        return format_html(
            '<div style="text-align: center;">'
            '<strong style="color: #667eea; font-size: 13px;">📍 {}</strong>'
            '<br><small style="color: #666; font-size: 11px;">{}</small>'
            '</div>',
            region, district
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
            '<strong style="color: #667eea;">{}</strong>',
            doctor_name
        )

    doctor_name.short_description = '👨‍⚕️ Shifokor'

    def specialization_name(self, obj):
        return format_html(
            '<span style="color: #28a745; font-weight: 600;">{}</span>',
            obj.name
        )

    specialization_name.short_description = '🎓 Mutaxassislik'

    def has_certificate(self, obj):
        if obj.certificate:
            return format_html('<span style="color: #28a745;">✅ Mavjud</span>')
        return format_html('<span style="color: #dc3545;">❌ Yo\'q</span>')

    has_certificate.short_description = '📜 Sertifikat'

    def certificate_info(self, obj):
        if obj.certificate:
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff;">📥 Yuklab olish</a>',
                obj.certificate.url
            )
        return '-'

    certificate_info.short_description = '📄 Fayl'