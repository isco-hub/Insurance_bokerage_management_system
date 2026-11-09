from rest_framework import viewsets

from common.viewsets import BaseModelViewSet, SoftDeleteMixin
from crm.models import (
    Client,
    ClientContact,
    ClientDirector,
    InsuranceClass,
    Insurer,
    InsurerBranch,
    InsurerContact,
    Product,
)
from crm.serializers import (
    ClientContactSerializer,
    ClientDirectorSerializer,
    ClientSerializer,
    InsuranceClassSerializer,
    InsurerBranchSerializer,
    InsurerContactSerializer,
    InsurerSerializer,
    ProductSerializer,
)


class ClientViewSet(SoftDeleteMixin, BaseModelViewSet):
    module = 'clients'
    audit_entity = 'Client'
    scope_branch = True
    queryset = (
        Client.objects.filter(deleted_at__isnull=True)
        .select_related('branch', 'relationship_manager', 'created_by')
        .prefetch_related('contacts', 'directors')
    )
    serializer_class = ClientSerializer
    filterset_fields = [
        'client_type',
        'kyc_status',
        'branch',
        'relationship_manager',
        'is_active',
    ]
    search_fields = [
        'name',
        'client_number',
        'phone',
        'national_id',
        'registration_no',
        'email',
        'tin',
    ]
    ordering_fields = ['name', 'client_number', 'created_at', 'kyc_status']
    ordering = ['name']


class ClientContactViewSet(BaseModelViewSet):
    module = 'clients'
    audit_entity = 'ClientContact'
    queryset = ClientContact.objects.select_related('client').all()
    serializer_class = ClientContactSerializer
    filterset_fields = ['client', 'is_primary']
    search_fields = ['full_name', 'email', 'phone']
    ordering = ['-is_primary', 'full_name']


class ClientDirectorViewSet(BaseModelViewSet):
    module = 'clients'
    audit_entity = 'ClientDirector'
    queryset = ClientDirector.objects.select_related('client').all()
    serializer_class = ClientDirectorSerializer
    filterset_fields = ['client']
    search_fields = ['full_name', 'national_id', 'email']
    ordering = ['full_name']


class InsurerViewSet(SoftDeleteMixin, BaseModelViewSet):
    module = 'insurers'
    audit_entity = 'Insurer'
    queryset = (
        Insurer.objects.all()
        .prefetch_related('contacts', 'branches')
    )
    serializer_class = InsurerSerializer
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'email', 'phone']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['name']


class InsurerContactViewSet(BaseModelViewSet):
    module = 'insurers'
    audit_entity = 'InsurerContact'
    queryset = InsurerContact.objects.select_related('insurer').all()
    serializer_class = InsurerContactSerializer
    filterset_fields = ['insurer', 'is_primary']
    search_fields = ['full_name', 'email', 'phone']
    ordering = ['-is_primary', 'full_name']


class InsurerBranchViewSet(BaseModelViewSet):
    module = 'insurers'
    audit_entity = 'InsurerBranch'
    queryset = InsurerBranch.objects.select_related('insurer').all()
    serializer_class = InsurerBranchSerializer
    filterset_fields = ['insurer', 'is_active']
    search_fields = ['name', 'address', 'email']
    ordering = ['name']


class InsuranceClassViewSet(BaseModelViewSet):
    module = 'products'
    audit_entity = 'InsuranceClass'
    queryset = InsuranceClass.objects.all()
    serializer_class = InsuranceClassSerializer
    filterset_fields = ['category', 'is_active']
    search_fields = ['code', 'name']
    ordering_fields = ['name', 'code']
    ordering = ['name']


class ProductViewSet(SoftDeleteMixin, BaseModelViewSet):
    module = 'products'
    audit_entity = 'Product'
    queryset = Product.objects.select_related('insurance_class', 'insurer')
    serializer_class = ProductSerializer
    filterset_fields = ['insurer', 'insurance_class', 'is_active']
    search_fields = ['code', 'name', 'insurer__name', 'insurance_class__name']
    ordering_fields = ['name', 'code', 'minimum_premium', 'created_at']
    ordering = ['name']
