from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.audit import log_action
from common.numbering import next_number
from common.viewsets import BaseModelViewSet
from finance.models import (
    Commission,
    CommissionStatus,
    CreditDebitNote,
    Invoice,
    Payment,
    Premium,
    Remittance,
    RemittanceStatus,
)
from finance.serializers import (
    CommissionSerializer,
    CreditDebitNoteSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    PremiumSerializer,
    RemittanceSerializer,
)
from finance.services import reverse_payment_allocation
from operations.models import Policy


class PremiumViewSet(BaseModelViewSet):
    module = 'premiums'
    audit_entity = 'Premium'
    scope_branch = True
    branch_filter = 'policy__branch'
    queryset = Premium.objects.select_related(
        'policy', 'policy__client', 'policy__insurer'
    )
    serializer_class = PremiumSerializer
    filterset_fields = ['policy', 'status']
    search_fields = ['policy__policy_number', 'policy__client__name']
    ordering_fields = ['due_date', 'status', 'amount_due']
    ordering = ['due_date']


class InvoiceViewSet(BaseModelViewSet):
    module = 'invoices'
    audit_entity = 'Invoice'
    scope_branch = True
    branch_filter = 'client__branch'
    queryset = Invoice.objects.select_related('client', 'policy', 'created_by')
    serializer_class = InvoiceSerializer
    filterset_fields = ['client', 'policy', 'status']
    search_fields = ['invoice_number', 'client__name', 'policy__policy_number']
    ordering_fields = ['issue_date', 'due_date', 'total', 'status']
    ordering = ['-issue_date']


class PaymentViewSet(BaseModelViewSet):
    module = 'payments'
    audit_entity = 'Payment'
    scope_branch = True
    branch_filter = 'client__branch'
    queryset = Payment.objects.select_related(
        'client', 'policy', 'invoice', 'received_by'
    )
    serializer_class = PaymentSerializer
    filterset_fields = ['client', 'policy', 'invoice', 'method', 'status']
    search_fields = ['receipt_number', 'reference', 'client__name']
    ordering_fields = ['paid_at', 'amount', 'created_at']
    ordering = ['-paid_at']
    extra_permissions = {'refund': 'payments:edit'}

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        payment = self.get_object()
        try:
            amount = Decimal(str(request.data.get('amount') or '0'))
        except Exception:
            return Response(
                {'statusCode': 400, 'message': 'Invalid refund amount'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if amount <= 0:
            return Response(
                {'statusCode': 400, 'message': 'Refund amount must be greater than zero'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        available = payment.amount - payment.refunded_amount
        if amount > available:
            return Response(
                {
                    'statusCode': 400,
                    'message': f'Refund exceeds the refundable balance of {available}',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'statusCode': 400, 'message': 'Refund reason is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payment.status == 'CONFIRMED':
            reverse_payment_allocation(payment, amount)
        payment.refunded_amount += amount
        payment.refunded_at = timezone.now()
        payment.refund_reason = reason
        if payment.refunded_amount >= payment.amount:
            payment.status = 'REVERSED'
        payment.save(
            update_fields=[
                'refunded_amount',
                'refunded_at',
                'refund_reason',
                'status',
                'updated_at',
            ]
        )
        log_action(
            request,
            'UPDATE',
            'payments',
            'Payment',
            payment.id,
            f'Refund of {amount} recorded: {reason}',
        )
        return Response(
            {'data': PaymentSerializer(payment, context={'request': request}).data}
        )


class CreditDebitNoteViewSet(BaseModelViewSet):
    module = 'notes'
    audit_entity = 'CreditDebitNote'
    scope_branch = True
    branch_filter = 'client__branch'
    queryset = CreditDebitNote.objects.select_related(
        'client', 'policy', 'created_by'
    )
    serializer_class = CreditDebitNoteSerializer
    filterset_fields = ['client', 'policy', 'note_type', 'status']
    search_fields = ['note_number', 'reason', 'client__name']
    ordering_fields = ['issue_date', 'amount', 'status']
    ordering = ['-issue_date']


class CommissionViewSet(BaseModelViewSet):
    module = 'commissions'
    audit_entity = 'Commission'
    scope_branch = True
    branch_filter = 'policy__branch'
    queryset = Commission.objects.select_related(
        'policy', 'policy__client', 'insurer', 'broker'
    )
    serializer_class = CommissionSerializer
    filterset_fields = ['policy', 'insurer', 'broker', 'status']
    search_fields = ['policy__policy_number', 'policy__client__name', 'insurer__name']
    ordering_fields = ['amount', 'rate', 'earned_at', 'status']
    ordering = ['-created_at']
    extra_permissions = {
        'mark_paid': 'commissions:edit',
        'reconcile': 'commissions:approve',
    }

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        commission = self.get_object()
        if commission.status in (CommissionStatus.PAID, CommissionStatus.RECONCILED, CommissionStatus.CANCELLED):
            return Response(
                {'statusCode': 400, 'message': f'Commission is already {commission.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        commission.status = CommissionStatus.PAID
        commission.paid_at = timezone.now()
        commission.save(update_fields=['status', 'paid_at', 'updated_at'])
        log_action(
            request,
            'UPDATE',
            'commissions',
            'Commission',
            commission.id,
            'Commission marked paid',
        )
        return Response(
            {
                'data': CommissionSerializer(
                    commission, context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        commission = self.get_object()
        if commission.status == CommissionStatus.CANCELLED:
            return Response(
                {'statusCode': 400, 'message': 'Cannot reconcile a cancelled commission'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if commission.status == CommissionStatus.RECONCILED:
            return Response(
                {'statusCode': 400, 'message': 'Commission is already reconciled'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if commission.status == CommissionStatus.PENDING:
            return Response(
                {'statusCode': 400, 'message': 'Commission must be marked as earned or paid before reconciliation'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        commission.status = CommissionStatus.RECONCILED
        if not commission.paid_at:
            commission.paid_at = timezone.now()
        commission.save(update_fields=['status', 'paid_at', 'updated_at'])
        log_action(
            request,
            'APPROVE',
            'commissions',
            'Commission',
            commission.id,
            'Commission reconciled',
        )
        return Response(
            {
                'data': CommissionSerializer(
                    commission, context={'request': request}
                ).data
            }
        )


class RemittanceViewSet(BaseModelViewSet):
    module = 'remittances'
    audit_entity = 'Remittance'
    queryset = Remittance.objects.select_related(
        'insurer', 'branch', 'created_by'
    )
    serializer_class = RemittanceSerializer
    filterset_fields = ['insurer', 'branch', 'status']
    search_fields = ['remittance_number', 'reference', 'insurer__name']
    ordering_fields = ['period_to', 'net_amount', 'status']
    ordering = ['-period_to']
    extra_permissions = {
        'mark_paid': 'remittances:edit',
        'reconcile': 'remittances:approve',
        'generate': 'remittances:create',
    }

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        remittance = self.get_object()
        if remittance.status in (RemittanceStatus.PAID, RemittanceStatus.RECONCILED):
            return Response(
                {'statusCode': 400, 'message': f'Remittance is already {remittance.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        remittance.status = RemittanceStatus.PAID
        remittance.paid_at = timezone.now()
        remittance.reference = (
            request.data.get('reference')
            or request.data.get('bank_reference')
            or remittance.reference
        )
        if request.data.get('bank_reference'):
            remittance.bank_reference = request.data['bank_reference']
        remittance.save(
            update_fields=[
                'status',
                'paid_at',
                'reference',
                'bank_reference',
                'updated_at',
            ]
        )
        log_action(
            request,
            'UPDATE',
            'remittances',
            'Remittance',
            remittance.id,
            'Remittance marked paid',
        )
        return Response(
            {
                'data': RemittanceSerializer(
                    remittance, context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        remittance = self.get_object()
        try:
            matched = Decimal(
                str(request.data.get('matched_amount') or remittance.net_amount)
            )
        except Exception:
            return Response(
                {'statusCode': 400, 'message': 'Invalid matched amount'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if matched != remittance.net_amount:
            return Response(
                {
                    'statusCode': 400,
                    'message': (
                        'Matched amount must equal the remittance net amount '
                        f'of {remittance.net_amount}'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        reference = (
            request.data.get('bank_reference')
            or request.data.get('reference')
            or remittance.bank_reference
        )
        if reference:
            remittance.bank_reference = reference
            remittance.reference = remittance.reference or reference
        remittance.matched_amount = matched
        remittance.matched_at = timezone.now()
        remittance.status = RemittanceStatus.RECONCILED
        if not remittance.paid_at:
            remittance.paid_at = timezone.now()
        remittance.save(
            update_fields=[
                'status',
                'paid_at',
                'reference',
                'bank_reference',
                'matched_amount',
                'matched_at',
                'updated_at',
            ]
        )
        log_action(
            request,
            'APPROVE',
            'remittances',
            'Remittance',
            remittance.id,
            'Remittance reconciled against bank reference',
        )
        return Response(
            {
                'data': RemittanceSerializer(
                    remittance, context={'request': request}
                ).data
            }
        )

    @action(detail=False, methods=['post'])
    def generate(self, request):
        insurer_id = request.data.get('insurer')
        period_from = request.data.get('period_from')
        period_to = request.data.get('period_to')
        if not insurer_id or not period_from or not period_to:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'insurer, period_from and period_to are required',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from datetime import date as date_type
            pf = date.fromisoformat(str(period_from))
            pt = date.fromisoformat(str(period_to))
        except ValueError:
            return Response(
                {'statusCode': 400, 'message': 'Invalid date format for period_from or period_to'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pt < pf:
            return Response(
                {'statusCode': 400, 'message': 'period_to cannot be before period_from'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        policies = Policy.objects.filter(
            insurer_id=insurer_id,
            start_date__gte=period_from,
            start_date__lte=period_to,
        )
        gross = policies.aggregate(total=Sum('total_premium'))['total'] or Decimal('0')
        taxes = policies.aggregate(total=Sum('taxes'))['total'] or Decimal('0')
        commission = (
            Commission.objects.filter(policy__in=policies).aggregate(
                total=Sum('amount')
            )['total']
            or Decimal('0')
        )
        net = gross - commission - taxes
        remittance = Remittance.objects.create(
            remittance_number=next_number(
                Remittance, 'remittance_number', 'REM'
            ),
            insurer_id=insurer_id,
            branch_id=(
                request.data.get('branch')
                or (request.user.branch_id if request.user.branch_id else None)
            ),
            period_from=period_from,
            period_to=period_to,
            gross_premium=gross,
            commission_retained=commission,
            taxes=taxes,
            net_amount=net,
            status=RemittanceStatus.DRAFT,
            created_by=request.user,
        )
        log_action(
            request,
            'CREATE',
            'remittances',
            'Remittance',
            remittance.id,
            'Remittance advice generated',
        )
        return Response(
            {
                'data': RemittanceSerializer(
                    remittance, context={'request': request}
                ).data
            },
            status=status.HTTP_201_CREATED,
        )
