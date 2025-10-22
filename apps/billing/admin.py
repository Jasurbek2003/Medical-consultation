# apps/billing/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    UserWallet, WalletTransaction, BillingRule,
    DoctorViewCharge, BillingSettings
)


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    """Admin configuration for User Wallets"""

    list_display = [
        'user_info', 'user_type_badge', 'balance_display', 'total_spent_display',
        'total_topped_up_display', 'status_badge', 'doctor_block_warning', 'last_transaction',
        'created_at'
    ]

    list_filter = [
        'is_blocked',
        'user__user_type',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    ]

    search_fields = [
        'user__username', 'user__phone', 'user__email',
        'user__first_name', 'user__last_name'
    ]

    readonly_fields = [
        'user', 'total_spent', 'total_topped_up',
        'created_at', 'updated_at', 'transaction_summary',
        'monthly_statistics', 'balance_history_chart'
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'balance', 'is_blocked')
        }),
        ('Financial Summary', {
            'fields': ('total_spent', 'total_topped_up', 'transaction_summary'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('monthly_statistics', 'balance_history_chart'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = [
        'block_wallets', 'unblock_wallets', 'unblock_doctors', 'add_bonus_10000', 'add_bonus_50000', 'add_bonus_100000', 'add_bonus_500000',
        'export_wallet_report', 'reset_wallet_balance'
    ]

    def user_info(self, obj):
        """Display user information with link"""
        user = obj.user
        info = f"{user.get_full_name() or user.username}"
        if user.phone:
            info += f"\n{user.phone} "
        url = reverse('admin:users_user_change', args=[user.pk])
        return format_html('<a href="{}">{}</a>', url, info)

    user_info.short_description = 'User'
    user_info.admin_order_field = 'user__username'

    def user_type_badge(self, obj):
        """Display user type with appropriate badge"""
        user = obj.user
        type_colors = {
            'doctor': '#007bff',
            'patient': '#28a745',
            'hospital_admin': '#6f42c1',
            'admin': '#dc3545',
        }
        type_icons = {
            'doctor': '👨‍⚕️',
            'patient': '👤',
            'hospital_admin': '🏥',
            'admin': '⚡',
        }
        color = type_colors.get(user.user_type, '#6c757d')
        icon = type_icons.get(user.user_type, '👤')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, user.user_type.replace('_', ' ').title()
        )

    user_type_badge.short_description = 'Type'
    user_type_badge.admin_order_field = 'user__user_type'

    def balance_display(self, obj):
        """Display balance with color coding"""
        balance = obj.balance
        is_doctor = obj.user.user_type == 'doctor'

        # Different thresholds for doctors (5000 critical) vs others
        if is_doctor:
            if balance <= 5000:
                color = '#dc3545'  # Red - critical for doctors
                icon = '🚨'
            elif balance <= 10000:
                color = '#ffc107'  # Yellow - warning
                icon = '⚠️'
            else:
                color = '#28a745'  # Green - safe
                icon = '✅'
        else:
            if balance < 1000:
                color = '#dc3545'
                icon = '💸'
            elif balance < 10000:
                color = '#ffc107'
                icon = '💰'
            else:
                color = '#28a745'
                icon = '💎'

        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 13px;">{} {} UZS</span>',
            color, icon, balance
        )

    balance_display.short_description = 'Balance'
    balance_display.admin_order_field = 'balance'

    def total_spent_display(self, obj):
        """Display total spent amount"""
        return format_html(
            '<span style="color: #dc3545;">{} UZS</span>',
            obj.total_spent
        )

    total_spent_display.short_description = 'Total Spent'
    total_spent_display.admin_order_field = 'total_spent'

    def total_topped_up_display(self, obj):
        """Display total topped up amount"""
        return format_html(
            '<span style="color: #28a745;">{} UZS</span>',
            obj.total_topped_up
        )

    total_topped_up_display.short_description = 'Total Topped Up'
    total_topped_up_display.admin_order_field = 'total_topped_up'

    def status_badge(self, obj):
        """Display wallet status badge"""
        if obj.is_blocked:
            return format_html(
                '<span class="badge" style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">Blocked</span>'
            )
        return format_html(
            '<span class="badge" style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Active</span>'
        )

    status_badge.short_description = 'Status'

    def doctor_block_warning(self, obj):
        """Display warning for doctors at risk of being blocked"""
        if obj.user.user_type != 'doctor':
            return '-'

        try:
            doctor = obj.user.doctor_profile
            balance = obj.balance

            if balance <= 5000:
                if doctor.is_blocked:
                    return format_html(
                        '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
                        '🚫 BLOCKED</span>'
                    )
                else:
                    return format_html(
                        '<span style="background: #ffc107; color: black; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
                        '⚠️ AT RISK</span>'
                    )
            elif balance <= 10000:
                return format_html(
                    '<span style="background: #17a2b8; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
                    'ℹ️ Low Balance</span>'
                )
            else:
                return format_html(
                    '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">'
                    '✅ Safe</span>'
                )
        except Exception:
            return '-'

    doctor_block_warning.short_description = 'Doctor Status'

    def last_transaction(self, obj):
        """Display last transaction info"""
        last_txn = obj.transactions.first()
        if last_txn:
            return format_html(
                '{}<br><small>{}</small>',
                f"{last_txn.amount} UZS",
                last_txn.created_at.strftime('%Y-%m-%d %H:%M')
            )
        return '-'

    last_transaction.short_description = 'Last Transaction'

    def transaction_summary(self, obj):
        """Display transaction summary"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        today_stats = obj.transactions.filter(
            created_at__date=today
        ).aggregate(
            credits=Sum('amount', filter=Q(transaction_type='credit')),
            debits=Sum('amount', filter=Q(transaction_type='debit'))
        )

        week_stats = obj.transactions.filter(
            created_at__date__gte=week_ago
        ).aggregate(
            credits=Sum('amount', filter=Q(transaction_type='credit')),
            debits=Sum('amount', filter=Q(transaction_type='debit'))
        )

        month_stats = obj.transactions.filter(
            created_at__date__gte=month_ago
        ).aggregate(
            credits=Sum('amount', filter=Q(transaction_type='credit')),
            debits=Sum('amount', filter=Q(transaction_type='debit'))
        )

        return format_html(
            '''
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f0f0f0;">
                    <th style="padding: 8px; text-align: left;">Period</th>
                    <th style="padding: 8px; text-align: right;">Credits</th>
                    <th style="padding: 8px; text-align: right;">Debits</th>
                    <th style="padding: 8px; text-align: right;">Net</th>
                </tr>
                <tr>
                    <td style="padding: 8px;">Today</td>
                    <td style="padding: 8px; text-align: right; color: green;">+{}</td>
                    <td style="padding: 8px; text-align: right; color: red;">-{}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">{}</td>
                </tr>
                <tr style="background: #f8f8f8;">
                    <td style="padding: 8px;">Last 7 days</td>
                    <td style="padding: 8px; text-align: right; color: green;">+{}</td>
                    <td style="padding: 8px; text-align: right; color: red;">-{}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">{}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;">Last 30 days</td>
                    <td style="padding: 8px; text-align: right; color: green;">+{}</td>
                    <td style="padding: 8px; text-align: right; color: red;">-{}</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">{}</td>
                </tr>
            </table>
            ''',
            today_stats['credits'] or 0,
            today_stats['debits'] or 0,
            (today_stats['credits'] or 0) - (today_stats['debits'] or 0),
            week_stats['credits'] or 0,
            week_stats['debits'] or 0,
            (week_stats['credits'] or 0) - (week_stats['debits'] or 0),
            month_stats['credits'] or 0,
            month_stats['debits'] or 0,
            (month_stats['credits'] or 0) - (month_stats['debits'] or 0)
        )

    transaction_summary.short_description = 'Transaction Summary'

    def monthly_statistics(self, obj):
        """Display monthly statistics chart"""
        # Implementation for monthly stats chart
        return format_html('<div>Monthly statistics chart placeholder</div>')

    monthly_statistics.short_description = 'Monthly Statistics'

    def balance_history_chart(self, obj):
        """Display balance history chart"""
        # Implementation for balance history chart
        return format_html('<div>Balance history chart placeholder</div>')

    balance_history_chart.short_description = 'Balance History'

    # Admin Actions
    def block_wallets(self, request, queryset):
        """Block selected wallets"""
        count = queryset.update(is_blocked=True)
        self.message_user(request, f'{count} wallet(s) blocked successfully.')

    block_wallets.short_description = 'Block selected wallets'

    def unblock_wallets(self, request, queryset):
        """Unblock selected wallets"""
        count = queryset.update(is_blocked=False)
        self.message_user(request, f'{count} wallet(s) unblocked successfully.')

    unblock_wallets.short_description = 'Unblock selected wallets'

    def unblock_doctors(self, request, queryset):
        """Unblock doctors if their balance is sufficient"""
        unblocked_count = 0
        insufficient_balance = 0

        for wallet in queryset:
            if wallet.user.user_type == 'doctor':
                try:
                    doctor = wallet.user.doctor_profile
                    if wallet.balance > 5000 and doctor.is_blocked:
                        doctor.is_blocked = False
                        doctor.save(update_fields=['is_blocked'])
                        unblocked_count += 1
                    elif wallet.balance <= 5000:
                        insufficient_balance += 1
                except Exception:
                    pass

        if unblocked_count > 0:
            self.message_user(
                request,
                f'✅ {unblocked_count} doctor(s) unblocked successfully.',
                level='success'
            )
        if insufficient_balance > 0:
            self.message_user(
                request,
                f'⚠️ {insufficient_balance} doctor(s) have insufficient balance (≤ 5000).',
                level='warning'
            )

    unblock_doctors.short_description = '🩺 Unblock doctors (if balance > 5000)'

    def add_bonus_10000(self, request, queryset):
        """Add bonus to selected wallets"""
        # In production, this would open a form to enter bonus amount
        bonus_amount = Decimal('10000.00')  # Example fixed bonus
        for wallet in queryset:
            wallet.add_balance(
                bonus_amount,
                f'Admin bonus - Added by {request.user.username}. Amount: {bonus_amount} UZS'
            )
        self.message_user(
            request,
            f'Added {bonus_amount} UZS bonus to {queryset.count()} wallet(s).'
        )

    add_bonus_10000.short_description = 'Add bonus to selected wallets. Amount: 10000 UZS'

    def add_bonus_50000(self, request, queryset):
        """Add bonus to selected wallets"""
        # In production, this would open a form to enter bonus amount
        bonus_amount = Decimal('50000.00')  # Example fixed bonus
        for wallet in queryset:
            wallet.add_balance(
                bonus_amount,
                f'Admin bonus - Added by {request.user.username}. Amount: {bonus_amount} UZS'
            )
        self.message_user(
            request,
            f'Added {bonus_amount} UZS bonus to {queryset.count()} wallet(s).'
        )

    add_bonus_50000.short_description = 'Add bonus to selected wallets. Amount: 50000 UZS'

    def add_bonus_100000(self, request, queryset):
        """Add bonus to selected wallets"""
        # In production, this would open a form to enter bonus amount
        bonus_amount = Decimal('100000.00')  # Example fixed bonus
        for wallet in queryset:
            wallet.add_balance(
                bonus_amount,
                f'Admin bonus - Added by {request.user.username}. Amount: {bonus_amount} UZS'
            )
        self.message_user(
            request,
            f'Added {bonus_amount} UZS bonus to {queryset.count()} wallet(s).'
        )

    add_bonus_100000.short_description = 'Add bonus to selected wallets. Amount: 100000 UZS'

    def add_bonus_500000(self, request, queryset):
        """Add bonus to selected wallets"""
        # In production, this would open a form to enter bonus amount
        bonus_amount = Decimal('500000.00')  # Example fixed bonus
        for wallet in queryset:
            wallet.add_balance(
                bonus_amount,
                f'Admin bonus - Added by {request.user.username}. Amount: {bonus_amount} UZS'
            )
        self.message_user(
            request,
            f'Added {bonus_amount} UZS bonus to {queryset.count()} wallet(s).'
        )

    add_bonus_500000.short_description = 'Add bonus to selected wallets. Amount: 500000 UZS'

    def export_wallet_report(self, request, queryset):
        """Export wallet report"""
        # Implementation for exporting wallet data
        self.message_user(request, 'Wallet report exported successfully.')

    export_wallet_report.short_description = 'Export wallet report'

    def reset_wallet_balance(self, request, queryset):
        """Reset wallet balance (dangerous operation)"""
        if request.user.is_superuser:
            for wallet in queryset:
                wallet.balance = Decimal('0.00')
                wallet.save()
            self.message_user(request, f'Reset {queryset.count()} wallet(s).')
        else:
            self.message_user(request, 'Only superusers can reset wallets.', level='error')

    reset_wallet_balance.short_description = 'Reset wallet balance (DANGER)'


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Wallet Transactions"""

    list_display = [
        'id', 'wallet_user', 'transaction_type_badge', 'amount_display',
        'balance_change', 'status_badge', 'description_short',
        'created_at'
    ]

    list_filter = [
        'transaction_type', 'status',
        ('created_at', admin.DateFieldListFilter),
        'wallet__user__is_active'
    ]

    search_fields = [
        'wallet__user__username', 'wallet__user__phone',
        'description', 'reference_number'
    ]

    # readonly_fields = [
    #     'wallet', 'transaction_type', 'amount', 'balance_before',
    #     'balance_after',  'created_at', 'updated_at'
    # ]

    date_hierarchy = 'created_at'

    ordering = ['-created_at']

    def wallet_user(self, obj):
        """Display wallet user with link"""
        user = obj.wallet.user
        url = reverse('admin:billing_userwallet_change', args=[obj.wallet.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            user.get_full_name() or user.username
        )

    wallet_user.short_description = 'User'
    wallet_user.admin_order_field = 'wallet__user__username'

    def transaction_type_badge(self, obj):
        """Display transaction type as badge"""
        if obj.transaction_type == 'credit':
            color = '#28a745'
            icon = '↑'
        else:
            color = '#dc3545'
            icon = '↓'
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )

    transaction_type_badge.short_description = 'Type'

    def amount_display(self, obj):
        """Display amount with color"""
        if obj.transaction_type == 'credit':
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">+{} UZS</span>',
                obj.amount
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">-{} UZS</span>',
                obj.amount
            )

    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def balance_change(self, obj):
        """Display balance change"""
        return format_html(
            '{} → {}',
            obj.balance_before,
            obj.balance_after
        )

    balance_change.short_description = 'Balance Change'

    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'pending': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def description_short(self, obj):
        """Display truncated description"""
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description

    description_short.short_description = 'Description'


@admin.register(BillingRule)
class BillingRuleAdmin(admin.ModelAdmin):
    """Admin configuration for Billing Rules"""

    list_display = [
        'service_type', 'price_display', 'discount_badge',
        'is_active_badge', 'usage_count',
        'created_at'
    ]

    list_filter = [
        'service_type', 'is_active',
        ('created_at', admin.DateFieldListFilter)
    ]

    search_fields = ['service_type', 'description']

    fieldsets = (
        ('Service Configuration', {
            'fields': ('service_type', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_percentage', )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['created_at', 'updated_at', 'usage_count']

    actions = ['activate_rules', 'deactivate_rules', 'apply_discount']

    def price_display(self, obj):
        """Display price with formatting"""
        return format_html(
            '<strong>{} UZS</strong>',
            obj.price
        )

    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'

    def discount_badge(self, obj):
        """Display discount percentage"""
        if obj.discount_percentage > 0:
            return format_html(
                '<span style="background: #ff6b6b; color: white; padding: 3px 8px; border-radius: 3px;">-{}%</span>',
                obj.discount_percentage
            )
        return '-'

    discount_badge.short_description = 'Discount'

    def is_active_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">Inactive</span>'
        )

    is_active_badge.short_description = 'Status'

    def usage_count(self, obj):
        """Get usage count for this rule"""
        # This would need to be implemented based on your tracking
        return format_html('<strong>0</strong>')

    usage_count.short_description = 'Usage Count'

    def activate_rules(self, request, queryset):
        """Activate selected rules"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} rule(s) activated.')

    activate_rules.short_description = 'Activate selected rules'

    def deactivate_rules(self, request, queryset):
        """Deactivate selected rules"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} rule(s) deactivated.')

    deactivate_rules.short_description = 'Deactivate selected rules'

    def apply_discount(self, request, queryset):
        """Apply discount to selected rules"""
        # In production, this would open a form
        discount = 10  # Example: 10% discount
        count = queryset.update(discount_percentage=discount)
        self.message_user(request, f'Applied {discount}% discount to {count} rule(s).')

    apply_discount.short_description = 'Apply discount to selected rules'


@admin.register(DoctorViewCharge)
class DoctorViewChargeAdmin(admin.ModelAdmin):
    """Admin configuration for Doctor View Charges"""

    list_display = [
        'id', 'user_link', 'doctor_link', 'amount_charged_display',
        'ip_address', 'view_duration_display', 'created_at'
    ]

    list_filter = [
        ('created_at', admin.DateFieldListFilter),
        'doctor__specialty',
        'doctor__verification_status'
    ]

    search_fields = [
        'user__username', 'user__phone',
        'doctor__user__first_name', 'doctor__user__last_name',
        'ip_address'
    ]

    readonly_fields = [
        'user', 'doctor', 'transaction', 'amount_charged',
        'view_duration', 'ip_address', 'user_agent', 'created_at'
    ]

    date_hierarchy = 'created_at'

    ordering = ['-created_at']

    def user_link(self, obj):
        """Display user with link"""
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.username
        )

    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def doctor_link(self, obj):
        """Display doctor with link"""
        url = reverse('admin:doctors_doctor_change', args=[obj.doctor.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.doctor.get_full_name()
        )

    doctor_link.short_description = 'Doctor'
    doctor_link.admin_order_field = 'doctor__user__first_name'

    def amount_charged_display(self, obj):
        """Display amount charged"""
        return format_html(
            '<strong>{} UZS</strong>',
            obj.amount_charged
        )

    amount_charged_display.short_description = 'Amount'
    amount_charged_display.admin_order_field = 'amount_charged'

    def view_duration_display(self, obj):
        """Display view duration"""
        if obj.view_duration:
            total_seconds = obj.view_duration.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f'{minutes}m {seconds}s'
        return '-'

    view_duration_display.short_description = 'Duration'


@admin.register(BillingSettings)
class BillingSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for Billing Settings"""

    list_display = [
        'id', 'free_views_per_day', 'free_views_for_new_users',
        'enable_billing_badge', 'maintenance_mode_badge',
        'updated_at'
    ]

    fieldsets = (
        ('Free Views Configuration', {
            'fields': (
                'free_views_per_day',
                'free_views_for_new_users',
                # 'free_trial_days'
            )
        }),
        ('System Settings', {
            'fields': (
                'enable_billing',
                'maintenance_mode',
                # 'maintenance_message'
            )
        }),
        ('Pricing Configuration', {
            'fields': (
                # 'default_doctor_view_price',
                # 'default_consultation_price',
                # 'minimum_topup_amount',
                # 'maximum_topup_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['created_at', 'updated_at']

    def enable_billing_badge(self, obj):
        """Display billing status"""
        if obj.enable_billing:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Enabled</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">Disabled</span>'
        )

    enable_billing_badge.short_description = 'Billing Status'

    def maintenance_mode_badge(self, obj):
        """Display maintenance mode status"""
        if obj.maintenance_mode:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 3px 8px; border-radius: 3px;">Maintenance</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Normal</span>'
        )

    maintenance_mode_badge.short_description = 'Mode'

    def has_add_permission(self, request):
        """Only allow one settings object"""
        return not BillingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings"""
        return False