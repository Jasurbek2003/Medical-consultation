"""
Custom OpenAPI schema extensions for better API documentation.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Custom authentication scheme for token authentication.
    Provides better documentation for token-based auth.
    """
    target_class = 'rest_framework.authentication.TokenAuthentication'
    name = 'tokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': (
                'Token-based authentication. '
                'Format: `Token <your-token>`. '
                'Obtain a token by calling the login endpoint.'
            )
        }
