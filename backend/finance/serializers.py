from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from common.numbering import next_number
from finance.models import (
    Commission,
    CommissionStatus,
    CreditDebitNote,
    Invoice,
    NoteType,
    Payment,
    Premium,
    Remittance,
)
from finance.services import allocate_payment


class PremiumSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    client_name = serializers.CharField(source='policy.client.name', read_only=True)
    insurer_name = serializers.CharField(
        source='policy.insurer.name', read_only=True
    )
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Premium
        fields = [
            'id',
            'policy',
            'policy_number',
            'client_name',
            'insurer_name',
            'installment_no',
            'amount_due',
            'amount_paid',
            'balance',
            'due_date',
            'paid_at',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['amount_paid', 'paid_at']

    def get_balance(self, obj):
        return float(obj.amount_due - obj.amount_paid)

    def validate_amount_due(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Amount due must be greater than zero.')
        return value

    def validate_status(self, value):
        if self.instance and self.instance.status in ('PAID', 'WAIVED') and value not in ('PAID', 'WAIVED'):
            raise serializers.ValidationError(
                f'Cannot change status of a {self.instance.status.lower()} premium instalment.'
            )
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'client',
            'client_name',
            'policy',
            'policy_number',
            'issue_date',
            'due_date',
            'subtotal',
            'tax',
            'total',
            'amount_paid',
            'balance',
            'status',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['invoice_number', 'amount_paid', 'created_by']
        extra_kwargs = {'total': {'required': False}}

    def get_balance(self, obj):
        return float(obj.total - obj.amount_paid)

    def validate_subtotal(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Subtotal cannot be negative.')
        return value

    def validate(self, attrs):
        issue_date = attrs.get('issue_date')
        due_date = attrs.get('due_date')
        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError(
                {'due_date': 'Due date cannot be before the issue date.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data['invoice_number'] = next_number(
            Invoice, 'invoice_number', 'INV'
        )
        if user and user.is_authenticated:
            validated_data['created_by'] = user
        validated_data.setdefault('issue_date', timezone.localdate())
        validated_data.setdefault(
            'due_date', validated_data['issue_date'] + timedelta(days=30)
        )
        subtotal = Decimal(str(validated_data.get('subtotal') or 0))
        tax = Decimal(str(validated_data.get('tax') or 0))
        if not validated_data.get('total'):
            validated_data['total'] = subtotal + tax
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    paid_at = serializers.DateTimeField(required=False, default=timezone.now)
    client_name = serializers.CharField(source='client.name', read_only=True)
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    invoice_number = serializers.CharField(
        source='invoice.invoice_number', read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.full_name', read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            'id',
            'receipt_number',
            'client',
            'client_name',
            'policy',
            'policy_number',
            'invoice',
            'invoice_number',
            'amount',
            'method',
            'reference',
            'paid_at',
            'status',
            'received_by',
            'received_by_name',
            'notes',
            'refunded_amount',
            'refunded_at',
            'refund_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'receipt_number',
            'received_by',
            'refunded_amount',
            'refunded_at',
            'refund_reason',
        ]

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Payment amount must be greater than zero.')
        return value

    def validate_invoice(self, invoice):
        if invoice and invoice.status == 'CANCELLED':
            raise serializers.ValidationError('Cannot apply a payment to a cancelled invoice.')
        return invoice

    def validate(self, attrs):
        client = attrs.get('client') or (self.instance.client if self.instance else None)
        invoice = attrs.get('invoice') or (self.instance.invoice if self.instance else None)
        if client and invoice and invoice.client_id != client.pk:
            raise serializers.ValidationError(
                {'invoice': 'The selected invoice does not belong to the selected client.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data['receipt_number'] = next_number(
            Payment, 'receipt_number', 'RCT'
        )
        if user and user.is_authenticated:
            validated_data['received_by'] = user
        validated_data.setdefault('paid_at', timezone.now())
        payment = super().create(validated_data)
        allocate_payment(payment)
        return payment


class CreditDebitNoteSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )

    class Meta:
        model = CreditDebitNote
        fields = [
            'id',
            'note_number',
            'note_type',
            'client',
            'client_name',
            'policy',
            'policy_number',
            'amount',
            'reason',
            'status',
            'issue_date',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['note_number', 'created_by']

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        prefix = 'DBN' if validated_data.get('note_type') == NoteType.DEBIT else 'CRN'
        validated_data['note_number'] = next_number(
            CreditDebitNote, 'note_number', prefix
        )
        if user and user.is_authenticated:
            validated_data['created_by'] = user
        validated_data.setdefault('issue_date', timezone.localdate())
        return super().create(validated_data)


class CommissionSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    client_name = serializers.CharField(source='policy.client.name', read_only=True)
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    broker_name = serializers.CharField(source='broker.full_name', read_only=True)

    class Meta:
        model = Commission
        fields = [
            'id',
            'policy',
            'policy_number',
            'client_name',
            'insurer',
            'insurer_name',
            'broker',
            'broker_name',
            'rate',
            'amount',
            'status',
            'earned_at',
            'paid_at',
            'notes',
            'created_at',
            'updated_at',
        ]

    def validate_rate(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError('Commission rate must be between 0 and 100.')
        return value

    def validate_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Commission amount cannot be negative.')
        return value

    def create(self, validated_data):
        if (
            validated_data.get('status') == CommissionStatus.EARNED
            and not validated_data.get('earned_at')
        ):
            validated_data['earned_at'] = timezone.now()
        return super().create(validated_data)


class RemittanceSerializer(serializers.ModelSerializer):
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )

    class Meta:
        model = Remittance
        fields = [
            'id',
            'remittance_number',
            'insurer',
            'insurer_name',
            'branch',
            'branch_name',
            'period_from',
            'period_to',
            'gross_premium',
            'commission_retained',
            'taxes',
            'net_amount',
            'status',
            'paid_at',
            'reference',
            'bank_reference',
            'matched_amount',
            'matched_at',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'remittance_number',
            'created_by',
            'paid_at',
            'matched_amount',
            'matched_at',
        ]

    def validate_gross_premium(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Gross premium cannot be negative.')
        return value

    def validate(self, attrs):
        period_from = attrs.get('period_from') or (self.instance.period_from if self.instance else None)
        period_to = attrs.get('period_to') or (self.instance.period_to if self.instance else None)
        if period_from and period_to and period_to < period_from:
            raise serializers.ValidationError(
                {'period_to': 'Period to cannot be before period from.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            validated_data['created_by'] = user
            if not validated_data.get('branch') and user.branch_id:
                validated_data['branch_id'] = user.branch_id
        gross = Decimal(str(validated_data.get('gross_premium') or 0))
        commission = Decimal(str(validated_data.get('commission_retained') or 0))
        taxes = Decimal(str(validated_data.get('taxes') or 0))
        if validated_data.get('net_amount') in (None, ''):
            validated_data['net_amount'] = gross - commission - taxes
        return super().create(validated_data)
