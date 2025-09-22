from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
import csv
from decimal import Decimal

from .models import (
    PaymentGateway, Payment, PaymentWebhook,
    ClickTransaction, PaymeTransaction, PaymentMethod,
    PaymentRefund, PaymentDispute
)
from apps.billing.models import UserWallet, WalletTransaction, BillingRule, DoctorViewCharge, BillingSettings


class PaymentStatusFilter(SimpleListFilter):
    """Custom filter for payment status"""
    title = 'Payment Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return Payment.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class PaymentAmountFilter(SimpleListFilter):
    """Filter payments by amount ranges"""
    title = 'Amount Range'
    parameter_name = 'amount_range'

    def lookups(self, request, model_admin):
        return [
            ('small', 'Under 50,000'),
            ('medium', '50,000 - 500,000'),
            ('large', '500,000 - 5,000,000'),
            ('xlarge', 'Over 5,000,000'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'small':
            return queryset.filter(amount__lt=50000)
        elif self.value() == 'medium':
            return queryset.filter(amount__gte=50000, amount__lt=500000)
        elif self.value() == 'large':
            return queryset.filter(amount__gte=500000, amount__lt=5000000)
        elif self.value() == 'xlarge':
            return queryset.filter(amount__gte=5000000)
        return queryset


class PaymentDateFilter(SimpleListFilter):
    """Filter payments by date"""
    title = 'Date Created'
    parameter_name = 'date_created'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'yesterday':
            yesterday = now.date() - timezone.timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        elif self.value() == 'week':
            week_ago = now - timezone.timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timezone.timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        return queryset


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    """Payment Gateway administration"""

    list_display = [
        'display_name', 'name', 'is_active_display', 'is_test_mode_display',
        'default_currency', 'commission_info', 'payment_count', 'last_used_at'
    ]
    list_filter = ['is_active', 'is_test_mode', 'name', 'default_currency', 'commission_type']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['last_used_at', 'created_at', 'updated_at', 'payment_stats']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'display_name', 'description', 'logo',
                'is_active', 'is_test_mode', 'sort_order'
            )
        }),
        ('Gateway Configuration', {
            'fields': (
                'merchant_id', 'service_id', 'secret_key', 'public_key',
                'api_url', 'webhook_url'
            )
        }),
        ('Currency & Limits', {
            'fields': (
                'supported_currencies', 'default_currency',
                'min_amount', 'max_amount'
            )
        }),
        ('Commission Settings', {
            'fields': (
                'commission_type', 'commission_percentage', 'commission_fixed'
            )
        }),
        ('Processing Settings', {
            'fields': (
                'processing_time_minutes', 'auto_capture',
                'supports_refunds', 'supports_recurring'
            )
        }),
        ('Advanced', {
            'fields': ('extra_config',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('payment_stats', 'last_used_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def is_active_display(self, obj):
        """Display active status with color"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'

    def is_test_mode_display(self, obj):
        """Display test mode status"""
        if obj.is_test_mode:
            return format_html('<span style="color: orange;">🧪 Test</span>')
        return format_html('<span style="color: blue;">🚀 Live</span>')
    is_test_mode_display.short_description = 'Mode'

    def commission_info(self, obj):
        """Display commission information"""
        if obj.commission_type == 'percentage':
            return f"{obj.commission_percentage}%"
        elif obj.commission_type == 'fixed':
            return f"{obj.commission_fixed} {obj.default_currency}"
        else:
            return f"{obj.commission_percentage}% + {obj.commission_fixed}"
    commission_info.short_description = 'Commission'

    def payment_count(self, obj):
        """Display number of payments"""
        count = obj.payments.count()
        url = reverse('admin:payments_payment_changelist') + f'?gateway__id__exact={obj.id}'
        return format_html('<a href="{}">{} payments</a>', url, count)
    payment_count.short_description = 'Payments'

    def payment_stats(self, obj):
        """Display payment statistics"""
        total_payments = obj.payments.count()
        successful = obj.payments.filter(status='completed').count()
        total_amount = obj.payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        success_rate = (successful / total_payments * 100) if total_payments > 0 else 0

        stats_html = f"""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Payment Statistics:</strong><br>
            Total Payments: {total_payments}<br>
            Successful: {successful} ({success_rate:.1f}%)<br>
            Total Volume: {total_amount:,.2f} {obj.default_currency}
        </div>
        """
        return format_html(stats_html)
    payment_stats.short_description = 'Payment Statistics'

    actions = ['activate_gateways', 'deactivate_gateways', 'enable_test_mode', 'disable_test_mode']

    def activate_gateways(self, request, queryset):
        """Activate selected gateways"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} gateways activated successfully.')
    activate_gateways.short_description = 'Activate selected gateways'

    def deactivate_gateways(self, request, queryset):
        """Deactivate selected gateways"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} gateways deactivated successfully.')
    deactivate_gateways.short_description = 'Deactivate selected gateways'

    def enable_test_mode(self, request, queryset):
        """Enable test mode for selected gateways"""
        count = queryset.update(is_test_mode=True)
        self.message_user(request, f'Test mode enabled for {count} gateways.')
    enable_test_mode.short_description = 'Enable test mode'

    def disable_test_mode(self, request, queryset):
        """Disable test mode for selected gateways"""
        count = queryset.update(is_test_mode=False)
        self.message_user(request, f'Test mode disabled for {count} gateways.')
    disable_test_mode.short_description = 'Disable test mode'


class ClickTransactionInline(admin.StackedInline):
    """Inline for Click transactions"""
    model = ClickTransaction
    extra = 0
    readonly_fields = ['click_trans_id', 'merchant_trans_id', 'service_id', 'created_at', 'updated_at']
    fields = [
        'click_trans_id', 'click_paydoc_id', 'merchant_trans_id', 'service_id',
        'merchant_prepare_id', 'merchant_confirm_id', 'sign_time',
        'error_code', 'error_note', 'card_type', 'card_number_masked'
    ]


class PaymeTransactionInline(admin.StackedInline):
    """Inline for Payme transactions"""
    model = PaymeTransaction
    extra = 0
    readonly_fields = ['payme_id', 'payme_time', 'create_time', 'created_at', 'updated_at']
    fields = [
        'payme_id', 'payme_time', 'create_time', 'perform_time', 'cancel_time',
        'state', 'reason', 'account', 'receivers'
    ]


class PaymentRefundInline(admin.TabularInline):
    """Inline for payment refunds"""
    model = PaymentRefund
    extra = 0
    readonly_fields = ['id', 'created_at', 'processed_at', 'completed_at']
    fields = [
        'amount', 'reason', 'status', 'requested_by', 'processed_by',
        'reason_description', 'created_at'
    ]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment administration with comprehensive features"""

    list_display = [
        'reference_number', 'user_name', 'gateway_name', 'amount_display',
        'status_display', 'payment_type_display', 'created_at_display',
        'actions_column'
    ]
    list_filter = [
        PaymentStatusFilter, 'gateway', 'payment_type', 'currency',
        PaymentAmountFilter, PaymentDateFilter, 'payment_method'
    ]
    search_fields = [
        'reference_number', 'user__email', 'user__first_name', 'user__last_name',
        'gateway_transaction_id', 'gateway_payment_id', 'description'
    ]
    readonly_fields = [
        'id', 'reference_number', 'created_at', 'updated_at',
        'processing_started_at', 'completed_at', 'commission',
        'total_amount', 'payment_details', 'gateway_details'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'id', 'reference_number', 'user', 'gateway',
                'payment_type', 'payment_method', 'description'
            )
        }),
        ('Amount Details', {
            'fields': (
                'currency', 'amount', 'commission', 'discount',
                'total_amount'
            )
        }),
        ('Status & Processing', {
            'fields': (
                'status', 'attempt_count', 'max_attempts',
                'expires_at'
            )
        }),
        ('Gateway Integration', {
            'fields': (
                'gateway_transaction_id', 'gateway_payment_id',
                'gateway_reference', 'gateway_error_code', 'gateway_error_message'
            )
        }),
        ('URLs & Callbacks', {
            'fields': (
                'payment_url', 'success_url', 'cancel_url', 'callback_url'
            ),
            'classes': ('collapse',)
        }),
        ('Client Information', {
            'fields': (
                'ip_address', 'user_agent', 'client_info'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata & Additional Info', {
            'fields': ('metadata', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'processing_started_at',
                'completed_at'
            ),
            'classes': ('collapse',)
        }),
        ('System Details', {
            'fields': ('payment_details', 'gateway_details'),
            'classes': ('collapse',)
        })
    )

    inlines = [ClickTransactionInline, PaymeTransactionInline, PaymentRefundInline]

    def user_name(self, obj):
        """Display user name with link"""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return '-'
    user_name.short_description = 'User'
    user_name.admin_order_field = 'user__first_name'

    def gateway_name(self, obj):
        """Display gateway name with status"""
        color = 'green' if obj.gateway.is_active else 'red'
        mode = '🧪' if obj.gateway.is_test_mode else '🚀'
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, obj.gateway.display_name, mode
        )
    gateway_name.short_description = 'Gateway'
    gateway_name.admin_order_field = 'gateway__display_name'

    def amount_display(self, obj):
        """Display amount with currency"""
        return f"{obj.amount:,.2f} {obj.currency}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'expired': 'darkred',
            'refunded': 'purple'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def payment_type_display(self, obj):
        """Display payment type"""
        icons = {
            'wallet_topup': '💳',
            'consultation': '🩺',
            'doctor_view': '👨‍⚕️',
            'subscription': '📅',
            'service': '🛠️',
            'refund': '↩️'
        }
        icon = icons.get(obj.payment_type, '💰')
        return f"{icon} {obj.get_payment_type_display()}"
    payment_type_display.short_description = 'Type'

    def created_at_display(self, obj):
        """Display creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'

    def actions_column(self, obj):
        """Display action buttons"""
        actions = []

        if obj.status == 'pending':
            actions.append('<button onclick="cancelPayment(\'{}\')">Cancel</button>'.format(obj.id))

        if obj.status == 'completed' and obj.can_be_refunded():
            actions.append('<button onclick="refundPayment(\'{}\')">Refund</button>'.format(obj.id))

        if obj.can_retry():
            actions.append('<button onclick="retryPayment(\'{}\')">Retry</button>'.format(obj.id))

        return format_html(' '.join(actions))
    actions_column.short_description = 'Actions'

    def payment_details(self, obj):
        """Display detailed payment information"""
        refunded_amount = obj.get_refunded_amount()
        refundable_amount = obj.get_refundable_amount()

        details_html = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
            <h4>Payment Details</h4>
            <table style="width: 100%;">
                <tr><td><strong>Reference:</strong></td><td>{obj.reference_number}</td></tr>
                <tr><td><strong>Amount:</strong></td><td>{obj.amount} {obj.currency}</td></tr>
                <tr><td><strong>Commission:</strong></td><td>{obj.commission} {obj.currency}</td></tr>
                <tr><td><strong>Discount:</strong></td><td>{obj.discount} {obj.currency}</td></tr>
                <tr><td><strong>Total:</strong></td><td>{obj.total_amount} {obj.currency}</td></tr>
                <tr><td><strong>Refunded:</strong></td><td>{refunded_amount} {obj.currency}</td></tr>
                <tr><td><strong>Refundable:</strong></td><td>{refundable_amount} {obj.currency}</td></tr>
                <tr><td><strong>Attempts:</strong></td><td>{obj.attempt_count}/{obj.max_attempts}</td></tr>
            </table>
        </div>
        """
        return format_html(details_html)
    payment_details.short_description = 'Payment Details'

    def gateway_details(self, obj):
        """Display gateway-specific details"""
        details_html = f"""
        <div style="background: #e3f2fd; padding: 15px; border-radius: 5px;">
            <h4>Gateway Details</h4>
            <table style="width: 100%;">
                <tr><td><strong>Gateway:</strong></td><td>{obj.gateway.display_name}</td></tr>
                <tr><td><strong>Transaction ID:</strong></td><td>{obj.gateway_transaction_id or 'N/A'}</td></tr>
                <tr><td><strong>Payment ID:</strong></td><td>{obj.gateway_payment_id or 'N/A'}</td></tr>
                <tr><td><strong>Reference:</strong></td><td>{obj.gateway_reference or 'N/A'}</td></tr>
                <tr><td><strong>Error Code:</strong></td><td>{obj.gateway_error_code or 'N/A'}</td></tr>
                <tr><td><strong>Error Message:</strong></td><td>{obj.gateway_error_message or 'N/A'}</td></tr>
            </table>
        </div>
        """
        return format_html(details_html)
    gateway_details.short_description = 'Gateway Details'

    actions = ['export_to_csv', 'cancel_payments', 'retry_failed_payments', 'mark_as_completed']

    def export_to_csv(self, request, queryset):
        """Export selected payments to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Reference', 'User', 'Gateway', 'Amount', 'Currency', 'Status',
            'Type', 'Created', 'Completed'
        ])

        for payment in queryset:
            writer.writerow([
                payment.reference_number,
                payment.user.get_full_name(),
                payment.gateway.display_name,
                payment.amount,
                payment.currency,
                payment.status,
                payment.get_payment_type_display(),
                payment.created_at.strftime('%Y-%m-%d %H:%M'),
                payment.completed_at.strftime('%Y-%m-%d %H:%M') if payment.completed_at else 'N/A'
            ])

        return response
    export_to_csv.short_description = 'Export selected payments to CSV'

    def cancel_payments(self, request, queryset):
        """Cancel selected pending payments"""
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_as_cancelled('Admin action')
            count += 1
        self.message_user(request, f'{count} payments cancelled successfully.')
    cancel_payments.short_description = 'Cancel selected pending payments'

    def retry_failed_payments(self, request, queryset):
        """Reset failed payments for retry"""
        count = 0
        for payment in queryset.filter(status='failed'):
            if payment.can_retry():
                payment.status = 'pending'
                payment.attempt_count = 0
                payment.gateway_error_code = ''
                payment.gateway_error_message = ''
                payment.save()
                count += 1
        self.message_user(request, f'{count} payments reset for retry.')
    retry_failed_payments.short_description = 'Reset failed payments for retry'

    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed (admin override)"""
        count = 0
        for payment in queryset.filter(status__in=['pending', 'processing']):
            payment.mark_as_completed()
            count += 1
        self.message_user(request, f'{count} payments marked as completed.')
    mark_as_completed.short_description = 'Mark as completed (admin override)'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Payment Method administration"""

    list_display = [
        'user_name', 'gateway_name', 'method_type_display', 'nickname',
        'is_default', 'is_active', 'is_verified', 'usage_count', 'last_used_at'
    ]
    list_filter = [
        'method_type', 'card_type', 'is_default', 'is_active',
        'is_verified', 'gateway'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'nickname', 'card_holder_name', 'bank_name'
    ]
    readonly_fields = [
        'gateway_token', 'gateway_customer_id', 'gateway_method_id',
        'usage_count', 'last_used_at', 'created_at', 'updated_at',
        'expires_at'
    ]

    def user_name(self, obj):
        """Display user name"""
        return obj.user.get_full_name()
    user_name.short_description = 'User'

    def gateway_name(self, obj):
        """Display gateway name"""
        return obj.gateway.display_name
    gateway_name.short_description = 'Gateway'

    def method_type_display(self, obj):
        """Display method type with icon"""
        icons = {
            'card': '💳',
            'wallet': '👛',
            'bank_account': '🏦',
            'mobile_money': '📱'
        }
        icon = icons.get(obj.method_type, '💰')
        return f"{icon} {obj.get_method_type_display()}"
    method_type_display.short_description = 'Type'


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    """Payment Refund administration"""

    list_display = [
        'id_short', 'payment_reference', 'amount_display', 'status_display',
        'reason_display', 'requested_by_name', 'created_at'
    ]
    list_filter = [
        'status', 'reason', 'currency', 'payment__gateway'
    ]
    search_fields = [
        'payment__reference_number', 'payment__user__email',
        'reason_description', 'customer_notes'
    ]
    readonly_fields = [
        'id', 'gateway_refund_id', 'gateway_reference',
        'created_at', 'updated_at', 'processed_at', 'completed_at'
    ]

    def id_short(self, obj):
        """Display short ID"""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def payment_reference(self, obj):
        """Display payment reference with link"""
        url = reverse('admin:payments_payment_change', args=[obj.payment.pk])
        return format_html('<a href="{}">{}</a>', url, obj.payment.reference_number)
    payment_reference.short_description = 'Payment'

    def amount_display(self, obj):
        """Display amount with currency"""
        return f"{obj.amount:,.2f} {obj.currency}"
    amount_display.short_description = 'Amount'

    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'rejected': 'darkred'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def reason_display(self, obj):
        """Display reason"""
        return obj.get_reason_display()
    reason_display.short_description = 'Reason'

    def requested_by_name(self, obj):
        """Display requester name"""
        if obj.requested_by:
            return obj.requested_by.get_full_name()
        return 'System'
    requested_by_name.short_description = 'Requested By'

    actions = ['approve_refunds', 'reject_refunds', 'process_refunds']

    def approve_refunds(self, request, queryset):
        """Approve selected refunds"""
        count = 0
        for refund in queryset.filter(status='pending'):
            refund.approve(approved_by=request.user)
            count += 1
        self.message_user(request, f'{count} refunds approved.')
    approve_refunds.short_description = 'Approve selected refunds'

    def reject_refunds(self, request, queryset):
        """Reject selected refunds"""
        count = 0
        for refund in queryset.filter(status='pending'):
            refund.reject(reason='Admin decision', rejected_by=request.user)
            count += 1
        self.message_user(request, f'{count} refunds rejected.')
    reject_refunds.short_description = 'Reject selected refunds'

    def process_refunds(self, request, queryset):
        """Process approved refunds"""
        count = 0
        for refund in queryset.filter(status='processing'):
            if refund.can_be_processed():
                refund.process_refund(processed_by=request.user)
                count += 1
        self.message_user(request, f'{count} refunds processed.')
    process_refunds.short_description = 'Process approved refunds'


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    """Payment Dispute administration"""

    list_display = [
        'dispute_id', 'payment_reference', 'amount_display',
        'status_display', 'reason_display', 'created_at'
    ]
    list_filter = ['status', 'reason', 'payment__gateway']
    search_fields = [
        'dispute_id', 'payment__reference_number',
        'description', 'customer_message'
    ]
    readonly_fields = [
        'id', 'gateway_dispute_id', 'created_at', 'updated_at',
        'responded_at', 'closed_at'
    ]

    def payment_reference(self, obj):
        """Display payment reference with link"""
        url = reverse('admin:payments_payment_change', args=[obj.payment.pk])
        return format_html('<a href="{}">{}</a>', url, obj.payment.reference_number)
    payment_reference.short_description = 'Payment'

    def amount_display(self, obj):
        """Display amount"""
        return f"{obj.amount:,.2f} {obj.currency}"
    amount_display.short_description = 'Amount'

    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'opened': 'orange',
            'under_review': 'blue',
            'evidence_required': 'purple',
            'responded': 'teal',
            'won': 'green',
            'lost': 'red',
            'accepted': 'darkgreen',
            'closed': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def reason_display(self, obj):
        """Display reason"""
        return obj.get_reason_display()
    reason_display.short_description = 'Reason'


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    """Payment Webhook administration for debugging"""

    list_display = [
        'id_short', 'gateway_name', 'webhook_type_display',
        'processed_display', 'response_status', 'created_at'
    ]
    list_filter = [
        'gateway', 'webhook_type', 'processed', 'response_status',
        'signature_valid'
    ]
    search_fields = ['payment__reference_number', 'ip_address']
    readonly_fields = [
        'id', 'processing_time_ms', 'created_at', 'processed_at'
    ]
    date_hierarchy = 'created_at'

    def id_short(self, obj):
        """Display short ID"""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def gateway_name(self, obj):
        """Display gateway name"""
        return obj.gateway.display_name
    gateway_name.short_description = 'Gateway'

    def webhook_type_display(self, obj):
        """Display webhook type"""
        return obj.get_webhook_type_display()
    webhook_type_display.short_description = 'Type'

    def processed_display(self, obj):
        """Display processed status"""
        if obj.processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    processed_display.short_description = 'Processed'


@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    """Click Transaction administration"""

    list_display = [
        'click_trans_id', 'payment_reference', 'service_id',
        'error_code_display', 'created_at'
    ]
    list_filter = ['service_id', 'error_code', 'card_type']
    search_fields = [
        'click_trans_id', 'merchant_trans_id', 'payment__reference_number'
    ]
    readonly_fields = ['created_at', 'updated_at']

    def payment_reference(self, obj):
        """Display payment reference"""
        return obj.payment.reference_number
    payment_reference.short_description = 'Payment'

    def error_code_display(self, obj):
        """Display error code with color"""
        if obj.error_code == 0:
            return format_html('<span style="color: green;">Success</span>')
        return format_html('<span style="color: red;">Error {}</span>', obj.error_code)
    error_code_display.short_description = 'Status'


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    """Payme Transaction administration"""

    list_display = [
        'payme_id', 'payment_reference', 'state_display',
        'payme_time_display', 'created_at'
    ]
    list_filter = ['state', 'reason']
    search_fields = ['payme_id', 'payment__reference_number']
    readonly_fields = ['created_at', 'updated_at']

    def payment_reference(self, obj):
        """Display payment reference"""
        return obj.payment.reference_number
    payment_reference.short_description = 'Payment'

    def state_display(self, obj):
        """Display state with color"""
        colors = {1: 'orange', 2: 'green', -1: 'red', -2: 'darkred'}
        color = colors.get(obj.state, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_state_display()
        )
    state_display.short_description = 'State'

    def payme_time_display(self, obj):
        """Display Payme time"""
        if obj.payme_time:
            dt = obj.get_payme_time_as_datetime()
            return dt.strftime('%Y-%m-%d %H:%M') if dt else 'N/A'
        return 'N/A'
    payme_time_display.short_description = 'Payme Time'


# Custom admin site configuration
admin.site.site_header = 'Medical Consultation - Payment Administration'
admin.site.site_title = 'Payment Admin'
admin.site.index_title = 'Payment Management Dashboard'

# Add custom CSS and JavaScript for enhanced UI
class PaymentAdminConfig:
    """Custom admin configuration"""

    class Media:
        css = {
            'all': ('admin/css/payment_admin.css',)
        }
        js = ('admin/js/payment_admin.js',)


# Wallet and Billing Admin Classes
# @admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    """User Wallet administration"""

    list_display = [
        'user_name', 'balance_display', 'total_spent_display', 'total_topped_up_display',
        'is_blocked', 'transaction_count', 'created_at'
    ]
    list_filter = ['is_blocked', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'user__phone']
    readonly_fields = ['created_at', 'updated_at', 'wallet_stats']

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Balance Information', {
            'fields': ('balance', 'total_spent', 'total_topped_up')
        }),
        ('Status', {
            'fields': ('is_blocked',)
        }),
        ('Statistics', {
            'fields': ('wallet_stats',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_name(self, obj):
        """Display user name with link"""
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_name.short_description = 'User'

    def balance_display(self, obj):
        """Display balance with color coding"""
        color = 'green' if obj.balance > 0 else 'red' if obj.balance < 0 else 'gray'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:,.2f} so\'m</span>',
            color, obj.balance
        )
    balance_display.short_description = 'Balance'

    def total_spent_display(self, obj):
        """Display total spent"""
        return f"{obj.total_spent:,.2f} so'm"
    total_spent_display.short_description = 'Total Spent'

    def total_topped_up_display(self, obj):
        """Display total topped up"""
        return f"{obj.total_topped_up:,.2f} so'm"
    total_topped_up_display.short_description = 'Total Topped Up'

    def transaction_count(self, obj):
        """Display transaction count with link"""
        count = obj.transactions.count()
        url = reverse('admin:billing_wallettransaction_changelist') + f'?wallet__id__exact={obj.id}'
        return format_html('<a href="{}">{} transactions</a>', url, count)
    transaction_count.short_description = 'Transactions'

    def wallet_stats(self, obj):
        """Display wallet statistics"""
        total_transactions = obj.transactions.count()
        credit_count = obj.transactions.filter(transaction_type='credit').count()
        debit_count = obj.transactions.filter(transaction_type='debit').count()
        avg_transaction = (obj.total_spent + obj.total_topped_up) / total_transactions if total_transactions > 0 else 0

        stats_html = f"""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Wallet Statistics:</strong><br>
            Total Transactions: {total_transactions}<br>
            Credit Transactions: {credit_count}<br>
            Debit Transactions: {debit_count}<br>
            Average Transaction: {avg_transaction:,.2f} so'm<br>
            Net Balance Change: {obj.total_topped_up - obj.total_spent:,.2f} so'm
        </div>
        """
        return format_html(stats_html)
    wallet_stats.short_description = 'Wallet Statistics'

    actions = ['block_wallets', 'unblock_wallets', 'export_wallets']

    def block_wallets(self, request, queryset):
        """Block selected wallets"""
        count = queryset.update(is_blocked=True)
        self.message_user(request, f'{count} wallets blocked successfully.')
    block_wallets.short_description = 'Block selected wallets'

    def unblock_wallets(self, request, queryset):
        """Unblock selected wallets"""
        count = queryset.update(is_blocked=False)
        self.message_user(request, f'{count} wallets unblocked successfully.')
    unblock_wallets.short_description = 'Unblock selected wallets'

    def export_wallets(self, request, queryset):
        """Export wallet data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="wallets.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'User', 'Email', 'Phone', 'Balance', 'Total Spent', 'Total Topped Up',
            'Is Blocked', 'Created At'
        ])

        for wallet in queryset:
            writer.writerow([
                wallet.user.get_full_name(),
                wallet.user.email or '',
                wallet.user.phone or '',
                wallet.balance,
                wallet.total_spent,
                wallet.total_topped_up,
                wallet.is_blocked,
                wallet.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response
    export_wallets.short_description = 'Export selected wallets to CSV'


# @admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Wallet Transaction administration"""

    list_display = [
        'id_short', 'user_name', 'transaction_type_display', 'amount_display',
        'balance_after_display', 'status_display', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = [
        'wallet__user__email', 'wallet__user__first_name', 'wallet__user__last_name',
        'description'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def id_short(self, obj):
        """Display short ID"""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def user_name(self, obj):
        """Display user name"""
        return obj.wallet.user.get_full_name()
    user_name.short_description = 'User'

    def transaction_type_display(self, obj):
        """Display transaction type with icon"""
        icons = {'credit': '💳', 'debit': '💸'}
        icon = icons.get(obj.transaction_type, '💰')
        return f"{icon} {obj.get_transaction_type_display()}"
    transaction_type_display.short_description = 'Type'

    def amount_display(self, obj):
        """Display amount with color"""
        color = 'green' if obj.transaction_type == 'credit' else 'red'
        return format_html(
            '<span style="color: {};">{:,.2f} so\'m</span>',
            color, obj.amount
        )
    amount_display.short_description = 'Amount'

    def balance_after_display(self, obj):
        """Display balance after transaction"""
        return f"{obj.balance_after:,.2f} so'm"
    balance_after_display.short_description = 'Balance After'

    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'


# @admin.register(BillingRule)
class BillingRuleAdmin(admin.ModelAdmin):
    """Billing Rule administration"""

    list_display = [
        'service_type_display', 'price_display', 'is_active',
        'discount_info', 'usage_count', 'updated_at'
    ]
    list_filter = ['service_type', 'is_active']
    search_fields = ['service_type', 'description']
    readonly_fields = ['created_at', 'updated_at', 'usage_stats']

    fieldsets = (
        ('Service Information', {
            'fields': ('service_type', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_percentage', 'min_quantity_for_discount')
        }),
        ('Statistics', {
            'fields': ('usage_stats',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def service_type_display(self, obj):
        """Display service type"""
        return obj.get_service_type_display()
    service_type_display.short_description = 'Service'

    def price_display(self, obj):
        """Display price"""
        return f"{obj.price:,.2f} so'm"
    price_display.short_description = 'Price'

    def discount_info(self, obj):
        """Display discount information"""
        if obj.discount_percentage > 0:
            return f"{obj.discount_percentage}% (min {obj.min_quantity_for_discount})"
        return "No discount"
    discount_info.short_description = 'Discount'

    def usage_count(self, obj):
        """Display usage count for doctor views"""
        if obj.service_type == 'doctor_view':
            count = DoctorViewCharge.objects.exclude(amount_charged=0).count()
            return f"{count} charges"
        return "N/A"
    usage_count.short_description = 'Usage'

    def usage_stats(self, obj):
        """Display usage statistics"""
        if obj.service_type == 'doctor_view':
            total_charges = DoctorViewCharge.objects.exclude(amount_charged=0).count()
            total_revenue = DoctorViewCharge.objects.exclude(amount_charged=0).aggregate(
                total=Sum('amount_charged')
            )['total'] or 0

            stats_html = f"""
            <div style="background: #e3f2fd; padding: 10px; border-radius: 5px;">
                <strong>Usage Statistics:</strong><br>
                Total Charges: {total_charges}<br>
                Total Revenue: {total_revenue:,.2f} so'm<br>
                Average per Charge: {total_revenue / total_charges if total_charges > 0 else 0:,.2f} so'm
            </div>
            """
            return format_html(stats_html)
        return "No statistics available"
    usage_stats.short_description = 'Usage Statistics'


# @admin.register(DoctorViewCharge)
class DoctorViewChargeAdmin(admin.ModelAdmin):
    """Doctor View Charge administration"""

    list_display = [
        'user_name', 'doctor_name', 'amount_charged_display',
        'is_free_view', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'doctor__first_name', 'doctor__last_name'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def user_name(self, obj):
        """Display user name"""
        return obj.user.get_full_name()
    user_name.short_description = 'User'

    def doctor_name(self, obj):
        """Display doctor name"""
        return obj.doctor.get_short_name()
    doctor_name.short_description = 'Doctor'

    def amount_charged_display(self, obj):
        """Display amount charged with color"""
        if obj.amount_charged == 0:
            return format_html('<span style="color: green;">FREE</span>')
        return format_html(
            '<span style="color: red;">{:,.2f} so\'m</span>',
            obj.amount_charged
        )
    amount_charged_display.short_description = 'Amount'

    def is_free_view(self, obj):
        """Display if it's a free view"""
        return obj.amount_charged == 0
    is_free_view.short_description = 'Free View'
    is_free_view.boolean = True


# @admin.register(BillingSettings)
class BillingSettingsAdmin(admin.ModelAdmin):
    """Billing Settings administration"""

    list_display = [
        'id', 'enable_billing', 'maintenance_mode', 'free_views_per_day',
        'min_wallet_topup_display', 'updated_at'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('General Settings', {
            'fields': ('enable_billing', 'maintenance_mode')
        }),
        ('Free Views', {
            'fields': ('free_views_per_day', 'free_views_for_new_users')
        }),
        ('Wallet Limits', {
            'fields': ('min_wallet_topup', 'max_wallet_balance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def min_wallet_topup_display(self, obj):
        """Display minimum topup amount"""
        return f"{obj.min_wallet_topup:,.2f} so'm"
    min_wallet_topup_display.short_description = 'Min Topup'

    def has_add_permission(self, request):
        """Only allow one billing settings instance"""
        return BillingSettings.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of billing settings"""
        return False


print("🚀 Payment admin interface loaded successfully!")
print("📊 Features: Comprehensive views, filters, actions, export functionality")
print("🔧 Admin tools: Gateway management, payment processing, refund handling")
print("💰 Wallet tools: Balance management, transaction tracking, billing rules")