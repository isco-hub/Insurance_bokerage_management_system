from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from accounts.serializers import BranchSerializer
from common.numbering import next_number
from crm.models import (
    Client,
    ClientContact,
    ClientDirector,
    InsuranceClass,
    Insurer,
    InsurerBranch,
    InsurerContact,
    KycStatus,
    Product,
)


def _validate_percentage(value, field_name='Value'):
    if value is not None and not (0 <= value <= 100):
        raise serializers.ValidationError(
            {field_name: f'{field_name} must be between 0 and 100.'}
        )
    return value


class ClientContactSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    def validate_client(self, client):
        if client and (client.deleted_at is not None or not client.is_active):
            raise serializers.ValidationError('Cannot add contacts to an inactive or deleted client.')
        return client

    class Meta:
        model = ClientContact
        fields = [
            'id',
            'client',
            'client_name',
            'full_name',
            'job_title',
            'email',
            'phone',
            'is_primary',
            'created_at',
            'updated_at',
        ]


class ClientDirectorSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    def validate_client(self, client):
        if client and (client.deleted_at is not None or not client.is_active):
            raise serializers.ValidationError('Cannot add directors to an inactive or deleted client.')
        return client

    def validate_ownership_percentage(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError('Ownership percentage must be between 0 and 100.')
        return value

    def validate(self, attrs):
        client = attrs.get('client') or (self.instance.client if self.instance else None)
        new_pct = attrs.get('ownership_percentage')
        if client and new_pct is not None:
            qs = ClientDirector.objects.filter(client=client)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            existing_total = sum(
                d.ownership_percentage or 0 for d in qs
            )
            if existing_total + new_pct > 100:
                raise serializers.ValidationError(
                    {'ownership_percentage': f'Total ownership for this client would exceed 100% ({existing_total + new_pct}%).'}  
                )
        return attrs

    class Meta:
        model = ClientDirector
        fields = [
            'id',
            'client',
            'client_name',
            'full_name',
            'national_id',
            'email',
            'phone',
            'ownership_percentage',
            'created_at',
            'updated_at',
        ]


class ClientSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    relationship_manager_name = serializers.CharField(
        source='relationship_manager.full_name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    contacts = ClientContactSerializer(many=True, read_only=True)
    directors = ClientDirectorSerializer(many=True, read_only=True)
    policy_count = serializers.IntegerField(source='policies.count', read_only=True)
    risk_count = serializers.IntegerField(source='risks.count', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id',
            'client_type',
            'client_number',
            'name',
            'national_id',
            'passport_no',
            'tin',
            'occupation',
            'date_of_birth',
            'gender',
            'email',
            'phone',
            'alt_phone',
            'physical_address',
            'postal_address',
            'kyc_status',
            'kyc_verified_at',
            'next_of_kin_name',
            'next_of_kin_phone',
            'next_of_kin_relationship',
            'registration_no',
            'incorporation_date',
            'business_sector',
            'website',
            'notes',
            'branch',
            'branch_name',
            'relationship_manager',
            'relationship_manager_name',
            'created_by',
            'created_by_name',
            'is_active',
            'deleted_at',
            'contacts',
            'directors',
            'policy_count',
            'risk_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['client_number', 'created_by', 'deleted_at']

    def validate_phone(self, value):
        if value:
            qs = Client.objects.filter(phone=value, deleted_at__isnull=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('A client with this phone number already exists.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not validated_data.get('branch') and user and user.branch_id:
            validated_data['branch_id'] = user.branch_id
        if user and user.is_authenticated:
            validated_data.setdefault('created_by', user)
        validated_data['client_number'] = next_number(
            Client, 'client_number', 'CLI'
        )
        if (
            validated_data.get('kyc_status') == KycStatus.VERIFIED
            and not validated_data.get('kyc_verified_at')
        ):
            validated_data['kyc_verified_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_status = validated_data.get('kyc_status', instance.kyc_status)
        if new_status == KycStatus.VERIFIED and not instance.kyc_verified_at:
            validated_data['kyc_verified_at'] = timezone.now()
        elif new_status != KycStatus.VERIFIED and instance.kyc_verified_at:
            validated_data['kyc_verified_at'] = None
        return super().update(instance, validated_data)


class InsurerContactSerializer(serializers.ModelSerializer):
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)

    class Meta:
        model = InsurerContact
        fields = [
            'id',
            'insurer',
            'insurer_name',
            'full_name',
            'job_title',
            'email',
            'phone',
            'is_primary',
            'created_at',
            'updated_at',
        ]


class InsurerBranchSerializer(serializers.ModelSerializer):
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)

    class Meta:
        model = InsurerBranch
        fields = [
            'id',
            'insurer',
            'insurer_name',
            'name',
            'address',
            'phone',
            'email',
            'is_active',
            'created_at',
            'updated_at',
        ]


class InsurerSerializer(serializers.ModelSerializer):
    contacts = InsurerContactSerializer(many=True, read_only=True)
    branches = InsurerBranchSerializer(many=True, read_only=True)
    product_count = serializers.IntegerField(
        source='products.count', read_only=True
    )
    policy_count = serializers.IntegerField(source='policies.count', read_only=True)

    def validate_code(self, value):
        qs = Insurer.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An insurer with this code already exists.')
        return value.upper()

    class Meta:
        model = Insurer
        fields = [
            'id',
            'code',
            'name',
            'email',
            'phone',
            'physical_address',
            'website',
            'payment_instructions',
            'notes',
            'is_active',
            'contacts',
            'branches',
            'product_count',
            'policy_count',
            'created_at',
            'updated_at',
        ]


class InsuranceClassSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(
        source='products.count', read_only=True
    )

    class Meta:
        model = InsuranceClass
        fields = [
            'id',
            'code',
            'name',
            'category',
            'description',
            'is_active',
            'product_count',
            'created_at',
            'updated_at',
        ]


class ProductSerializer(serializers.ModelSerializer):
    insurance_class_name = serializers.CharField(
        source='insurance_class.name', read_only=True
    )
    insurance_class_category = serializers.CharField(
        source='insurance_class.category', read_only=True
    )
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)

    def validate_commission_rate(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError('Commission rate must be between 0 and 100.')
        return value

    def validate_minimum_premium(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Minimum premium cannot be negative.')
        return value

    def validate_insurer(self, insurer):
        if insurer and not insurer.is_active:
            raise serializers.ValidationError('Cannot assign an inactive insurer to a product.')
        return insurer

    def validate_insurance_class(self, ins_class):
        if ins_class and not ins_class.is_active:
            raise serializers.ValidationError('Cannot assign an inactive insurance class to a product.')
        return ins_class

    class Meta:
        model = Product
        fields = [
            'id',
            'code',
            'name',
            'insurance_class',
            'insurance_class_name',
            'insurance_class_category',
            'insurer',
            'insurer_name',
            'underwriting_contact',
            'required_documents',
            'minimum_premium',
            'commission_rate',
            'is_active',
            'created_at',
            'updated_at',
        ]


class ClientOptionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='name', read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'client_number', 'name', 'label', 'phone']


class UserOptionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'label']
# 2026-11-11T15:06:07Z product serializer
