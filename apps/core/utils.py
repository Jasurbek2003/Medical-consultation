"""
Centralized utility functions for the Medical Consultation platform.
"""
import ipaddress
import re


def is_valid_ip(ip: str) -> bool:
    """
    Validate IP address format (both IPv4 and IPv6).

    Args:
        ip: IP address string to validate

    Returns:
        bool: True if valid IP address, False otherwise
    """
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

    if re.match(ipv4_pattern, ip):
        # Check if all octets are valid (0-255)
        return all(0 <= int(octet) <= 255 for octet in ip.split('.'))
    elif re.match(ipv6_pattern, ip):
        return True
    return False


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is in private range.

    Args:
        ip: IP address string to check

    Returns:
        bool: True if private IP, False otherwise
    """
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def get_client_ip(request) -> str:
    """
    Get client IP address from request with enhanced security.
    Handles multiple proxy scenarios and validates IP addresses.

    This is the centralized IP detection utility that should be used
    across the entire application for consistency and security.

    Args:
        request: Django/DRF request object

    Returns:
        str: Client IP address

    Priority order:
        1. HTTP_X_FORWARDED_FOR (most common proxy header)
        2. HTTP_X_REAL_IP (nginx)
        3. HTTP_CF_CONNECTING_IP (Cloudflare)
        4. HTTP_X_FORWARDED
        5. HTTP_FORWARDED_FOR
        6. HTTP_FORWARDED
        7. REMOTE_ADDR (fallback)
    """
    # List of headers to check in order of preference
    ip_headers = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_CF_CONNECTING_IP',  # Cloudflare
        'HTTP_X_FORWARDED',
        'HTTP_FORWARDED_FOR',
        'HTTP_FORWARDED',
        'REMOTE_ADDR'
    ]

    for header in ip_headers:
        ip_list = request.META.get(header)
        if ip_list:
            # Handle comma-separated IPs (first one is usually the original client)
            ip = ip_list.split(',')[0].strip()

            # Basic IP validation and private IP filtering
            if is_valid_ip(ip) and not is_private_ip(ip):
                return ip

    # Fallback to REMOTE_ADDR even if it might be private
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def get_user_agent(request) -> str:
    """
    Get user agent string from request.

    Args:
        request: Django/DRF request object

    Returns:
        str: User agent string
    """
    return request.META.get('HTTP_USER_AGENT', 'Unknown')


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]

    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)

    # Limit length
    max_length = 100
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]

    return filename
