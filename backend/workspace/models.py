import uuid

from django.conf import settings
from django.db import models


class CommChannel(models.TextChoices):
    EMAIL = 'EMAIL', 'Email'
    SMS = 'SMS', 'SMS'
    PHONE = 'PHONE', 'Phone call'
    MEETING = 'MEETING', 'Meeting'
    LETTER = 'LETTER', 'Letter'
    PORTAL = 'PORTAL', 'Portal'


class Priority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'To do'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    DONE = 'DONE', 'Done'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ApprovalType(models.TextChoices):
    QUOTATION = 'QUOTATION', 'High-value quotation'
    COMMISSION_OVERRIDE = 'COMMISSION_OVERRIDE', 'Commission override'
    ENDORSEMENT = 'ENDORSEMENT', 'Policy endorsement'
    REFUND = 'REFUND', 'Premium refund'
    CREDIT_TERMS = 'CREDIT_TERMS', 'Credit terms'
    CLAIM_SETTLEMENT = 'CLAIM_SETTLEMENT', 'Claim settlement'


class ApprovalStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=40)
    entity_id = models.UUIDField()
    name = models.CharField(max_length=180)
    category = models.CharField(max_length=60, blank=True)
    file = models.FileField(upload_to='documents/%Y/%m')
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.IntegerField(null=True, blank=True)
    version = models.IntegerField(default=1)
    is_current = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='documents_uploaded',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['entity_type', 'entity_id'])]

    def __str__(self):
        return self.name


class Communication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'crm.Client',
        on_delete=models.SET_NULL,
        related_name='communications',
        null=True,
        blank=True,
    )
    channel = models.CharField(
        max_length=20, choices=CommChannel.choices, default=CommChannel.EMAIL
    )
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    related_entity_type = models.CharField(max_length=40, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='LOGGED')
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='communications_sent',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'communications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.channel} — {self.subject or self.client_id}'


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='tasks_assigned',
    )
    related_entity_type = models.CharField(max_length=40, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='tasks_created',
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['due_date', '-priority']
        indexes = [models.Index(fields=['assigned_to', 'status'])]

    def __str__(self):
        return self.title


class Approval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=30, choices=ApprovalType.choices)
    entity_type = models.CharField(max_length=40)
    entity_id = models.UUIDField()
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='approvals_requested',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='approvals_decided',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    comments = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approvals'
        ordering = ['-requested_at']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f'{self.type} — {self.status}'
# 2026-11-11T15:06:09Z document model
# 2026-11-11T15:06:09Z task model
# 2026-11-11T15:06:09Z approval model
# 2026-11-11T15:06:09Z comms log
