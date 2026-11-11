from rest_framework import serializers

from claims.models import Claim
from common.numbering import next_number


class ClaimSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(
        source='policy.policy_number', read_only=True
    )
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_number = serializers.CharField(
        source='client.client_number', read_only=True
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
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = [
            'id',
            'claim_number',
            'policy',
            'policy_number',
            'client',
            'client_name',
            'client_number',
            'insurer_name',
            'product_name',
            'date_of_loss',
            'reported_at',
            'cause',
            'description',
            'surveyor',
            'reserve_amount',
            'paid_amount',
            'recovered_amount',
            'status',
            'settled_at',
            'notes',
            'handled_by',
            'handled_by_name',
            'days_open',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['claim_number', 'handled_by', 'reported_at']

    def get_days_open(self, obj):
        from django.utils import timezone

        end = (
            obj.settled_at.date()
            if obj.settled_at
            else timezone.localdate()
        )
        return max(0, (end - obj.date_of_loss).days)

    def validate_policy(self, policy):
        if policy and policy.status in ('CANCELLED', 'EXPIRED', 'LAPSED'):
            raise serializers.ValidationError(
                f'Cannot create a claim on a {policy.status.lower()} policy.'
            )
        return policy

    def validate(self, attrs):
        from django.utils import timezone
        policy = attrs.get('policy') or (self.instance.policy if self.instance else None)
        date_of_loss = attrs.get('date_of_loss') or (self.instance.date_of_loss if self.instance else None)
        if date_of_loss:
            if date_of_loss > timezone.localdate():
                raise serializers.ValidationError(
                    {'date_of_loss': 'Date of loss cannot be in the future.'}
                )
            if policy and date_of_loss < policy.start_date:
                raise serializers.ValidationError(
                    {'date_of_loss': 'Date of loss cannot be before the policy start date.'}
                )
        reserve = attrs.get('reserve_amount')
        if reserve is not None and reserve < 0:
            raise serializers.ValidationError(
                {'reserve_amount': 'Reserve amount cannot be negative.'}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        validated_data['claim_number'] = next_number(Claim, 'claim_number', 'CLM')
        if user and user.is_authenticated and not validated_data.get('handled_by'):
            validated_data['handled_by'] = user
        if validated_data.get('policy') and not validated_data.get('client'):
            validated_data['client'] = validated_data['policy'].client
        return super().create(validated_data)
# 2026-11-11T15:06:09Z document upload
# 2026-11-11T15:06:09Z date validation
