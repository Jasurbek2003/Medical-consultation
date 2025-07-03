from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Consultation
)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = [
        'consultation_info', 'patient_doctor_info', 'scheduled_info',
        'status_badge', 'consultation_type_badge', 'payment_status', 'actions_column'
    ]
    list_filter = [
        'status', 'consultation_type', 'priority', 'is_paid',
        'scheduled_date', 'created_at'
    ]
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
        'chief_complaint'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'final_amount'
    ]
    date_hierarchy = 'scheduled_date'
    list_per_page = 20

    fieldsets = (
        ('📋 Asosiy Ma\'lumotlar', {
            'fields': ('id', 'patient', 'doctor', 'chat_session'),
            'classes': ('wide',)
        }),
        ('🏥 Konsultatsiya Detallari', {
            'fields': (
                'consultation_type', 'status', 'priority',
                'scheduled_date', 'scheduled_time', 'duration_minutes'
            ),
            'classes': ('wide',)
        }),
        ('🩺 Tibbiy Ma\'lumotlar', {
            'fields': (
                'chief_complaint', 'symptoms', 'symptom_duration',
                'current_medications', 'allergies'
            ),
            'classes': ('wide',)
        }),
        ('💰 Moliyaviy', {
            'fields': (
                'consultation_fee', 'discount_amount', 'final_amount',
                'is_paid', 'payment_method'
            ),
            'classes': ('wide',)
        }),
        ('📝 Qo\'shimcha', {
            'fields': ('notes', 'referral_reason'),
            'classes': ('collapse',)
        }),
        ('⏰ Vaqt Ma\'lumotlari', {
            'fields': (
                'actual_start_time', 'actual_end_time',
                'created_at', 'updated_at', 'cancelled_at', 'cancellation_reason'
            ),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_completed', 'mark_as_paid', 'send_reminder']

    def consultation_info(self, obj):
        return format_html(
            '<div style="background: white; padding: 10px; border-radius: 8px; border-left: 4px solid #667eea;">'
            '<strong style="color: #333; font-size: 13px;">#{}</strong>'
            '<br><small style="color: #666;">📅 {}</small>'
            '</div>',
            str(obj.id)[:8], obj.created_at.strftime('%d.%m.%Y %H:%M')
        )

    consultation_info.short_description = '🆔 ID'

    def patient_doctor_info(self, obj):
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">'
            '<div style="margin-bottom: 5px;"><strong style="color: #667eea;">👤 {}</strong></div>'
            '<div><strong style="color: #28a745;">👨‍⚕️ {}</strong></div>'
            '</div>',
            obj.patient.get_full_name() or obj.patient.phone,
            obj.doctor.get_short_name()
        )

    patient_doctor_info.short_description = '👥 Ishtirokchilar'

    def scheduled_info(self, obj):
        return format_html(
            '<div style="text-align: center; background: #e8f4fd; padding: 8px; border-radius: 8px; border: 1px solid #bee5eb;">'
            '<strong style="color: #0c5460;">📅 {}</strong>'
            '<br><strong style="color: #0c5460;">🕐 {}</strong>'
            '<br><small style="color: #666;">⏱️ {} min</small>'
            '</div>',
            obj.scheduled_date.strftime('%d.%m.%Y'),
            obj.scheduled_time.strftime('%H:%M'),
            obj.duration_minutes
        )

    scheduled_info.short_description = '📅 Vaqt'

    def status_badge(self, obj):
        status_colors = {
            'scheduled': '#ffc107',
            'in_progress': '#17a2b8',
            'completed': '#28a745',
            'cancelled': '#dc3545',
            'no_show': '#6c757d',
            'rescheduled': '#fd7e14',
        }

        status_emojis = {
            'scheduled': '📅',
            'in_progress': '⏳',
            'completed': '✅',
            'cancelled': '❌',
            'no_show': '👻',
            'rescheduled': '🔄',
        }

        color = status_colors.get(obj.status, '#6c757d')
        emoji = status_emojis.get(obj.status, '❓')

        return format_html(
            '<span style="background: {}; color: white; padding: 5px 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
            '{} {}</span>',
            color, emoji, obj.get_status_display()
        )

    status_badge.short_description = '📊 Holat'

    def consultation_type_badge(self, obj):
        type_colors = {
            'online': '#17a2b8',
            'offline': '#28a745',
            'phone': '#ffc107',
            'video': '#6f42c1',
            'home_visit': '#fd7e14',
        }

        type_emojis = {
            'online': '💻',
            'offline': '🏥',
            'phone': '📞',
            'video': '📹',
            'home_visit': '🏠',
        }

        color = type_colors.get(obj.consultation_type, '#6c757d')
        emoji = type_emojis.get(obj.consultation_type, '❓')

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: 600; display: inline-flex; align-items: center; gap: 3px;">'
            '{} {}</span>',
            color, emoji, obj.get_consultation_type_display()
        )

    consultation_type_badge.short_description = '💻 Tur'

    def payment_status(self, obj):
        if obj.is_paid:
            return format_html(
                '<div style="text-align: center;">'
                '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">💳 To\'langan</span>'
                '<br><small style="color: #28a745; font-weight: 600; margin-top: 4px; display: block;">{:,} so\'m</small>'
                '</div>',
                int(obj.final_amount)
            )
        else:
            return format_html(
                '<div style="text-align: center;">'
                '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">💸 To\'lanmagan</span>'
                '<br><small style="color: #dc3545; font-weight: 600; margin-top: 4px; display: block;">{:,} so\'m</small>'
                '</div>',
                int(obj.final_amount)
            )

    payment_status.short_description = '💰 To\'lov'

    def actions_column(self, obj):
        actions_html = '<div style="display: flex; gap: 4px; justify-content: center;">'

        if obj.status == 'scheduled':
            actions_html += '<span style="background: #17a2b8; color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px;">▶️ Boshlash mumkin</span>'
        elif obj.status == 'in_progress':
            actions_html += '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px;">✅ Yakunlash mumkin</span>'
        elif obj.status == 'completed':
            actions_html += '<span style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px;">📋 Tugallangan</span>'

        actions_html += '</div>'
        return format_html(actions_html)

    actions_column.short_description = '⚡ Amallar'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(
            request,
            format_html('✅ <strong>{}</strong> ta konsultatsiya tugallandi.', updated),
            level='SUCCESS'
        )

    mark_as_completed.short_description = "✅ Tugallangan deb belgilash"

    def mark_as_paid(self, request, queryset):
        updated = queryset.update(is_paid=True)
        self.message_user(
            request,
            format_html('💳 <strong>{}</strong> ta konsultatsiya to\'landi.', updated),
            level='SUCCESS'
        )

    mark_as_paid.short_description = "💳 To'langan deb belgilash"

    def send_reminder(self, request, queryset):
        count = queryset.count()
        self.message_user(
            request,
            format_html('📧 <strong>{}</strong> ta konsultatsiya uchun eslatma yuborildi.', count),
            level='INFO'
        )

    send_reminder.short_description = "📧 Eslatma yuborish"