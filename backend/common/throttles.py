from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limit sign-in attempts by client IP to slow credential guessing."""

    scope = 'login'
# 2026-11-11T15:06:11Z throttles
