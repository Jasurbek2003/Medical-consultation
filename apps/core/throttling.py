"""
Custom throttling classes for API rate limiting.

These throttle classes provide fine-grained control over API access rates
to prevent abuse and ensure fair usage across all users.
"""
from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class BurstRateThrottle(UserRateThrottle):
    """
    Throttle for burst requests - very short time window.
    Prevents rapid-fire requests from the same user.

    Default: 10 requests per minute
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle for sustained usage - longer time window.
    Prevents excessive API usage over time.

    Default: 100 requests per hour
    """
    scope = 'sustained'


class AnonBurstRateThrottle(AnonRateThrottle):
    """
    Throttle for anonymous users - burst requests.
    More restrictive than authenticated users.

    Default: 5 requests per minute
    """
    scope = 'anon_burst'


class AnonSustainedRateThrottle(AnonRateThrottle):
    """
    Throttle for anonymous users - sustained usage.
    More restrictive than authenticated users.

    Default: 30 requests per hour
    """
    scope = 'anon_sustained'


class ChatThrottle(SimpleRateThrottle):
    """
    Special throttle for chat/messaging endpoints.
    Allows higher rate but still prevents spam.

    Default: 20 messages per minute
    """
    scope = 'chat'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class AuthenticationThrottle(SimpleRateThrottle):
    """
    Throttle for authentication endpoints (login, register).
    Prevents brute force attacks and account enumeration.

    Default: 5 requests per minute, 20 per hour
    """
    scope = 'auth'

    def get_cache_key(self, request, view):
        # Use IP address for authentication throttling
        ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class PaymentThrottle(SimpleRateThrottle):
    """
    Throttle for payment endpoints.
    Very restrictive to prevent payment abuse.

    Default: 5 requests per minute, 10 per hour
    """
    scope = 'payment'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class SearchThrottle(SimpleRateThrottle):
    """
    Throttle for search endpoints.
    Prevents search scraping and excessive queries.

    Default: 30 requests per minute
    """
    scope = 'search'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class FileUploadThrottle(SimpleRateThrottle):
    """
    Throttle for file upload endpoints.
    Prevents storage abuse.

    Default: 10 uploads per hour
    """
    scope = 'upload'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class WebhookThrottle(SimpleRateThrottle):
    """
    Throttle for payment webhook endpoints (Click, Payme, etc).
    Very permissive but still provides DDoS protection.

    Default: 100 requests per minute
    """
    scope = 'webhook'

    def get_cache_key(self, request, view):
        # Use IP for webhooks since they're not authenticated
        ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
