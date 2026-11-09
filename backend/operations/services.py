import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.utils import timezone

from common.numbering import next_number
from finance.models import Commission, CommissionStatus, Invoice, Premium
from operations.models import (
    Policy,
    PolicyStatus,
    Quotation,
    QuotationStatus,
    Renewal,
    RenewalStatus,
    RiskStatus,
)


def to_decimal(value, default='0'):
    if value in (None, ''):
        return Decimal(default)
    return Decimal(str(value))


def money(value):
    return to_decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def stage_for(due_date: date, today: date | None = None) -> int:
    today = today or timezone.localdate()
    days = (due_date - today).days
    if days > 60:
        return 90
    if days > 30:
        return 60
    if days > 14:
        return 30
    if days > 7:
        return 14
    return 7


def installments_for(frequency: str | None) -> int:
    return {
        'ANNUAL': 1,
        'SEMI_ANNUAL': 2,
        'SEMI-ANNUAL': 2,
        'QUARTERLY': 4,
        'MONTHLY': 12,
    }.get((frequency or 'ANNUAL').upper(), 1)


def create_policy(data, user, quotation: Quotation | None = None):
    """Create a policy and all dependent financial/operational records."""

    if quotation is None:
        quotation = data.get('quotation')

    client = data.get('client') or (quotation.client if quotation else None)
    product = data.get('product') or (quotation.product if quotation else None)
    if not client or not product:
        raise ValueError('A client and product are required to create a policy')

    insurer = data.get('insurer')
    if insurer is None and quotation and quotation.selected_insurer_id:
        insurer = quotation.selected_insurer
    if insurer is None:
        insurer = product.insurer

    if quotation and quotation.selected_insurer_id:
        insurer = quotation.selected_insurer

    branch = data.get('branch')
    if branch is None and quotation:
        branch = quotation.branch
    if branch is None and getattr(user, 'branch_id', None):
        branch = user.branch
    if branch is None:
        raise ValueError('A branch is required to create a policy')

    broker = data.get('broker')
    if broker is None and quotation:
        broker = quotation.broker
    if broker is None and user:
        broker = user

    start_date = data.get('start_date') or timezone.localdate()
    end_date = data.get('end_date') or (
        add_months(start_date, 12) - timedelta(days=1)
    )
    renewal_date = data.get('renewal_date') or end_date

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if isinstance(renewal_date, str):
        renewal_date = date.fromisoformat(renewal_date)

    if end_date < start_date:
        raise ValueError('Policy end date must be after the start date')
    if end_date == start_date:
        raise ValueError('Policy end date must be after the start date (zero-duration policies are not allowed)')

    premium = money(
        data.get('premium')
        if data.get('premium') is not None
        else (quotation.premium if quotation else 0)
    )
    if premium <= 0:
        raise ValueError('Policy premium must be greater than zero')
    taxes = money(
        data.get('taxes')
        if data.get('taxes') is not None
        else (quotation.taxes if quotation else 0)
    )
    total = money(data.get('total_premium')) if data.get('total_premium') else (
        premium + taxes
    )
    sum_insured = money(
        data.get('sum_insured')
        if data.get('sum_insured') is not None
        else (quotation.sum_insured if quotation else 0)
    )
    commission_rate = data.get('commission_rate')
    commission_rate = money(
        commission_rate if commission_rate is not None else product.commission_rate
    )
    commission_amount = money(premium * commission_rate / Decimal('100'))
    status = data.get('status') or PolicyStatus.ACTIVE
    frequency = (data.get('payment_frequency') or 'ANNUAL').upper()

    attempts = 0
    while True:
        attempts += 1
        try:
            with transaction.atomic():
                policy = Policy.objects.create(
                    policy_number=next_number(Policy, 'policy_number', 'POL'),
                    client=client,
                    product=product,
                    insurer=insurer,
                    quotation=quotation,
                    branch=branch,
                    broker=broker,
                    sum_insured=sum_insured,
                    premium=premium,
                    taxes=taxes,
                    total_premium=total,
                    start_date=start_date,
                    end_date=end_date,
                    renewal_date=renewal_date,
                    status=status,
                    payment_frequency=frequency,
                    commission_rate=commission_rate,
                    commission_amount=commission_amount,
                    notes=data.get('notes') or '',
                    created_by=user if user and user.is_authenticated else None,
                )

                Invoice.objects.create(
                    invoice_number=next_number(Invoice, 'invoice_number', 'INV'),
                    client=client,
                    policy=policy,
                    issue_date=start_date,
                    due_date=start_date + timedelta(days=30),
                    subtotal=premium,
                    tax=taxes,
                    total=total,
                    status='ISSUED',
                    created_by=user if user and user.is_authenticated else None,
                )

                count = installments_for(frequency)
                base_amount = money(total / count)
                allocated = Decimal('0')
                for index in range(count):
                    if index == count - 1:
                        amount = total - allocated
                    else:
                        amount = base_amount
                        allocated += amount
                    Premium.objects.create(
                        policy=policy,
                        installment_no=index + 1,
                        amount_due=amount,
                        due_date=add_months(start_date, index),
                        status='UNPAID',
                    )

                Commission.objects.create(
                    policy=policy,
                    insurer=insurer,
                    broker=broker if broker and broker.pk else None,
                    rate=commission_rate,
                    amount=commission_amount,
                    status=(
                        CommissionStatus.EARNED
                        if status == PolicyStatus.ACTIVE
                        else CommissionStatus.PENDING
                    ),
                    earned_at=(
                        timezone.now()
                        if status == PolicyStatus.ACTIVE
                        else None
                    ),
                )

                Renewal.objects.get_or_create(
                    policy=policy,
                    due_date=renewal_date,
                    defaults={
                        'stage_days': stage_for(renewal_date),
                        'status': RenewalStatus.UPCOMING,
                        'handled_by': broker if broker and broker.pk else None,
                    },
                )

                if quotation:
                    quotation.status = QuotationStatus.ACCEPTED
                    quotation.save(update_fields=['status', 'updated_at'])
                    if quotation.risk_id:
                        quotation.risk.status = RiskStatus.CLOSED
                        quotation.risk.save(update_fields=['status', 'updated_at'])

                return policy
        except IntegrityError:
            if attempts >= 5:
                raise
