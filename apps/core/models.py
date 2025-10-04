"""
Core models for tracking and monitoring system-wide activities.
"""
from django.db import models
from django.utils import timezone
from datetime import date


class SearchLog(models.Model):
    """
    Tracks searches/views of doctors and hospitals by unauthenticated users.
    Used to enforce daily search limits set by doctors and hospitals.
    """
    ENTITY_TYPES = [
        ('doctor', 'Doctor'),
        ('hospital', 'Hospital'),
    ]

    # What was searched
    entity_type = models.CharField(
        max_length=10,
        choices=ENTITY_TYPES,
        verbose_name="Entity Type"
    )
    entity_id = models.PositiveIntegerField(
        verbose_name="Entity ID",
        help_text="ID of the doctor or hospital"
    )

    # Who searched
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_logs',
        verbose_name="User",
        help_text="User who performed the search (null for unauthenticated)"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="IP Address"
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="User Agent"
    )

    # When
    searched_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Searched At"
    )
    search_date = models.DateField(
        default=date.today,
        verbose_name="Search Date",
        help_text="Date of search for daily limit tracking",
        db_index=True
    )

    # Metadata
    action = models.CharField(
        max_length=20,
        default='view',
        verbose_name="Action",
        help_text="Type of action: view, search, detail"
    )

    class Meta:
        verbose_name = "Search Log"
        verbose_name_plural = "Search Logs"
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', 'search_date']),
            models.Index(fields=['ip_address', 'search_date']),
            models.Index(fields=['user', 'search_date']),
        ]

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} by {self.ip_address} on {self.search_date}"

    @classmethod
    def get_daily_count(cls, entity_type, entity_id, ip_address, today=None):
        """
        Get the number of times this IP has searched for this entity today.

        Args:
            entity_type: 'doctor' or 'hospital'
            entity_id: ID of the doctor or hospital
            ip_address: IP address to check
            today: Date to check (defaults to today)

        Returns:
            int: Count of searches today
        """
        if today is None:
            today = date.today()

        return cls.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            search_date=today
        ).count()

    @classmethod
    def log_search(cls, entity_type, entity_id, request, action='view'):
        """
        Log a search/view for a doctor or hospital.

        Args:
            entity_type: 'doctor' or 'hospital'
            entity_id: ID of the doctor or hospital
            request: Django request object
            action: Type of action (view, search, detail)

        Returns:
            SearchLog: Created log entry
        """
        from apps.core.utils import get_client_ip, get_user_agent

        return cls.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            action=action,
            search_date=date.today()
        )

    @classmethod
    def check_limit_exceeded(cls, entity_type, entity_id, limit, ip_address, today=None):
        """
        Check if the daily search limit has been exceeded.

        Args:
            entity_type: 'doctor' or 'hospital'
            entity_id: ID of the doctor or hospital
            limit: Daily limit (0 means unlimited)
            ip_address: IP address to check
            today: Date to check (defaults to today)

        Returns:
            bool: True if limit exceeded, False otherwise
        """
        if limit == 0:
            return False  # Unlimited

        count = cls.get_daily_count(entity_type, entity_id, ip_address, today)
        return count >= limit
