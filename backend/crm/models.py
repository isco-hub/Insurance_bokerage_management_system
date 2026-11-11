import uuid

from django.conf import settings
from django.db import models


class ClientType(models.TextChoices):
    INDIVIDUAL = 'INDIVIDUAL', 'Individual'
    CORPORATE = 'CORPORATE', 'Corporate'


class KycStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    VERIFIED = 'VERIFIED', 'Verified'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_type = models.CharField(
        max_length=20, choices=ClientType.choices, default=ClientType.INDIVIDUAL
    )
    client_number = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=180)
    national_id = models.CharField(max_length=40, blank=True)
    passport_no = models.CharField(max_length=40, blank=True)
    tin = models.CharField(max_length=40, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)
    alt_phone = models.CharField(max_length=30, blank=True)
    physical_address = models.CharField(max_length=255, blank=True)
    postal_address = models.CharField(max_length=255, blank=True)
    kyc_status = models.CharField(
        max_length=20, choices=KycStatus.choices, default=KycStatus.PENDING
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    next_of_kin_name = models.CharField(max_length=120, blank=True)
    next_of_kin_phone = models.CharField(max_length=30, blank=True)
    next_of_kin_relationship = models.CharField(max_length=60, blank=True)
    registration_no = models.CharField(max_length=60, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    business_sector = models.CharField(max_length=120, blank=True)
    website = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    branch = models.ForeignKey(
        'accounts.Branch', on_delete=models.RESTRICT, related_name='clients'
    )
    relationship_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='clients_managed',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='clients_created',
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['phone']),
            models.Index(fields=['national_id']),
            models.Index(fields=['registration_no']),
        ]

    def __str__(self):
        return f'{self.client_number} — {self.name}'


class ClientContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='contacts'
    )
    full_name = models.CharField(max_length=120)
    job_title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'client_contacts'
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f'{self.full_name} ({self.client.name})'


class ClientDirector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='directors'
    )
    full_name = models.CharField(max_length=120)
    national_id = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    ownership_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'client_directors'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.client.name})'


class Insurer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    physical_address = models.CharField(max_length=255, blank=True)
    website = models.CharField(max_length=150, blank=True)
    payment_instructions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurers'
        ordering = ['name']

    def __str__(self):
        return self.name


class InsurerContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    insurer = models.ForeignKey(
        Insurer, on_delete=models.CASCADE, related_name='contacts'
    )
    full_name = models.CharField(max_length=120)
    job_title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurer_contacts'
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f'{self.full_name} ({self.insurer.name})'


class InsurerBranch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    insurer = models.ForeignKey(
        Insurer, on_delete=models.CASCADE, related_name='branches'
    )
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurer_branches'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.insurer.name})'


class ClassCategory(models.TextChoices):
    GENERAL = 'GENERAL', 'General Insurance'
    LIFE = 'LIFE', 'Life Insurance'


class InsuranceClass(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=20, choices=ClassCategory.choices, default=ClassCategory.GENERAL
    )
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurance_classes'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    insurance_class = models.ForeignKey(
        InsuranceClass, on_delete=models.RESTRICT, related_name='products'
    )
    insurer = models.ForeignKey(
        Insurer, on_delete=models.RESTRICT, related_name='products'
    )
    underwriting_contact = models.CharField(max_length=150, blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    minimum_premium = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        unique_together = [('insurer', 'name')]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.insurer.name})'
# 2026-11-11T15:06:07Z client model
# 2026-11-11T15:06:07Z insurer model
# 2026-11-11T15:06:07Z class/product models
# 2026-11-11T15:06:08Z client CRUD tests
