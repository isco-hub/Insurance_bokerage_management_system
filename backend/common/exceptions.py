from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            detail = exc.message_dict
        else:
            detail = {'detail': exc.messages}
        return Response(
            {'statusCode': 400, 'message': 'Validation failed', 'details': detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {
                'statusCode': 409,
                'message': 'The operation conflicts with existing records.',
            },
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        message = detail
        if isinstance(detail, dict) and 'detail' in detail:
            message = detail['detail']
        elif isinstance(detail, list):
            message = detail[0] if detail else 'Request failed'
        elif isinstance(detail, dict):
            first = next(iter(detail.values()), None)
            if isinstance(first, list) and first:
                message = f'{next(iter(detail.keys()))}: {first[0]}'
        response.data = {
            'statusCode': response.status_code,
            'message': message,
            'details': detail,
        }
    return response
# 2026-11-11T15:06:11Z exception handler
