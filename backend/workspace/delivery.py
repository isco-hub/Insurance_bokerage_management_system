import json
from urllib import error as urlerror
from urllib import request as urlrequest

from django.conf import settings
from django.core.mail import send_mail


def deliver_communication(communication):
    """Deliver a communication through its configured channel.

    Returns ``(delivered, error)`` and never raises for expected delivery
    failures, so callers can persist a failed status consistently.
    """

    if communication.channel == 'EMAIL':
        recipient = communication.client.email if communication.client else ''
        if not recipient:
            return False, 'The client does not have an email address'
        send_mail(
            communication.subject or 'Message from IBMS',
            communication.message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        return True, ''
    if communication.channel == 'SMS':
        recipient = communication.client.phone if communication.client else ''
        if not recipient:
            return False, 'The client does not have a phone number'
        gateway = getattr(settings, 'SMS_GATEWAY_URL', '')
        if not gateway:
            return False, 'SMS gateway is not configured'
        payload = json.dumps(
            {
                'to': recipient,
                'message': communication.message,
                'sender': getattr(settings, 'SMS_SENDER_ID', 'IBMS'),
            }
        ).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        token = getattr(settings, 'SMS_GATEWAY_TOKEN', '')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        try:
            with urlrequest.urlopen(
                urlrequest.Request(
                    gateway, data=payload, headers=headers, method='POST'
                ),
                timeout=15,
            ) as response:
                if not 200 <= response.status < 300:
                    return False, f'SMS gateway returned {response.status}'
        except (urlerror.URLError, OSError) as exc:
            return False, f'SMS gateway error: {exc}'
        return True, ''
    return False, 'Only email and SMS can be sent electronically'
