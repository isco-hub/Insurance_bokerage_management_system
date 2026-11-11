from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.audit import log_action
from common.numbering import next_number
from common.viewsets import BaseModelViewSet
from finance.models import Commission, CommissionStatus, CreditDebitNote
from operations.models import (
    Endorsement,
    EndorsementStatus,
    InsurerQuote,
    MotorDetail,
    Policy,
    PolicyStatus,
    Quotation,
    QuoteResponseStatus,
    Renewal,
    RenewalStatus,
    Risk,
)
from operations.serializers import (
    EndorsementSerializer,
    InsurerQuoteSerializer,
    MotorDetailSerializer,
    PolicySerializer,
    PolicyWriteSerializer,
    QuotationSerializer,
    RenewalSerializer,
    RiskSerializer,
)
from operations.services import create_policy, money
from workspace.models import Approval, ApprovalStatus, ApprovalType


class RiskViewSet(BaseModelViewSet):
    module = 'risks'
    audit_entity = 'Risk'
    scope_branch = True
    branch_filter = 'client__branch'
    queryset = Risk.objects.select_related('client', 'created_by').prefetch_related(
        'motor_details'
    )
    serializer_class = RiskSerializer
    filterset_fields = ['client', 'status', 'category']
    search_fields = ['risk_number', 'description', 'location', 'client__name']
    ordering_fields = ['risk_number', 'created_at', 'status']
    ordering = ['-created_at']


class MotorDetailViewSet(BaseModelViewSet):
    module = 'motor'
    audit_entity = 'MotorDetail'
    scope_branch = True
    branch_filter = 'risk__client__branch'
    queryset = MotorDetail.objects.select_related('risk', 'risk__client').all()
    serializer_class = MotorDetailSerializer
    filterset_fields = ['risk']
    search_fields = [
        'registration_number',
        'chassis_number',
        'engine_number',
        'make',
        'model',
        'driver_name',
    ]
    ordering = ['registration_number']


_TERMINAL_QUOTATION_STATUSES = {'ACCEPTED', 'DECLINED', 'EXPIRED'}


class QuotationViewSet(BaseModelViewSet):
    module = 'quotations'
    audit_entity = 'Quotation'
    scope_branch = True
    queryset = Quotation.objects.select_related(
        'client',
        'product',
        'product__insurance_class',
        'risk',
        'broker',
        'branch',
        'selected_insurer',
    ).prefetch_related('insurer_quotes__insurer')
    serializer_class = QuotationSerializer
    filterset_fields = [
        'client',
        'product',
        'risk',
        'status',
        'branch',
        'broker',
        'selected_insurer',
    ]
    search_fields = ['quotation_number', 'client__name', 'notes']
    ordering_fields = ['quotation_number', 'created_at', 'total_premium', 'valid_to']
    ordering = ['-created_at']
    extra_permissions = {
        'select': 'quotations:edit',
        'accept': 'policies:create',
    }

    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in _TERMINAL_QUOTATION_STATUSES:
            return Response(
                {'statusCode': 400, 'message': 'Quotation can no longer be changed'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        insurer_id = request.data.get('insurer_id') or request.data.get('insurer')
        quote = quotation.insurer_quotes.filter(
            insurer_id=insurer_id, status=QuoteResponseStatus.RECEIVED
        ).first()
        if not quote:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'No received quotation from the selected insurer',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.selected_insurer = quote.insurer
        quotation.premium = quote.premium
        quotation.taxes = quote.taxes
        quotation.total_premium = money(quote.premium) + money(quote.taxes)
        quotation.status = 'SELECTED'
        quotation.save(
            update_fields=[
                'selected_insurer',
                'premium',
                'taxes',
                'total_premium',
                'status',
                'updated_at',
            ]
        )
        log_action(
            request,
            'UPDATE',
            'quotations',
            'Quotation',
            quotation.id,
            f'Selected insurer {quote.insurer.name}',
        )
        return Response(
            {
                'data': QuotationSerializer(
                    quotation, context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status == 'ACCEPTED':
            return Response(
                {'statusCode': 400, 'message': 'Quotation has already been accepted'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quotation.status == 'DECLINED':
            return Response(
                {'statusCode': 400, 'message': 'Quotation was declined'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quotation.valid_to < timezone.localdate():
            quotation.status = 'EXPIRED'
            quotation.save(update_fields=['status', 'updated_at'])
            return Response(
                {'statusCode': 400, 'message': 'Quotation validity has expired'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not quotation.selected_insurer_id:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Select an insurer quotation before accepting',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        threshold = Decimal(str(settings.HIGH_VALUE_QUOTE_THRESHOLD))
        if quotation.total_premium >= threshold:
            approved = Approval.objects.filter(
                type=ApprovalType.QUOTATION,
                entity_type='Quotation',
                entity_id=str(quotation.id),
                status=ApprovalStatus.APPROVED,
            ).exists()
            if not approved:
                pending = Approval.objects.filter(
                    type=ApprovalType.QUOTATION,
                    entity_type='Quotation',
                    entity_id=str(quotation.id),
                    status=ApprovalStatus.PENDING,
                ).exists()
                if not pending:
                    Approval.objects.create(
                        type=ApprovalType.QUOTATION,
                        entity_type='Quotation',
                        entity_id=str(quotation.id),
                        amount=quotation.total_premium,
                        requested_by=request.user,
                        status=ApprovalStatus.PENDING,
                    )
                return Response(
                    {
                        'statusCode': 400,
                        'message': (
                            'This quotation exceeds the approval threshold and '
                            'requires management approval before acceptance.'
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data = {
            'quotation': quotation,
            'start_date': request.data.get('start_date'),
            'end_date': request.data.get('end_date'),
            'payment_frequency': request.data.get('payment_frequency'),
            'notes': request.data.get('notes'),
        }
        try:
            policy = create_policy(data, request.user, quotation)
        except ValueError as exc:
            return Response(
                {'statusCode': 400, 'message': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_action(
            request,
            'CREATE',
            'policies',
            'Policy',
            policy.id,
            f'Policy created from quotation {quotation.quotation_number}',
        )
        log_action(
            request,
            'APPROVE',
            'quotations',
            'Quotation',
            quotation.id,
            f'Quotation {quotation.quotation_number} accepted',
        )
        return Response(
            {'data': PolicySerializer(policy, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )


class InsurerQuoteViewSet(BaseModelViewSet):
    module = 'quotations'
    audit_entity = 'InsurerQuote'
    queryset = InsurerQuote.objects.select_related('quotation', 'insurer').all()
    serializer_class = InsurerQuoteSerializer
    filterset_fields = ['quotation', 'insurer', 'status']
    ordering_fields = ['premium', 'received_at']
    ordering = ['premium']


class PolicyViewSet(BaseModelViewSet):
    module = 'policies'
    audit_entity = 'Policy'
    scope_branch = True
    queryset = Policy.objects.select_related(
        'client',
        'product',
        'product__insurance_class',
        'insurer',
        'branch',
        'broker',
        'quotation',
        'created_by',
    ).prefetch_related('premiums', 'claims')
    filterset_fields = [
        'client',
        'insurer',
        'product',
        'status',
        'branch',
        'broker',
    ]
    search_fields = [
        'policy_number',
        'client__name',
        'insurer__name',
        'product__name',
    ]
    ordering_fields = ['policy_number', 'created_at', 'end_date', 'total_premium']
    ordering = ['-created_at']
    extra_permissions = {'cancel': 'policies:edit'}

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return PolicyWriteSerializer
        return PolicySerializer

    def create(self, request, *args, **kwargs):
        serializer = PolicyWriteSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            policy = create_policy(serializer.validated_data, request.user)
        except ValueError as exc:
            return Response(
                {'statusCode': 400, 'message': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_action(
            request,
            'CREATE',
            'policies',
            'Policy',
            policy.id,
            f'Policy {policy.policy_number} created',
        )
        return Response(
            {'data': PolicySerializer(policy, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        policy = self.get_object()
        if policy.status in (PolicyStatus.CANCELLED, PolicyStatus.EXPIRED, PolicyStatus.LAPSED):
            return Response(
                {'statusCode': 400, 'message': f'Policy is already {policy.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        effective = request.data.get('effective_date') or timezone.localdate()
        if isinstance(effective, str):
            try:
                effective = date.fromisoformat(effective)
            except ValueError:
                return Response(
                    {'statusCode': 400, 'message': 'Invalid effective date'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'statusCode': 400, 'message': 'Cancellation reason is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            policy.status = PolicyStatus.CANCELLED
            policy.cancelled_at = timezone.now()
            policy.cancellation_effective_date = effective
            policy.cancellation_reason = reason
            policy.save(
                update_fields=[
                    'status',
                    'cancelled_at',
                    'cancellation_effective_date',
                    'cancellation_reason',
                    'updated_at',
                ]
            )
            policy.renewals.filter(
                status__in=[
                    RenewalStatus.UPCOMING,
                    RenewalStatus.DUE,
                    RenewalStatus.QUOTED,
                ]
            ).update(status=RenewalStatus.LAPSED, updated_at=timezone.now())
            Commission.objects.filter(
                policy=policy, status=CommissionStatus.PENDING
            ).update(status=CommissionStatus.CANCELLED, updated_at=timezone.now())
        log_action(
            request,
            'UPDATE',
            'policies',
            'Policy',
            policy.id,
            f'Policy {policy.policy_number} cancelled: {reason}',
        )
        return Response(
            {'data': PolicySerializer(policy, context={'request': request}).data}
        )


class EndorsementViewSet(BaseModelViewSet):
    module = 'endorsements'
    audit_entity = 'Endorsement'
    scope_branch = True
    branch_filter = 'policy__branch'
    queryset = Endorsement.objects.select_related(
        'policy',
        'policy__client',
        'policy__insurer',
        'requested_by',
        'approved_by',
    )
    serializer_class = EndorsementSerializer
    filterset_fields = ['policy', 'status', 'type']
    search_fields = ['endorsement_number', 'description', 'policy__policy_number']
    ordering = ['-created_at']
    extra_permissions = {'decide': 'endorsements:approve'}

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        endorsement = self.get_object()
        if endorsement.status != EndorsementStatus.PENDING_APPROVAL:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Only endorsements in Pending Approval state can be decided',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        decision = (request.data.get('status') or '').upper()
        if decision not in (EndorsementStatus.APPROVED, EndorsementStatus.REJECTED):
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Decision must be APPROVED or REJECTED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if endorsement.requested_by_id == request.user.id:
            return Response(
                {
                    'statusCode': 403,
                    'message': 'You cannot approve your own endorsement request',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        with transaction.atomic():
            endorsement.status = decision
            endorsement.approved_by = request.user
            endorsement.approved_at = timezone.now()
            endorsement.save(
                update_fields=['status', 'approved_by', 'approved_at', 'updated_at']
            )
            if (
                decision == EndorsementStatus.APPROVED
                and endorsement.premium_adjustment
            ):
                adjustment = money(endorsement.premium_adjustment)
                if adjustment != 0:
                    note_type = 'DEBIT' if adjustment > 0 else 'CREDIT'
                    prefix = 'DBN' if adjustment > 0 else 'CRN'
                    CreditDebitNote.objects.create(
                        note_number=next_number(
                            CreditDebitNote, 'note_number', prefix
                        ),
                        note_type=note_type,
                        client=endorsement.policy.client,
                        policy=endorsement.policy,
                        amount=abs(adjustment),
                        reason=f'Endorsement {endorsement.endorsement_number}',
                        status='ISSUED',
                        issue_date=timezone.localdate(),
                        created_by=request.user,
                    )
        log_action(
            request,
            'APPROVE' if decision == EndorsementStatus.APPROVED else 'REJECT',
            'endorsements',
            'Endorsement',
            endorsement.id,
            f'Endorsement {endorsement.endorsement_number} {decision.lower()}',
        )
        return Response(
            {
                'data': EndorsementSerializer(
                    endorsement, context={'request': request}
                ).data
            }
        )


class RenewalViewSet(BaseModelViewSet):
    module = 'renewals'
    audit_entity = 'Renewal'
    scope_branch = True
    branch_filter = 'policy__branch'
    queryset = Renewal.objects.select_related(
        'policy',
        'policy__client',
        'policy__insurer',
        'policy__product',
        'handled_by',
        'renewal_quotation',
    )
    serializer_class = RenewalSerializer
    filterset_fields = ['policy', 'status', 'stage_days', 'handled_by']
    search_fields = ['policy__policy_number', 'policy__client__name', 'notes']
    ordering_fields = ['due_date', 'status']
    ordering = ['due_date']

    @action(detail=True, methods=['post'])
    def outcome(self, request, pk=None):
        renewal = self.get_object()
        if renewal.status in (RenewalStatus.WON, RenewalStatus.LOST, RenewalStatus.LAPSED):
            return Response(
                {'statusCode': 400, 'message': f'Renewal is already {renewal.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        outcome = (request.data.get('status') or '').upper()
        if outcome not in (
            RenewalStatus.WON,
            RenewalStatus.LOST,
            RenewalStatus.LAPSED,
        ):
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Outcome must be WON, LOST or LAPSED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        renewal.status = outcome
        if outcome == RenewalStatus.WON:
            renewal.won_at = timezone.now()
        else:
            lost_reason = (request.data.get('lost_reason') or '').strip()
            if outcome == RenewalStatus.LOST and not lost_reason:
                return Response(
                    {'statusCode': 400, 'message': 'A lost reason is required when marking a renewal as lost'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            renewal.lost_at = timezone.now()
            renewal.lost_reason = lost_reason
        if request.data.get('notes'):
            renewal.notes = request.data['notes']
        renewal.save()
        log_action(
            request,
            'UPDATE',
            'renewals',
            'Renewal',
            renewal.id,
            f'Renewal marked {outcome}',
        )
        return Response(
            {'data': RenewalSerializer(renewal, context={'request': request}).data}
        )
# 2026-11-11T15:06:08Z expired quotation
# 2026-11-11T15:06:08Z double issuance
