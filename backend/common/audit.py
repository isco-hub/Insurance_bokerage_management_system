import logging

logger = logging.getLogger(__name__)


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(
    request,
    action,
    module,
    entity_type='',
    entity_id='',
    description='',
    metadata=None,
    user=None,
):
    from accounts.models import AuditLog

    actor = user if user is not None else getattr(request, 'user', None)
    if actor is not None and not getattr(actor, 'is_authenticated', False):
        actor = None
    try:
        AuditLog.objects.create(
            user=actor if actor and getattr(actor, 'pk', None) else None,
            user_email=getattr(actor, 'email', '') if actor else '',
            action=action,
            module=module,
            entity_type=entity_type or '',
            entity_id=str(entity_id or ''),
            description=description or '',
            metadata=metadata or {},
            ip_address=client_ip(request) or '',
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
    except Exception:  # pragma: no cover - audit must never break a request
        logger.exception('Failed to write audit log')
