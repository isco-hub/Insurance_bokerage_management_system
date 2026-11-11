import uuid

from django.conf import settings
from django.db import models


class ClaimStatus(models.TextChoices):
    NOTIFIED = 'NOTIFIED', 'Notified'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under review'
    RESERVED = 'RESERVED', 'Reserved'
    APPROVED = 'APPROVED', 'Approved'
    PAID = 'PAID', 'Paid'
    SETTLED = 'SETTLED', 'Settled'
    REJECTED = 'REJECTED', 'Rejected'
    CLOSED = 'CLOSED', 'Closed'


class Claim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=40, unique=True)
    policy = models.ForeignKey(
        'operations.Policy', on_delete=models.RESTRICT, related_name='claims'
    )
    client = models.ForeignKey(
        'crm.Client', on_delete=models.RESTRICT, related_name='claims'
    )
    date_of_loss = models.DateField()
    reported_at = models.DateTimeField(auto_now_add=True)
    cause = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    surveyor = models.CharField(max_length=150, blank=True)
    reserve_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recovered_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=ClaimStatus.choices, default=ClaimStatus.NOTIFIED
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='claims_handled',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'claims'
        ordering = ['-reported_at']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.claim_number
# 2026-11-11T15:06:09Z claim model
