import uuid

from django.conf import settings
from django.db import models


class PremiumStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partially paid'
    PAID = 'PAID', 'Paid'
    OVERDUE = 'OVERDUE', 'Overdue'
    WAIVED = 'WAIVED', 'Waived'


class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ISSUED = 'ISSUED', 'Issued'
    PARTIAL = 'PARTIAL', 'Partially paid'
    PAID = 'PAID', 'Paid'
    OVERDUE = 'OVERDUE', 'Overdue'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Cash'
    CHEQUE = 'CHEQUE', 'Cheque'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Bank transfer'
    MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile money'
    CARD = 'CARD', 'Card'
    OTHER = 'OTHER', 'Other'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    REVERSED = 'REVERSED', 'Reversed'


class NoteType(models.TextChoices):
    CREDIT = 'CREDIT', 'Credit note'
    DEBIT = 'DEBIT', 'Debit note'


class NoteStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ISSUED = 'ISSUED', 'Issued'
    APPLIED = 'APPLIED', 'Applied'
    CANCELLED = 'CANCELLED', 'Cancelled'


class CommissionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    EARNED = 'EARNED', 'Earned'
    PAID = 'PAID', 'Paid'
    RECONCILED = 'RECONCILED', 'Reconciled'
    CANCELLED = 'CANCELLED', 'Cancelled'


class RemittanceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING = 'PENDING', 'Pending'
    PAID = 'PAID', 'Paid'
    RECONCILED = 'RECONCILED', 'Reconciled'


class Premium(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        'operations.Policy', on_delete=models.CASCADE, related_name='premiums'
    )
    installment_no = models.IntegerField(default=1)
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=PremiumStatus.choices, default=PremiumStatus.UNPAID
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'premiums'
        unique_together = [('policy', 'installment_no')]
        ordering = ['due_date', 'installment_no']
        indexes = [models.Index(fields=['status', 'due_date'])]

    def __str__(self):
        return f'{self.policy.policy_number} #{self.installment_no}'

    @property
    def balance(self):
        return self.amount_due - self.amount_paid


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=40, unique=True)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='invoices'
    )
    policy = models.ForeignKey(
        'operations.Policy',
        on_delete=models.SET_NULL,
        related_name='invoices',
        null=True,
        blank=True,
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='invoices_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-issue_date']
        indexes = [models.Index(fields=['status', 'due_date'])]

    def __str__(self):
        return self.invoice_number

    @property
    def balance(self):
        return self.total - self.amount_paid


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_number = models.CharField(max_length=40, unique=True)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='payments'
    )
    policy = models.ForeignKey(
        'operations.Policy',
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.CONFIRMED
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payments_received',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    refunded_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-paid_at']
        indexes = [models.Index(fields=['client']), models.Index(fields=['policy'])]

    def __str__(self):
        return self.receipt_number


class CreditDebitNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note_number = models.CharField(max_length=40, unique=True)
    note_type = models.CharField(max_length=10, choices=NoteType.choices)
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='credit_debit_notes'
    )
    policy = models.ForeignKey(
        'operations.Policy',
        on_delete=models.SET_NULL,
        related_name='credit_debit_notes',
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=NoteStatus.choices, default=NoteStatus.DRAFT
    )
    issue_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='notes_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credit_debit_notes'
        ordering = ['-issue_date']

    def __str__(self):
        return self.note_number


class Commission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        'operations.Policy', on_delete=models.CASCADE, related_name='commissions'
    )
    insurer = models.ForeignKey(
        'crm.Insurer', on_delete=models.RESTRICT, related_name='commissions'
    )
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='commissions',
        null=True,
        blank=True,
    )
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=CommissionStatus.choices,
        default=CommissionStatus.PENDING,
    )
    earned_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commissions'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'earned_at'])]

    def __str__(self):
        return f'{self.policy.policy_number} — {self.amount}'


class Remittance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    remittance_number = models.CharField(max_length=40, unique=True)
    insurer = models.ForeignKey(
        'crm.Insurer', on_delete=models.RESTRICT, related_name='remittances'
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        related_name='remittances',
        null=True,
        blank=True,
    )
    period_from = models.DateField()
    period_to = models.DateField()
    gross_premium = models.DecimalField(max_digits=14, decimal_places=2)
    commission_retained = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    taxes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=RemittanceStatus.choices,
        default=RemittanceStatus.DRAFT,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    matched_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    matched_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='remittances_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'remittances'
        ordering = ['-period_to']

    def __str__(self):
        return self.remittance_number
# 2026-11-11T15:06:08Z invoice model
