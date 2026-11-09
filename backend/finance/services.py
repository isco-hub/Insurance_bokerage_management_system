from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from finance.models import InvoiceStatus, PremiumStatus


def _invoice_status(invoice):
    if invoice.amount_paid <= 0:
        if invoice.due_date < timezone.localdate() and invoice.status not in (
            InvoiceStatus.DRAFT,
            InvoiceStatus.CANCELLED,
        ):
            return InvoiceStatus.OVERDUE
        return invoice.status
    if invoice.amount_paid >= invoice.total:
        return InvoiceStatus.PAID
    return InvoiceStatus.PARTIAL


def allocate_payment(payment):
    """Allocate a confirmed payment to its invoice and policy instalments."""

    if payment.status != 'CONFIRMED':
        return

    with transaction.atomic():
        remaining = Decimal(payment.amount)

        if payment.invoice_id:
            invoice = payment.invoice
            invoice.amount_paid = min(
                invoice.total, (invoice.amount_paid or Decimal('0')) + payment.amount
            )
            invoice.status = _invoice_status(invoice)
            invoice.save(update_fields=['amount_paid', 'status', 'updated_at'])

        if payment.policy_id:
            premiums = payment.policy.premiums.filter(
                status__in=[
                    PremiumStatus.UNPAID,
                    PremiumStatus.PARTIAL,
                    PremiumStatus.OVERDUE,
                ]
            ).order_by('installment_no')
            for premium in premiums:
                if remaining <= 0:
                    break
                balance = premium.amount_due - premium.amount_paid
                if balance <= 0:
                    continue
                applied = min(balance, remaining)
                premium.amount_paid += applied
                remaining -= applied
                if premium.amount_paid >= premium.amount_due:
                    premium.status = PremiumStatus.PAID
                    premium.paid_at = timezone.now()
                else:
                    premium.status = PremiumStatus.PARTIAL
                premium.save(
                    update_fields=['amount_paid', 'status', 'paid_at', 'updated_at']
                )


def reverse_payment_allocation(payment, amount):
    """Reverse part or all of a confirmed payment's invoice and premium allocation."""

    amount = Decimal(amount)
    if amount <= 0:
        return

    with transaction.atomic():
        remaining = amount

        if payment.invoice_id:
            invoice = payment.invoice
            reduction = min(amount, invoice.amount_paid or Decimal('0'))
            invoice.amount_paid = (invoice.amount_paid or Decimal('0')) - reduction
            invoice.status = _invoice_status(invoice)
            invoice.save(update_fields=['amount_paid', 'status', 'updated_at'])

        if payment.policy_id:
            premiums = payment.policy.premiums.filter(
                amount_paid__gt=0
            ).order_by('-installment_no')
            for premium in premiums:
                if remaining <= 0:
                    break
                reduction = min(premium.amount_paid, remaining)
                premium.amount_paid -= reduction
                remaining -= reduction
                if premium.amount_paid <= 0:
                    premium.amount_paid = Decimal('0')
                    premium.status = PremiumStatus.UNPAID
                    premium.paid_at = None
                else:
                    premium.status = PremiumStatus.PARTIAL
                premium.save(
                    update_fields=['amount_paid', 'status', 'paid_at', 'updated_at']
                )
