from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from claims.models import Claim, ClaimStatus
from claims.serializers import ClaimSerializer
from common.audit import log_action
from common.viewsets import BaseModelViewSet


class ClaimViewSet(BaseModelViewSet):
    module = 'claims'
    audit_entity = 'Claim'
    scope_branch = True
    branch_filter = 'policy__branch'
    queryset = Claim.objects.select_related(
        'policy',
        'policy__insurer',
        'policy__product',
        'client',
        'handled_by',
    )
    serializer_class = ClaimSerializer
    filterset_fields = ['policy', 'client', 'status', 'handled_by']
    search_fields = [
        'claim_number',
        'cause',
        'client__name',
        'policy__policy_number',
    ]
    ordering_fields = ['reported_at', 'date_of_loss', 'reserve_amount', 'status']
    ordering = ['-reported_at']
    extra_permissions = {'settle': 'claims:approve'}

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        claim = self.get_object()
        if claim.status in (ClaimStatus.SETTLED, ClaimStatus.REJECTED, ClaimStatus.CLOSED):
            return Response(
                {'statusCode': 400, 'message': f'Claim is already {claim.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paid = request.data.get('paid_amount')
        recovered = request.data.get('recovered_amount')
        if paid is not None:
            try:
                paid = Decimal(str(paid))
            except Exception:
                return Response(
                    {'statusCode': 400, 'message': 'Invalid paid amount'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if paid < 0:
                return Response(
                    {'statusCode': 400, 'message': 'Paid amount cannot be negative'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if claim.reserve_amount and paid > claim.reserve_amount:
                return Response(
                    {'statusCode': 400, 'message': f'Paid amount ({paid}) exceeds the reserve amount ({claim.reserve_amount}). Increase the reserve first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            claim.paid_amount = paid
        if recovered is not None:
            claim.recovered_amount = recovered
        claim.status = ClaimStatus.SETTLED
        claim.settled_at = timezone.now()
        if request.data.get('notes'):
            claim.notes = request.data['notes']
        claim.save()
        log_action(
            request,
            'APPROVE',
            'claims',
            'Claim',
            claim.id,
            f'Claim {claim.claim_number} settled',
        )
        return Response(
            {'data': ClaimSerializer(claim, context={'request': request}).data}
        )
# 2026-11-11T15:06:09Z claim registration
# 2026-11-11T15:06:09Z role restriction
