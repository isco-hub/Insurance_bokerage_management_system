from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from accounts.models import Branch, User
from common.numbering import next_number
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
    Risk,
)
from operations.services import money, stage_for


class MotorDetailSerializer(serializers.ModelSerializer):
    risk_number = serializers.CharField(source='risk.risk_number', read_only=True)
    client_name = serializers.CharField(source='risk.client.name', read_only=True)

    def validate_vehicle_value(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Vehicle value must be greater than zero.')
        return value

    def validate_year(self, value):
        if value is not None:
            current_year = timezone.now().year
            if value < 1900 or value > current_year + 1:
                raise serializers.ValidationError(
                    f'Year must be between 1900 and {current_year + 1}.'
                )
        return value

    class Meta:
        model = MotorDetail
        fields = [
            'id',
            'risk',
            'risk_number',
            'client_name',
            'registration_number',
            'chassis_number',
            'engine_number',
            'make',
            'model',
            'year',
            'vehicle_value',
            'driver_name',
            'driver_license_no',
            'usage',
            'logbook_document',
            'created_at',
            'updated_at',
        ]


class RiskSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_number = serializers.CharField(
        source='client.client_number', read_only=True
    )
    branch = serializers.UUIDField(source='client.branch_id', read_only=True)
    motor_details = MotorDetailSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    quotation_count = serializers.IntegerField(
        source='quotations.count', read_only=True
    )

    class Meta:
        model = Risk
        fields = [
            'id',
            'risk_number',
            'client',
            'client_name',
            'client_number',
            'branch',
            'category',
            'location',
            'description',
            'asset_details',
            'previous_claims',
            'status',
            'created_by',
            'created_by_name',
            'motor_details',
            'quotation_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['risk_number', 'created_by']

    def validate_client(self, client):
        if client and (not client.is_active or client.deleted_at is not None):
            raise serializers.ValidationError('Cannot create a risk for an inactive or deleted client.')
        return client
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data['risk_number'] = next_number(Risk, 'risk_number', 'RSK')
        if user and user.is_authenticated:
            validated_data['created_by'] = user
        return super().create(validated_data)


class InsurerQuoteSerializer(serializers.ModelSerializer):
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    quotation_number = serializers.CharField(
        source='quotation.quotation_number', read_only=True
    )

    class Meta:
        model = InsurerQuote
        fields = [
            'id',
            'quotation',
            'quotation_number',
            'insurer',
            'insurer_name',
            'premium',
            'taxes',
            'terms',
            'status',
            'received_at',
            'valid_until',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['received_at']

    def validate_premium(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Premium cannot be negative.')
        return value

    def validate(self, attrs):
        quotation = attrs.get('quotation') or (self.instance.quotation if self.instance else None)
        insurer = attrs.get('insurer') or (self.instance.insurer if self.instance else None)
        if quotation and insurer:
            qs = InsurerQuote.objects.filter(quotation=quotation, insurer=insurer)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'insurer': 'A quote from this insurer already exists for this quotation.'}
                )
        premium = attrs.get('premium')
        if premium is not None and premium <= 0:
            raise serializers.ValidationError(
                {'premium': 'Premium must be greater than zero.'}
            )
        return attrs

    def _sync(self, instance):
        quotation = instance.quotation
        if instance.status == QuoteResponseStatus.RECEIVED:
            if quotation.status in ('DRAFT', 'SENT'):
                quotation.status = 'QUOTES_RECEIVED'
                quotation.save(update_fields=['status', 'updated_at'])
        return instance

    def create(self, validated_data):
        if (
            validated_data.get('status') == QuoteResponseStatus.RECEIVED
            and not validated_data.get('received_at')
        ):
            validated_data['received_at'] = timezone.now()
        instance = super().create(validated_data)
        return self._sync(instance)

    def update(self, instance, validated_data):
        if (
            validated_data.get('status') == QuoteResponseStatus.RECEIVED
            and not instance.received_at
        ):
            validated_data['received_at'] = timezone.now()
        instance = super().update(instance, validated_data)
        return self._sync(instance)


class QuotationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_number = serializers.CharField(
        source='client.client_number', read_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    insurance_class_name = serializers.CharField(
        source='product.insurance_class.name', read_only=True
    )
    risk_number = serializers.CharField(source='risk.risk_number', read_only=True)
    broker_name = serializers.CharField(source='broker.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    selected_insurer_name = serializers.CharField(
        source='selected_insurer.name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    insurer_quotes = InsurerQuoteSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()

    broker = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=False
    )

    class Meta:
        model = Quotation
        fields = [
            'id',
            'quotation_number',
            'client',
            'client_name',
            'client_number',
            'product',
            'product_name',
            'insurance_class_name',
            'risk',
            'risk_number',
            'broker',
            'broker_name',
            'branch',
            'branch_name',
            'sum_insured',
            'premium',
            'taxes',
            'total_premium',
            'valid_from',
            'valid_to',
            'status',
            'selected_insurer',
            'selected_insurer_name',
            'notes',
            'created_by',
            'created_by_name',
            'insurer_quotes',
            'is_expired',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['quotation_number', 'created_by']

    def get_is_expired(self, obj):
        return obj.valid_to < timezone.localdate()

    def validate(self, attrs):
        valid_from = attrs.get('valid_from') or (self.instance.valid_from if self.instance else None)
        valid_to = attrs.get('valid_to') or (self.instance.valid_to if self.instance else None)
        if valid_from and valid_to and valid_to <= valid_from:
            raise serializers.ValidationError(
                {'valid_to': 'Valid to date must be after valid from date.'}
            )
        client = attrs.get('client') or (self.instance.client if self.instance else None)
        if client and (not client.is_active or client.deleted_at is not None):
            raise serializers.ValidationError(
                {'client': 'Cannot create a quotation for an inactive or deleted client.'}
            )
        risk = attrs.get('risk') or (self.instance.risk if self.instance else None)
        if risk and client and risk.client_id != client.pk:
            raise serializers.ValidationError(
                {'risk': 'The selected risk does not belong to the selected client.'}
            )
        premium = attrs.get('premium')
        if premium is not None and premium < 0:
            raise serializers.ValidationError(
                {'premium': 'Premium cannot be negative.'}
            )
        return attrs

    def _apply_totals(self, validated_data, instance=None):
        premium = validated_data.get(
            'premium', instance.premium if instance else Decimal('0')
        )
        taxes = validated_data.get(
            'taxes', instance.taxes if instance else Decimal('0')
        )
        validated_data['premium'] = money(premium)
        validated_data['taxes'] = money(taxes)
        if 'total_premium' not in validated_data or not validated_data.get(
            'total_premium'
        ):
            validated_data['total_premium'] = money(premium) + money(taxes)
        return validated_data

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data = self._apply_totals(validated_data)
        validated_data['quotation_number'] = next_number(
            Quotation, 'quotation_number', 'QT'
        )
        if user and user.is_authenticated:
            validated_data.setdefault('broker', user)
            validated_data.setdefault('created_by', user)
            if not validated_data.get('branch') and user.branch_id:
                validated_data['branch_id'] = user.branch_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_totals(validated_data, instance)
        return super().update(instance, validated_data)


class PolicySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_number = serializers.CharField(
        source='client.client_number', read_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    insurance_class_name = serializers.CharField(
        source='product.insurance_class.name', read_only=True
    )
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    broker_name = serializers.CharField(source='broker.full_name', read_only=True)
    quotation_number = serializers.CharField(
        source='quotation.quotation_number', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    days_to_renewal = serializers.SerializerMethodField()
    claim_count = serializers.IntegerField(source='claims.count', read_only=True)
    outstanding_premium = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            'id',
            'policy_number',
            'client',
            'client_name',
            'client_number',
            'product',
            'product_name',
            'insurance_class_name',
            'insurer',
            'insurer_name',
            'quotation',
            'quotation_number',
            'branch',
            'branch_name',
            'broker',
            'broker_name',
            'sum_insured',
            'premium',
            'taxes',
            'total_premium',
            'start_date',
            'end_date',
            'renewal_date',
            'status',
            'payment_frequency',
            'commission_rate',
            'commission_amount',
            'notes',
            'cancelled_at',
            'cancellation_effective_date',
            'cancellation_reason',
            'created_by',
            'created_by_name',
            'days_to_renewal',
            'claim_count',
            'outstanding_premium',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'policy_number',
            'created_by',
            'commission_amount',
            'cancelled_at',
            'cancellation_effective_date',
            'cancellation_reason',
        ]

    def get_days_to_renewal(self, obj):
        return (obj.renewal_date - timezone.localdate()).days

    def get_outstanding_premium(self, obj):
        total = sum(
            (p.amount_due - p.amount_paid)
            for p in obj.premiums.all()
            if p.status not in ('PAID', 'WAIVED')
        )
        return float(money(total))


class PolicyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            'client',
            'product',
            'insurer',
            'quotation',
            'branch',
            'broker',
            'sum_insured',
            'premium',
            'taxes',
            'total_premium',
            'start_date',
            'end_date',
            'renewal_date',
            'status',
            'payment_frequency',
            'commission_rate',
            'notes',
        ]
        extra_kwargs = {
            'insurer': {'required': False},
            'quotation': {'required': False},
            'branch': {'required': False},
            'broker': {'required': False},
            'status': {'required': False},
            'renewal_date': {'required': False},
            'taxes': {'required': False},
            'total_premium': {'required': False},
            'commission_rate': {'required': False},
        }

    def validate(self, attrs):
        start = attrs.get('start_date') or getattr(self.instance, 'start_date', None)
        end = attrs.get('end_date') or getattr(self.instance, 'end_date', None)
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after the start date.'}
            )
        premium = attrs.get('premium')
        if premium is not None and premium <= 0:
            raise serializers.ValidationError(
                {'premium': 'Premium must be greater than zero.'}
            )
        commission_rate = attrs.get('commission_rate')
        if commission_rate is not None and not (0 <= commission_rate <= 100):
            raise serializers.ValidationError(
                {'commission_rate': 'Commission rate must be between 0 and 100.'}
            )
        return attrs


class EndorsementSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    client_name = serializers.CharField(
        source='policy.client.name', read_only=True
    )
    insurer_name = serializers.CharField(
        source='policy.insurer.name', read_only=True
    )
    requested_by_name = serializers.CharField(
        source='requested_by.full_name', read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.full_name', read_only=True
    )

    class Meta:
        model = Endorsement
        fields = [
            'id',
            'endorsement_number',
            'policy',
            'policy_number',
            'client_name',
            'insurer_name',
            'type',
            'description',
            'effective_date',
            'premium_adjustment',
            'status',
            'requested_by',
            'requested_by_name',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'endorsement_number',
            'requested_by',
            'approved_by',
            'approved_at',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data['endorsement_number'] = next_number(
            Endorsement, 'endorsement_number', 'END'
        )
        if user and user.is_authenticated:
            validated_data['requested_by'] = user
        return super().create(validated_data)

    def validate_policy(self, policy):
        if policy and policy.status in ('CANCELLED', 'EXPIRED', 'LAPSED'):
            raise serializers.ValidationError(
                f'Cannot create an endorsement on a {policy.status.lower()} policy.'
            )
        return policy

    def validate_effective_date(self, value):
        return value

    def validate(self, attrs):
        policy = attrs.get('policy') or (self.instance.policy if self.instance else None)
        effective_date = attrs.get('effective_date') or (self.instance.effective_date if self.instance else None)
        if policy and effective_date:
            if effective_date < policy.start_date:
                raise serializers.ValidationError(
                    {'effective_date': 'Effective date cannot be before the policy start date.'}
                )
            if effective_date > policy.end_date:
                raise serializers.ValidationError(
                    {'effective_date': 'Effective date cannot be after the policy end date.'}
                )
        return attrs


class RenewalSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    client_name = serializers.CharField(
        source='policy.client.name', read_only=True
    )
    insurer_name = serializers.CharField(
        source='policy.insurer.name', read_only=True
    )
    product_name = serializers.CharField(
        source='policy.product.name', read_only=True
    )
    handled_by_name = serializers.CharField(
        source='handled_by.full_name', read_only=True
    )
    renewal_quotation_number = serializers.CharField(
        source='renewal_quotation.quotation_number', read_only=True
    )
    days_to_due = serializers.SerializerMethodField()

    class Meta:
        model = Renewal
        fields = [
            'id',
            'policy',
            'policy_number',
            'client_name',
            'insurer_name',
            'product_name',
            'due_date',
            'stage_days',
            'status',
            'renewal_quotation',
            'renewal_quotation_number',
            'handled_by',
            'handled_by_name',
            'won_at',
            'lost_at',
            'lost_reason',
            'notes',
            'days_to_due',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['handled_by', 'won_at', 'lost_at']

    def get_days_to_due(self, obj):
        return (obj.due_date - timezone.localdate()).days

    def validate(self, attrs):
        policy = attrs.get('policy') or (self.instance.policy if self.instance else None)
        due_date = attrs.get('due_date') or (self.instance.due_date if self.instance else None)
        if policy and due_date and due_date < policy.end_date:
            raise serializers.ValidationError(
                {'due_date': 'Renewal due date cannot be before the policy end date.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not validated_data.get('stage_days'):
            validated_data['stage_days'] = stage_for(validated_data['due_date'])
        if user and user.is_authenticated and not validated_data.get('handled_by'):
            validated_data['handled_by'] = user
        return super().create(validated_data)
