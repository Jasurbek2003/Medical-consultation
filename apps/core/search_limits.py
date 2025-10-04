"""
Search limit enforcement utilities.

These utilities help enforce daily search limits for unauthenticated users
viewing doctors and hospitals.
"""
from rest_framework.exceptions import Throttled
from apps.core.models import SearchLog
from apps.core.utils import get_client_ip


def check_search_limit(request, entity_type, entity, action='view'):
    """
    Check if the user has exceeded the daily search limit for this entity.

    Args:
        request: Django request object
        entity_type: 'doctor' or 'hospital'
        entity: Doctor or Hospital instance
        action: Type of action (view, search, detail)

    Returns:
        bool: True if allowed, raises Throttled exception if limit exceeded

    Raises:
        Throttled: If the daily limit has been exceeded
    """
    # Authenticated users bypass limits
    if request.user.is_authenticated:
        # Still log the search for statistics
        SearchLog.log_search(entity_type, entity.id, request, action)
        return True

    # Get the limit from the entity
    limit = entity.daily_search_limit

    # If limit is 0, unlimited access
    if limit == 0:
        # Still log the search for statistics
        SearchLog.log_search(entity_type, entity.id, request, action)
        return True

    # Check if limit exceeded
    ip_address = get_client_ip(request)
    if SearchLog.check_limit_exceeded(entity_type, entity.id, limit, ip_address):
        # Limit exceeded - raise throttled exception
        raise Throttled(
            detail=f"Daily search limit ({limit}) exceeded for this {entity_type}. "
                   f"Please try again tomorrow or sign in for unlimited access.",
            wait=None  # Wait until tomorrow
        )

    # Limit not exceeded - log the search and allow
    SearchLog.log_search(entity_type, entity.id, request, action)
    return True


def get_search_stats(entity_type, entity_id, days=7):
    """
    Get search statistics for a doctor or hospital.

    Args:
        entity_type: 'doctor' or 'hospital'
        entity_id: ID of the doctor or hospital
        days: Number of days to look back (default 7)

    Returns:
        dict: Statistics including total searches, unique IPs, etc.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count

    start_date = (timezone.now() - timedelta(days=days)).date()

    logs = SearchLog.objects.filter(
        entity_type=entity_type,
        entity_id=entity_id,
        search_date__gte=start_date
    )

    return {
        'total_searches': logs.count(),
        'unique_ips': logs.values('ip_address').distinct().count(),
        'authenticated_searches': logs.filter(user__isnull=False).count(),
        'unauthenticated_searches': logs.filter(user__isnull=True).count(),
        'by_date': list(
            logs.values('search_date')
            .annotate(count=Count('id'))
            .order_by('search_date')
        ),
        'period_days': days
    }


def get_remaining_searches(request, entity_type, entity):
    """
    Get the number of remaining searches for this entity today.

    Args:
        request: Django request object
        entity_type: 'doctor' or 'hospital'
        entity: Doctor or Hospital instance

    Returns:
        dict: Information about remaining searches
    """
    # Authenticated users have unlimited access
    if request.user.is_authenticated:
        return {
            'limit': None,
            'used': 0,
            'remaining': 'unlimited',
            'unlimited': True
        }

    limit = entity.daily_search_limit

    # If limit is 0, unlimited
    if limit == 0:
        return {
            'limit': 0,
            'used': 0,
            'remaining': 'unlimited',
            'unlimited': True
        }

    # Get usage for this IP today
    ip_address = get_client_ip(request)
    used = SearchLog.get_daily_count(entity_type, entity.id, ip_address)
    remaining = max(0, limit - used)

    return {
        'limit': limit,
        'used': used,
        'remaining': remaining,
        'unlimited': False,
        'exceeded': used >= limit
    }


def filter_by_search_limit(request, queryset, entity_type):
    """
    Filter a queryset of doctors or hospitals to exclude those where limit is exceeded.

    This is useful for search results where you want to hide entities that the user
    has already viewed too many times today.

    Args:
        request: Django request object
        queryset: QuerySet of Doctor or Hospital objects
        entity_type: 'doctor' or 'hospital'

    Returns:
        QuerySet: Filtered queryset
    """
    # Authenticated users see everything
    if request.user.is_authenticated:
        return queryset

    ip_address = get_client_ip(request)

    # Filter out entities where limit is exceeded
    allowed_ids = []
    for entity in queryset:
        if entity.daily_search_limit == 0:
            # Unlimited
            allowed_ids.append(entity.id)
        elif not SearchLog.check_limit_exceeded(
            entity_type, entity.id, entity.daily_search_limit, ip_address
        ):
            # Limit not exceeded
            allowed_ids.append(entity.id)

    return queryset.filter(id__in=allowed_ids)
