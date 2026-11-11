import uuid

from django.conf import settings
from django.db import models


class RiskStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under review'
    CLOSED = 'CLOSED', 'Closed'


class QuotationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SENT = 'SENT', 'Sent to insurers'
    QUOTES_RECEIVED = 'QUOTES_RECEIVED', 'Quotes received'
    SELECTED = 'SELECTED', 'Selected'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DECLINED = 'DECLINED', 'Declined'
    EXPIRED = 'EXPIRED', 'Expired'


class QuoteResponseStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    RECEIVED = 'RECEIVED', 'Received'
    DECLINED = 'DECLINED', 'Declined'


class PolicyStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'
    LAPSED = 'LAPSED', 'Lapsed'


class EndorsementType(models.TextChoices):
    ADDITION = 'ADDITION', 'Addition'
    DELETION = 'DELETION', 'Deletion'
    AMENDMENT = 'AMENDMENT', 'Amendment'
    CANCELLATION = 'CANCELLATION', 'Cancellation'
    REINSTATEMENT = 'REINSTATEMENT', 'Reinstatement'


class EndorsementStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class RenewalStatus(models.TextChoices):
    UPCOMING = 'UPCOMING', 'Upcoming'
    DUE = 'DUE', 'Due'
    QUOTED = 'QUOTED', 'Quoted'
    WON = 'WON', 'Won'
    LOST = 'LOST', 'Lost'
    LAPSED = 'LAPSED', 'Lapsed'


class Risk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    risk_number = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='risks'
    )
    category = models.CharField(max_length=60)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    asset_details = models.JSONField(default=dict, blank=True)
    previous_claims = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=RiskStatus.choices, default=RiskStatus.OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='risks_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'risks'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['category'])]

    def __str__(self):
        return f'{self.risk_number} — {self.category}'


class MotorDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    risk = models.ForeignKey(
        Risk, on_delete=models.CASCADE, related_name='motor_details'
    )
    registration_number = models.CharField(max_length=30)
    chassis_number = models.CharField(max_length=60, blank=True)
    engine_number = models.CharField(max_length=60, blank=True)
    make = models.CharField(max_length=60)
    model = models.CharField(max_length=60, blank=True)
    year = models.IntegerField(null=True, blank=True)
    vehicle_value = models.DecimalField(max_digits=14, decimal_places=2)
    driver_name = models.CharField(max_length=120, blank=True)
    driver_license_no = models.CharField(max_length=50, blank=True)
    usage = models.CharField(max_length=60, blank=True)
    logbook_document = models.ForeignKey(
        'workspace.Document',
        on_delete=models.SET_NULL,
        related_name='motor_details',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'motor_details'
        ordering = ['registration_number']
        indexes = [models.Index(fields=['registration_number'])]

    def __str__(self):
        return self.registration_number


class Quotation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation_number = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='quotations'
    )
    product = models.ForeignKey(
        'crm.Product', on_delete=models.RESTRICT, related_name='quotations'
    )
    risk = models.ForeignKey(
        Risk, on_delete=models.SET_NULL, related_name='quotations', null=True, blank=True
    )
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='quotations_brokered',
    )
    branch = models.ForeignKey(
        'accounts.Branch', on_delete=models.RESTRICT, related_name='quotations'
    )
    sum_insured = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    premium = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_premium = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valid_from = models.DateField()
    valid_to = models.DateField()
    status = models.CharField(
        max_length=20, choices=QuotationStatus.choices, default=QuotationStatus.DRAFT
    )
    selected_insurer = models.ForeignKey(
        'crm.Insurer',
        on_delete=models.SET_NULL,
        related_name='selected_quotations',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='quotations_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quotations'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.quotation_number


class InsurerQuote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name='insurer_quotes'
    )
    insurer = models.ForeignKey(
        'crm.Insurer', on_delete=models.RESTRICT, related_name='quotes'
    )
    premium = models.DecimalField(max_digits=14, decimal_places=2)
    taxes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    terms = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=QuoteResponseStatus.choices,
        default=QuoteResponseStatus.REQUESTED,
    )
    received_at = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurer_quotes'
        unique_together = [('quotation', 'insurer')]
        ordering = ['premium']

    def __str__(self):
        return f'{self.quotation.quotation_number} / {self.insurer.name}'


class Policy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_number = models.CharField(max_length=40, unique=True)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='policies'
    )
    product = models.ForeignKey(
        'crm.Product', on_delete=models.RESTRICT, related_name='policies'
    )
    insurer = models.ForeignKey(
        'crm.Insurer', on_delete=models.RESTRICT, related_name='policies'
    )
    quotation = models.OneToOneField(
        Quotation,
        on_delete=models.SET_NULL,
        related_name='policy',
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        'accounts.Branch', on_delete=models.RESTRICT, related_name='policies'
    )
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='policies_brokered',
        null=True,
        blank=True,
    )
    sum_insured = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    premium = models.DecimalField(max_digits=14, decimal_places=2)
    taxes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_premium = models.DecimalField(max_digits=14, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    renewal_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=PolicyStatus.choices, default=PolicyStatus.PENDING
    )
    payment_frequency = models.CharField(max_length=20, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    notes = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_effective_date = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='policies_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'policies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return self.policy_number


class Endorsement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endorsement_number = models.CharField(max_length=40, unique=True)
    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name='endorsements'
    )
    type = models.CharField(max_length=20, choices=EndorsementType.choices)
    description = models.TextField()
    effective_date = models.DateField()
    premium_adjustment = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20,
        choices=EndorsementStatus.choices,
        default=EndorsementStatus.DRAFT,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='endorsements_requested',
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='endorsements_approved',
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'endorsements'
        ordering = ['-created_at']

    def __str__(self):
        return self.endorsement_number


class Renewal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name='renewals'
    )
    due_date = models.DateField()
    stage_days = models.IntegerField(default=90)
    status = models.CharField(
        max_length=20, choices=RenewalStatus.choices, default=RenewalStatus.UPCOMING
    )
    renewal_quotation = models.OneToOneField(
        Quotation,
        on_delete=models.SET_NULL,
        related_name='renewal',
        null=True,
        blank=True,
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='renewals_handled',
        null=True,
        blank=True,
    )
    won_at = models.DateTimeField(null=True, blank=True)
    lost_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'renewals'
        unique_together = [('policy', 'due_date')]
        ordering = ['due_date']

    def __str__(self):
        return f'{self.policy.policy_number} — {self.due_date}'
# 2026-11-11T15:06:08Z risk model
# 2026-11-11T15:06:08Z motor risk
# 2026-11-11T15:06:08Z policy model
# 2026-11-11T15:06:08Z endorsement model
