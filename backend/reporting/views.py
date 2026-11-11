import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.http import HttpResponse
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog, User
from common.audit import log_action
from claims.models import Claim
from crm.models import Client
from finance.models import (
    Commission,
    CreditDebitNote,
    Invoice,
    Payment,
    Premium,
    Remittance,
)
from operations.models import Policy, Quotation, Renewal
from operations.serializers import RenewalSerializer
from workspace.models import Approval, Task, TaskStatus
from workspace.serializers import TaskSerializer

BRANCH_SCOPED_ROLES = {'BRANCH', 'BROKER', 'SERVICE'}


def num(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def is_scoped(user):
    role = getattr(user, 'role', None)
    return bool(role and role.code in BRANCH_SCOPED_ROLES and user.branch_id)


def scope(qs, user, field):
    if is_scoped(user):
        return qs.filter(**{field: user.branch_id})
    return qs


def sum_or_zero(qs, field):
    return num(qs.aggregate(total=Sum(field))['total'])


class DashboardView(APIView):
    def get_required_permission(self):
        return 'dashboard:view'

    def get(self, request):
        today = timezone.localdate()
        year = today.year
        user = request.user
        policies = scope(Policy.objects.all(), user, 'branch')
        clients = scope(
            Client.objects.filter(is_active=True, deleted_at__isnull=True),
            user,
            'branch',
        )
        premiums = scope(Premium.objects.all(), user, 'policy__branch')
        commissions = scope(Commission.objects.all(), user, 'policy__branch')
        claims = scope(Claim.objects.all(), user, 'policy__branch')
        renewals = scope(Renewal.objects.all(), user, 'policy__branch')
        tasks = Task.objects.all()
        role_code = getattr(getattr(user, 'role', None), 'code', '')
        if is_scoped(user) and role_code in ('BROKER', 'SERVICE'):
            tasks = tasks.filter(assigned_to=user)

        outstanding_premium = sum_or_zero(
            premiums.filter(status__in=['UNPAID', 'PARTIAL', 'OVERDUE']),
            'amount_due',
        ) - sum_or_zero(
            premiums.filter(status__in=['UNPAID', 'PARTIAL', 'OVERDUE']),
            'amount_paid',
        )
        outstanding_commission = num(
            commissions.filter(status__in=['PENDING', 'EARNED']).aggregate(
                total=Sum('amount')
            )['total']
        )

        kpis = {
            'active_clients': clients.count(),
            'active_policies': policies.filter(status='ACTIVE').count(),
            'total_policies': policies.count(),
            'premium_placed_ytd': sum_or_zero(
                policies.filter(start_date__year=year), 'total_premium'
            ),
            'brokerage_earned_ytd': num(
                commissions.filter(earned_at__year=year).aggregate(
                    total=Sum('amount')
                )['total']
            ),
            'outstanding_premium': outstanding_premium,
            'outstanding_commission': outstanding_commission,
            'open_claims': claims.exclude(
                status__in=['SETTLED', 'REJECTED', 'CLOSED']
            ).count(),
            'renewals_due_90': renewals.filter(
                due_date__lte=today + timedelta(days=90),
                status__in=['UPCOMING', 'DUE', 'QUOTED'],
            ).count(),
            'new_business_month': policies.filter(
                start_date__year=today.year, start_date__month=today.month
            ).count(),
            'pending_approvals': Approval.objects.filter(status='PENDING').count(),
            'overdue_tasks': tasks.filter(
                due_date__lt=today,
                status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
            ).count(),
            'claims_reserve': sum_or_zero(
                claims.exclude(status__in=['SETTLED', 'REJECTED', 'CLOSED']),
                'reserve_amount',
            ),
        }

        by_class = [
            {
                'name': row['product__insurance_class__name'] or 'Unclassified',
                'count': row['count'],
                'premium': num(row['premium']),
            }
            for row in policies.values('product__insurance_class__name')
            .annotate(count=Count('id'), premium=Sum('total_premium'))
            .order_by('-premium')
        ]

        by_insurer = [
            {
                'name': row['insurer__name'],
                'count': row['count'],
                'premium': num(row['premium']),
            }
            for row in policies.values('insurer__name')
            .annotate(count=Count('id'), premium=Sum('total_premium'))
            .order_by('-premium')
        ]

        by_broker = [
            {
                'name': ' '.join(
                    filter(
                        None,
                        [row['broker__first_name'], row['broker__last_name']],
                    )
                )
                or 'Unassigned',
                'count': row['count'],
                'premium': num(row['premium']),
            }
            for row in policies.values('broker__first_name', 'broker__last_name')
            .annotate(count=Count('id'), premium=Sum('total_premium'))
            .order_by('-premium')
        ]

        premium_by_month = [
            {
                'month': row['month'].strftime('%Y-%m') if row['month'] else '',
                'premium': num(row['premium']),
                'count': row['count'],
            }
            for row in policies.filter(start_date__year=year)
            .annotate(month=TruncMonth('start_date'))
            .values('month')
            .annotate(premium=Sum('total_premium'), count=Count('id'))
            .order_by('month')
        ]

        claims_by_status = [
            {
                'status': row['status'],
                'count': row['count'],
                'reserve': num(row['reserve']),
                'paid': num(row['paid']),
            }
            for row in claims.values('status').annotate(
                count=Count('id'),
                reserve=Sum('reserve_amount'),
                paid=Sum('paid_amount'),
            )
        ]

        renewal_pipeline = [
            {'status': row['status'], 'count': row['count']}
            for row in renewals.values('status').annotate(count=Count('id'))
        ]

        renewals_due = Renewal.objects.select_related(
            'policy', 'policy__client', 'policy__insurer', 'policy__product'
        ).filter(
            due_date__lte=today + timedelta(days=90),
            status__in=['UPCOMING', 'DUE', 'QUOTED'],
        )
        renewals_due = scope(renewals_due, user, 'policy__branch').order_by(
            'due_date'
        )[:8]

        tasks_due = tasks.filter(
            status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS]
        ).order_by('due_date')[:8]

        recent = AuditLog.objects.select_related('user').all()[:10]

        return Response(
            {
                'data': {
                    'kpis': kpis,
                    'charts': {
                        'policies_by_class': by_class,
                        'business_by_insurer': by_insurer,
                        'business_by_broker': by_broker,
                        'premium_by_month': premium_by_month,
                        'claims_by_status': claims_by_status,
                        'renewal_pipeline': renewal_pipeline,
                    },
                    'renewals_due': RenewalSerializer(
                        renewals_due, many=True, context={'request': request}
                    ).data,
                    'tasks_due': TaskSerializer(
                        tasks_due, many=True, context={'request': request}
                    ).data,
                    'recent_activity': [
                        {
                            'id': str(log.id),
                            'action': log.action,
                            'module': log.module,
                            'description': log.description,
                            'user': log.user.full_name if log.user else log.user_email,
                            'created_at': log.created_at,
                        }
                        for log in recent
                    ],
                }
            }
        )


class ReportsView(APIView):
    def get_required_permission(self):
        return 'reports:view'

    def get(self, request, report):
        handler = getattr(self, f'report_{report.replace("-", "_")}', None)
        if not handler:
            return Response(
                {'statusCode': 404, 'message': 'Unknown report'}, status=404
            )
        return handler(request)

    def _date_filters(self, qs, request, field):
        date_from = parse_date(request.query_params.get('from'))
        date_to = parse_date(request.query_params.get('to'))
        if date_from:
            qs = qs.filter(**{f'{field}__gte': date_from})
        if date_to:
            qs = qs.filter(**{f'{field}__lte': date_to})
        return qs

    def report_premium_production(self, request):
        qs = self._date_filters(
            scope(Policy.objects.all(), request.user, 'branch'),
            request,
            'start_date',
        )
        rows = [
            {
                'policy_number': p.policy_number,
                'client': p.client.name,
                'insurer': p.insurer.name,
                'product': p.product.name,
                'class': p.product.insurance_class.name,
                'branch': p.branch.name,
                'broker': p.broker.full_name if p.broker else '',
                'premium': num(p.premium),
                'taxes': num(p.taxes),
                'total_premium': num(p.total_premium),
                'start_date': p.start_date,
                'status': p.status,
            }
            for p in qs.select_related(
                'client', 'insurer', 'product', 'product__insurance_class', 'branch', 'broker'
            ).order_by('-start_date')[:500]
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'premium': sum_or_zero(qs, 'premium'),
                        'taxes': sum_or_zero(qs, 'taxes'),
                        'total_premium': sum_or_zero(qs, 'total_premium'),
                    },
                }
            }
        )

    def report_business_mix(self, request):
        qs = self._date_filters(
            scope(Policy.objects.all(), request.user, 'branch'),
            request,
            'start_date',
        )
        dimensions = {
            'by_insurer': 'insurer__name',
            'by_class': 'product__insurance_class__name',
            'by_branch': 'branch__name',
            'by_broker': 'broker__first_name',
            'by_product': 'product__name',
        }
        result = {}
        for key, field in dimensions.items():
            result[key] = [
                {
                    'name': row[field] or 'Unassigned',
                    'count': row['count'],
                    'premium': num(row['premium']),
                }
                for row in qs.values(field)
                .annotate(count=Count('id'), premium=Sum('total_premium'))
                .order_by('-premium')
            ]
        return Response({'data': result})

    def report_commission(self, request):
        qs = self._date_filters(
            scope(Commission.objects.all(), request.user, 'policy__branch'),
            request,
            'earned_at__date',
        )
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        rows = [
            {
                'policy_number': c.policy.policy_number,
                'client': c.policy.client.name,
                'insurer': c.insurer.name,
                'broker': c.broker.full_name if c.broker else '',
                'rate': num(c.rate),
                'amount': num(c.amount),
                'status': c.status,
                'earned_at': c.earned_at,
            }
            for c in qs.select_related(
                'policy', 'policy__client', 'insurer', 'broker'
            ).order_by('-created_at')[:500]
        ]
        by_status = [
            {'status': row['status'], 'count': row['count'], 'amount': num(row['amount'])}
            for row in qs.values('status').annotate(
                count=Count('id'), amount=Sum('amount')
            )
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'amount': sum_or_zero(qs, 'amount'),
                        'by_status': by_status,
                    },
                }
            }
        )

    def report_commission_statement(self, request):
        qs = self._date_filters(
            scope(Commission.objects.all(), request.user, 'policy__branch'),
            request,
            'earned_at__date',
        )
        for param, field in (
            ('insurer', 'insurer_id'),
            ('broker', 'broker_id'),
            ('status', 'status'),
            ('policy', 'policy_id'),
        ):
            value = request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        qs = qs.select_related(
            'policy',
            'policy__client',
            'policy__product',
            'policy__product__insurance_class',
            'insurer',
            'broker',
        )

        def grouped(field, label):
            return [
                {
                    label: row[field] or 'Unassigned',
                    'count': row['count'],
                    'amount': num(row['total_amount']),
                    'outstanding': num(row['total_outstanding']),
                    'paid': num(row['total_paid']),
                }
                for row in qs.values(field)
                .annotate(
                    count=Count('id'),
                    total_amount=Sum('amount'),
                    total_outstanding=Sum(
                        'amount',
                        filter=Q(status__in=['PENDING', 'EARNED']),
                    ),
                    total_paid=Sum(
                        'amount',
                        filter=Q(status__in=['PAID', 'RECONCILED']),
                    ),
                )
                .order_by('-total_amount')
            ]

        rows = [
            {
                'policy_number': c.policy.policy_number,
                'client': c.policy.client.name,
                'insurer': c.insurer.name,
                'class': c.policy.product.insurance_class.name,
                'product': c.policy.product.name,
                'broker': c.broker.full_name if c.broker else '',
                'rate': num(c.rate),
                'amount': num(c.amount),
                'status': c.status,
                'earned_at': c.earned_at,
                'paid_at': c.paid_at,
            }
            for c in qs.order_by('-earned_at', '-created_at')[:500]
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'amount': sum_or_zero(qs, 'amount'),
                        'outstanding': num(
                            qs.filter(status__in=['PENDING', 'EARNED']).aggregate(
                                total=Sum('amount')
                            )['total']
                        ),
                        'paid': num(
                            qs.filter(status__in=['PAID', 'RECONCILED']).aggregate(
                                total=Sum('amount')
                            )['total']
                        ),
                    },
                    'by_insurer': grouped('insurer__name', 'insurer'),
                    'by_class': grouped(
                        'policy__product__insurance_class__name', 'class'
                    ),
                    'by_product': grouped('policy__product__name', 'product'),
                }
            }
        )

    def report_remittance_reconciliation(self, request):
        qs = self._date_filters(
            scope(Remittance.objects.all(), request.user, 'branch'),
            request,
            'period_to',
        )
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        insurer = request.query_params.get('insurer')
        if insurer:
            qs = qs.filter(insurer_id=insurer)
        qs = qs.select_related('insurer', 'branch')
        rows = []
        for remittance in qs.order_by('-period_to')[:500]:
            matched = (
                remittance.matched_amount
                if remittance.matched_amount is not None
                else Decimal('0')
            )
            rows.append(
                {
                    'remittance_number': remittance.remittance_number,
                    'insurer': remittance.insurer.name,
                    'branch': remittance.branch.name if remittance.branch else '',
                    'period_from': remittance.period_from,
                    'period_to': remittance.period_to,
                    'gross_premium': num(remittance.gross_premium),
                    'commission_retained': num(remittance.commission_retained),
                    'taxes': num(remittance.taxes),
                    'net_amount': num(remittance.net_amount),
                    'matched_amount': num(matched),
                    'difference': num(remittance.net_amount - matched),
                    'status': remittance.status,
                    'bank_reference': remittance.bank_reference,
                    'paid_at': remittance.paid_at,
                }
            )
        by_status = [
            {
                'status': row['status'],
                'count': row['count'],
                'net_amount': num(row['net_amount']),
            }
            for row in qs.values('status').annotate(
                count=Count('id'), net_amount=Sum('net_amount')
            )
        ]
        matched_total = sum(
            (Decimal(str(row['matched_amount'])) for row in rows),
            Decimal('0'),
        )
        net_total = sum((Decimal(str(row['net_amount'])) for row in rows), Decimal('0'))
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': len(rows),
                        'gross_premium': sum_or_zero(qs, 'gross_premium'),
                        'commission_retained': sum_or_zero(
                            qs, 'commission_retained'
                        ),
                        'net_amount': num(net_total),
                        'matched_amount': num(matched_total),
                        'difference': num(net_total - matched_total),
                    },
                    'by_status': by_status,
                }
            }
        )

    def report_debtors_ageing(self, request):
        today = timezone.localdate()
        qs = scope(
            Invoice.objects.exclude(status__in=['PAID', 'CANCELLED']),
            request.user,
            'client__branch',
        ).select_related('client', 'policy')
        buckets = {
            'Not due': {'amount': Decimal('0'), 'count': 0},
            '0-30': {'amount': Decimal('0'), 'count': 0},
            '31-60': {'amount': Decimal('0'), 'count': 0},
            '61-90': {'amount': Decimal('0'), 'count': 0},
            '91-180': {'amount': Decimal('0'), 'count': 0},
            '180+': {'amount': Decimal('0'), 'count': 0},
        }
        rows = []
        for invoice in qs:
            balance = invoice.total - invoice.amount_paid
            if balance <= 0:
                continue
            overdue_days = (today - invoice.due_date).days
            if overdue_days <= 0:
                bucket = 'Not due'
            elif overdue_days <= 30:
                bucket = '0-30'
            elif overdue_days <= 60:
                bucket = '31-60'
            elif overdue_days <= 90:
                bucket = '61-90'
            elif overdue_days <= 180:
                bucket = '91-180'
            else:
                bucket = '180+'
            buckets[bucket]['amount'] += balance
            buckets[bucket]['count'] += 1
            rows.append(
                {
                    'invoice_number': invoice.invoice_number,
                    'client': invoice.client.name,
                    'policy': invoice.policy.policy_number if invoice.policy else '',
                    'issue_date': invoice.issue_date,
                    'due_date': invoice.due_date,
                    'days_overdue': max(0, overdue_days),
                    'total': num(invoice.total),
                    'paid': num(invoice.amount_paid),
                    'balance': num(balance),
                    'bucket': bucket,
                    'status': invoice.status,
                }
            )
        rows.sort(key=lambda row: (-row['days_overdue'], row['invoice_number']))
        return Response(
            {
                'data': {
                    'rows': rows[:500],
                    'summary': {
                        'count': len(rows),
                        'balance': num(
                            sum(
                                (Decimal(str(row['balance'])) for row in rows),
                                Decimal('0'),
                            )
                        ),
                    },
                    'buckets': [
                        {
                            'bucket': key,
                            'count': value['count'],
                            'amount': num(value['amount']),
                        }
                        for key, value in buckets.items()
                    ],
                }
            }
        )

    def report_quotation_conversion(self, request):
        qs = self._date_filters(
            scope(Quotation.objects.all(), request.user, 'branch'),
            request,
            'created_at__date',
        )
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        broker = request.query_params.get('broker')
        if broker:
            qs = qs.filter(broker_id=broker)
        qs = qs.select_related(
            'client',
            'broker',
            'product',
            'product__insurance_class',
            'branch',
            'selected_insurer',
        )
        total = qs.count()
        accepted = qs.filter(status='ACCEPTED').count()
        declined = qs.filter(status='DECLINED').count()
        by_status = [
            {
                'status': row['status'],
                'count': row['count'],
                'premium': num(row['premium']),
            }
            for row in qs.values('status').annotate(
                count=Count('id'), premium=Sum('total_premium')
            )
        ]
        by_broker = [
            {
                'broker': row['broker__first_name'] or 'Unassigned',
                'count': row['count'],
                'accepted': row['accepted'],
                'premium': num(row['premium']),
            }
            for row in qs.values('broker__first_name').annotate(
                count=Count('id'),
                accepted=Count('id', filter=Q(status='ACCEPTED')),
                premium=Sum('total_premium'),
            )
        ]
        by_class = [
            {
                'class': row['product__insurance_class__name'] or 'Unclassified',
                'count': row['count'],
                'accepted': row['accepted'],
                'premium': num(row['premium']),
            }
            for row in qs.values('product__insurance_class__name').annotate(
                count=Count('id'),
                accepted=Count('id', filter=Q(status='ACCEPTED')),
                premium=Sum('total_premium'),
            )
        ]
        rows = [
            {
                'quotation_number': quotation.quotation_number,
                'client': quotation.client.name,
                'product': quotation.product.name,
                'class': quotation.product.insurance_class.name,
                'broker': quotation.broker.full_name if quotation.broker else '',
                'insurer': (
                    quotation.selected_insurer.name
                    if quotation.selected_insurer
                    else ''
                ),
                'total_premium': num(quotation.total_premium),
                'status': quotation.status,
                'valid_to': quotation.valid_to,
                'created_at': quotation.created_at,
            }
            for quotation in qs.order_by('-created_at')[:500]
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'total': total,
                        'accepted': accepted,
                        'declined': declined,
                        'open': total - accepted - declined,
                        'conversion_rate': (
                            num(round((accepted / total) * 100, 2))
                            if total
                            else 0
                        ),
                    },
                    'by_status': by_status,
                    'by_broker': by_broker,
                    'by_class': by_class,
                }
            }
        )

    def report_claim_analysis(self, request):
        qs = scope(Claim.objects.all(), request.user, 'policy__branch')
        qs = self._date_filters(qs, request, 'date_of_loss')
        qs = qs.select_related(
            'policy',
            'policy__insurer',
            'policy__product',
            'policy__product__insurance_class',
            'client',
        )
        rows = [
            {
                'claim_number': claim.claim_number,
                'client': claim.client.name,
                'policy_number': claim.policy.policy_number,
                'insurer': claim.policy.insurer.name,
                'class': claim.policy.product.insurance_class.name,
                'date_of_loss': claim.date_of_loss,
                'reserve': num(claim.reserve_amount),
                'paid': num(claim.paid_amount),
                'recovered': num(claim.recovered_amount),
                'status': claim.status,
            }
            for claim in qs.order_by('-date_of_loss')[:500]
        ]

        def grouped(field, label):
            return [
                {
                    label: row[field] or 'Unassigned',
                    'count': row['count'],
                    'reserve': num(row['reserve']),
                    'paid': num(row['paid']),
                    'recovered': num(row['recovered']),
                }
                for row in qs.values(field).annotate(
                    count=Count('id'),
                    reserve=Sum('reserve_amount'),
                    paid=Sum('paid_amount'),
                    recovered=Sum('recovered_amount'),
                )
            ]

        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'reserve': sum_or_zero(qs, 'reserve_amount'),
                        'paid': sum_or_zero(qs, 'paid_amount'),
                        'recovered': sum_or_zero(qs, 'recovered_amount'),
                    },
                    'by_insurer': grouped('policy__insurer__name', 'insurer'),
                    'by_class': grouped(
                        'policy__product__insurance_class__name', 'class'
                    ),
                    'by_status': grouped('status', 'status'),
                }
            }
        )

    def report_business_by_client(self, request):
        qs = self._date_filters(
            scope(Policy.objects.all(), request.user, 'branch'),
            request,
            'start_date',
        )
        rows = [
            {
                'client_number': row['client__client_number'],
                'client': row['client__name'],
                'policies': row['count'],
                'premium': num(row['premium']),
                'commission': num(row['commission']),
            }
            for row in qs.values('client__client_number', 'client__name')
            .annotate(
                count=Count('id'),
                premium=Sum('total_premium'),
                commission=Sum('commission_amount'),
            )
            .order_by('-premium')
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'clients': len(rows),
                        'policies': qs.count(),
                        'premium': sum_or_zero(qs, 'total_premium'),
                        'commission': sum_or_zero(qs, 'commission_amount'),
                    },
                }
            }
        )

    def report_policy_register(self, request):
        qs = self._date_filters(
            scope(Policy.objects.all(), request.user, 'branch'),
            request,
            'start_date',
        )
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        insurer = request.query_params.get('insurer')
        if insurer:
            qs = qs.filter(insurer_id=insurer)
        qs = qs.select_related(
            'client',
            'insurer',
            'product',
            'product__insurance_class',
            'branch',
            'broker',
        )
        rows = [
            {
                'policy_number': policy.policy_number,
                'client': policy.client.name,
                'insurer': policy.insurer.name,
                'product': policy.product.name,
                'class': policy.product.insurance_class.name,
                'branch': policy.branch.name,
                'broker': policy.broker.full_name if policy.broker else '',
                'start_date': policy.start_date,
                'end_date': policy.end_date,
                'total_premium': num(policy.total_premium),
                'commission_rate': num(policy.commission_rate),
                'commission_amount': num(policy.commission_amount),
                'status': policy.status,
            }
            for policy in qs.order_by('-start_date')[:500]
        ]
        by_status = [
            {'status': row['status'], 'count': row['count']}
            for row in qs.values('status').annotate(count=Count('id'))
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'premium': sum_or_zero(qs, 'total_premium'),
                        'commission': sum_or_zero(qs, 'commission_amount'),
                    },
                    'by_status': by_status,
                }
            }
        )

    def report_commission_ageing(self, request):
        today = timezone.localdate()
        qs = scope(
            Commission.objects.filter(status__in=['PENDING', 'EARNED']),
            request.user,
            'policy__branch',
        ).select_related('policy', 'policy__client', 'insurer', 'broker')
        buckets = {
            '0-30': {'amount': Decimal('0'), 'count': 0},
            '31-60': {'amount': Decimal('0'), 'count': 0},
            '61-90': {'amount': Decimal('0'), 'count': 0},
            '91-180': {'amount': Decimal('0'), 'count': 0},
            '180+': {'amount': Decimal('0'), 'count': 0},
        }
        rows = []
        for commission in qs:
            base = (
                commission.earned_at.date()
                if commission.earned_at
                else commission.created_at.date()
            )
            days = max(0, (today - base).days)
            if days <= 30:
                bucket = '0-30'
            elif days <= 60:
                bucket = '31-60'
            elif days <= 90:
                bucket = '61-90'
            elif days <= 180:
                bucket = '91-180'
            else:
                bucket = '180+'
            buckets[bucket]['amount'] += commission.amount
            buckets[bucket]['count'] += 1
            rows.append(
                {
                    'policy_number': commission.policy.policy_number,
                    'client': commission.policy.client.name,
                    'insurer': commission.insurer.name,
                    'amount': num(commission.amount),
                    'days': days,
                    'bucket': bucket,
                }
            )
        return Response(
            {
                'data': {
                    'buckets': [
                        {
                            'bucket': key,
                            'count': value['count'],
                            'amount': num(value['amount']),
                        }
                        for key, value in buckets.items()
                    ],
                    'rows': rows[:500],
                }
            }
        )

    def report_premium_collections(self, request):
        qs = scope(Payment.objects.all(), request.user, 'client__branch')
        date_from = parse_date(request.query_params.get('from'))
        date_to = parse_date(request.query_params.get('to'))
        if date_from:
            qs = qs.filter(paid_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(paid_at__date__lte=date_to)
        by_method = [
            {
                'method': row['method'],
                'count': row['count'],
                'amount': num(row['amount']),
            }
            for row in qs.values('method').annotate(
                count=Count('id'), amount=Sum('amount')
            )
        ]
        rows = [
            {
                'receipt_number': p.receipt_number,
                'client': p.client.name,
                'policy': p.policy.policy_number if p.policy else '',
                'amount': num(p.amount),
                'method': p.method,
                'paid_at': p.paid_at,
                'status': p.status,
            }
            for p in qs.select_related('client', 'policy').order_by('-paid_at')[:500]
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'amount': sum_or_zero(qs, 'amount'),
                        'by_method': by_method,
                    },
                }
            }
        )

    def report_outstanding_premiums(self, request):
        qs = scope(
            Premium.objects.filter(
                status__in=['UNPAID', 'PARTIAL', 'OVERDUE']
            ).exclude(amount_due=F('amount_paid')),
            request.user,
            'policy__branch',
        ).select_related('policy', 'policy__client', 'policy__insurer')
        rows = []
        by_client = {}
        for premium in qs:
            balance = premium.amount_due - premium.amount_paid
            if balance <= 0:
                continue
            client_name = premium.policy.client.name
            by_client[client_name] = by_client.get(client_name, Decimal('0')) + balance
            rows.append(
                {
                    'policy_number': premium.policy.policy_number,
                    'client': client_name,
                    'insurer': premium.policy.insurer.name,
                    'installment_no': premium.installment_no,
                    'due_date': premium.due_date,
                    'balance': num(balance),
                    'status': premium.status,
                }
            )
        total = sum(by_client.values(), Decimal('0'))
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'total': num(total),
                        'count': len(rows),
                        'by_client': [
                            {'client': name, 'balance': num(amount)}
                            for name, amount in sorted(
                                by_client.items(), key=lambda item: item[1], reverse=True
                            )
                        ],
                    },
                }
            }
        )

    def report_outstanding_debtors(self, request):
        qs = scope(
            Invoice.objects.exclude(status__in=['PAID', 'CANCELLED']),
            request.user,
            'client__branch',
        ).select_related('client', 'policy')
        rows = [
            {
                'invoice_number': invoice.invoice_number,
                'client': invoice.client.name,
                'policy': invoice.policy.policy_number if invoice.policy else '',
                'issue_date': invoice.issue_date,
                'due_date': invoice.due_date,
                'total': num(invoice.total),
                'paid': num(invoice.amount_paid),
                'balance': num(invoice.total - invoice.amount_paid),
                'status': invoice.status,
            }
            for invoice in qs
            if invoice.total > invoice.amount_paid
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': len(rows),
                        'balance': num(
                            sum(
                                (
                                    invoice.total - invoice.amount_paid
                                    for invoice in qs
                                    if invoice.total > invoice.amount_paid
                                ),
                                Decimal('0'),
                            )
                        ),
                    },
                }
            }
        )

    def report_claims(self, request):
        qs = scope(Claim.objects.all(), request.user, 'policy__branch')
        date_from = parse_date(request.query_params.get('from'))
        date_to = parse_date(request.query_params.get('to'))
        if date_from:
            qs = qs.filter(date_of_loss__gte=date_from)
        if date_to:
            qs = qs.filter(date_of_loss__lte=date_to)
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        rows = [
            {
                'claim_number': c.claim_number,
                'policy_number': c.policy.policy_number,
                'client': c.client.name,
                'insurer': c.policy.insurer.name,
                'date_of_loss': c.date_of_loss,
                'cause': c.cause,
                'reserve': num(c.reserve_amount),
                'paid': num(c.paid_amount),
                'recovered': num(c.recovered_amount),
                'status': c.status,
            }
            for c in qs.select_related(
                'policy', 'client', 'policy__insurer'
            ).order_by('-date_of_loss')[:500]
        ]
        by_status = [
            {
                'status': row['status'],
                'count': row['count'],
                'reserve': num(row['reserve']),
                'paid': num(row['paid']),
            }
            for row in qs.values('status').annotate(
                count=Count('id'),
                reserve=Sum('reserve_amount'),
                paid=Sum('paid_amount'),
            )
        ]
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': qs.count(),
                        'reserve': sum_or_zero(qs, 'reserve_amount'),
                        'paid': sum_or_zero(qs, 'paid_amount'),
                        'recovered': sum_or_zero(qs, 'recovered_amount'),
                        'by_status': by_status,
                    },
                }
            }
        )

    def report_renewals(self, request):
        qs = scope(Renewal.objects.all(), request.user, 'policy__branch')
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        rows = [
            {
                'policy_number': r.policy.policy_number,
                'client': r.policy.client.name,
                'insurer': r.policy.insurer.name,
                'due_date': r.due_date,
                'days_to_due': (r.due_date - timezone.localdate()).days,
                'status': r.status,
                'lost_reason': r.lost_reason,
            }
            for r in qs.select_related(
                'policy', 'policy__client', 'policy__insurer'
            ).order_by('due_date')[:500]
        ]
        by_status = [
            {'status': row['status'], 'count': row['count']}
            for row in qs.values('status').annotate(count=Count('id'))
        ]
        return Response(
            {'data': {'rows': rows, 'summary': {'by_status': by_status}}}
        )

    def report_staff_performance(self, request):
        users = User.objects.filter(is_active=True).select_related('role')
        rows = []
        for user in users:
            quotations = Quotation.objects.filter(broker=user).count()
            policies = Policy.objects.filter(broker=user)
            commissions = Commission.objects.filter(broker=user)
            tasks_done = Task.objects.filter(
                assigned_to=user, status=TaskStatus.DONE
            ).count()
            rows.append(
                {
                    'name': user.full_name,
                    'role': user.role.name if user.role else '',
                    'quotations': quotations,
                    'policies': policies.count(),
                    'premium': num(
                        policies.aggregate(total=Sum('total_premium'))['total']
                    ),
                    'commission': num(
                        commissions.aggregate(total=Sum('amount'))['total']
                    ),
                    'tasks_completed': tasks_done,
                }
            )
        return Response({'data': {'rows': rows}})

    def report_expiring_policies(self, request):
        today = timezone.localdate()
        days = int(request.query_params.get('days') or 60)
        qs = scope(
            Policy.objects.filter(
                status='ACTIVE', end_date__gte=today, end_date__lte=today + timedelta(days=days)
            ),
            request.user,
            'branch',
        ).select_related('client', 'insurer', 'product')
        rows = [
            {
                'policy_number': p.policy_number,
                'client': p.client.name,
                'insurer': p.insurer.name,
                'product': p.product.name,
                'end_date': p.end_date,
                'days_to_expiry': (p.end_date - today).days,
                'premium': num(p.total_premium),
            }
            for p in qs.order_by('end_date')
        ]
        return Response({'data': {'rows': rows}})

    def report_lost_business(self, request):
        qs = scope(
            Renewal.objects.filter(status='LOST'),
            request.user,
            'policy__branch',
        ).select_related('policy', 'policy__client', 'policy__insurer')
        rows = [
            {
                'policy_number': r.policy.policy_number,
                'client': r.policy.client.name,
                'insurer': r.policy.insurer.name,
                'due_date': r.due_date,
                'lost_reason': r.lost_reason,
                'lost_at': r.lost_at,
            }
            for r in qs
        ]
        return Response({'data': {'rows': rows}})

    def report_accounting(self, request):
        date_from = parse_date(request.query_params.get('from'))
        date_to = parse_date(request.query_params.get('to'))

        def filtered(qs, field):
            if date_from:
                qs = qs.filter(**{f'{field}__gte': date_from})
            if date_to:
                qs = qs.filter(**{f'{field}__lte': date_to})
            return qs

        rows = []
        invoices = filtered(
            scope(Invoice.objects.all(), request.user, 'client__branch'),
            'issue_date',
        ).select_related('client', 'policy')
        for invoice in invoices.order_by('-issue_date')[:500]:
            rows.append(
                {
                    'date': invoice.issue_date,
                    'type': 'Invoice',
                    'reference': invoice.invoice_number,
                    'client': invoice.client.name,
                    'policy': invoice.policy.policy_number if invoice.policy else '',
                    'debit': num(invoice.total),
                    'credit': 0.0,
                    'status': invoice.status,
                }
            )

        payments = scope(Payment.objects.all(), request.user, 'client__branch')
        if date_from:
            payments = payments.filter(paid_at__date__gte=date_from)
        if date_to:
            payments = payments.filter(paid_at__date__lte=date_to)
        for payment in payments.select_related('client', 'policy').order_by('-paid_at')[:500]:
            rows.append(
                {
                    'date': payment.paid_at.date() if payment.paid_at else '',
                    'type': 'Receipt',
                    'reference': payment.receipt_number,
                    'client': payment.client.name,
                    'policy': payment.policy.policy_number if payment.policy else '',
                    'debit': 0.0,
                    'credit': num(payment.amount),
                    'status': payment.status,
                }
            )

        notes = filtered(
            scope(CreditDebitNote.objects.all(), request.user, 'client__branch'),
            'issue_date',
        ).select_related('client', 'policy')
        for note in notes.order_by('-issue_date')[:500]:
            is_credit = note.note_type == 'CREDIT'
            rows.append(
                {
                    'date': note.issue_date,
                    'type': 'Credit note' if is_credit else 'Debit note',
                    'reference': note.note_number,
                    'client': note.client.name,
                    'policy': note.policy.policy_number if note.policy else '',
                    'debit': 0.0 if is_credit else num(note.amount),
                    'credit': num(note.amount) if is_credit else 0.0,
                    'status': note.status,
                }
            )

        rows.sort(key=lambda row: str(row['date']), reverse=True)
        return Response(
            {
                'data': {
                    'rows': rows,
                    'summary': {
                        'count': len(rows),
                        'debit': sum(row['debit'] for row in rows),
                        'credit': sum(row['credit'] for row in rows),
                    },
                }
            }
        )

    def report_audit_summary(self, request):
        qs = AuditLog.objects.all()
        date_from = parse_date(request.query_params.get('from'))
        date_to = parse_date(request.query_params.get('to'))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        by_action = [
            {'action': row['action'], 'count': row['count']}
            for row in qs.values('action').annotate(count=Count('id'))
        ]
        by_module = [
            {'module': row['module'], 'count': row['count']}
            for row in qs.values('module').annotate(count=Count('id'))
        ]
        return Response(
            {
                'data': {
                    'total': qs.count(),
                    'by_action': by_action,
                    'by_module': by_module,
                }
            }
        )


class ReportExportView(APIView):
    def get_required_permission(self):
        return 'reports:view'

    def get(self, request, report):
        response = ReportsView().get(request, report)
        if response.status_code >= 400:
            return response
        payload = response.data.get('data', response.data)
        sections = []
        for key, value in payload.items():
            if isinstance(value, list) and value and all(
                isinstance(item, dict) for item in value
            ):
                sections.append((key, value))
        if not sections:
            sections = [
                (
                    'summary',
                    [
                        {'field': key, 'value': value}
                        for key, value in payload.items()
                        if not isinstance(value, (dict, list))
                    ],
                )
            ]
        multiple = len(sections) > 1
        columns = []
        for _, rows in sections:
            for row in rows:
                for key in row:
                    if key not in columns:
                        columns.append(key)
        if multiple:
            columns = ['section'] + columns

        def cell(value):
            if value is None:
                return ''
            if isinstance(value, (dict, list)):
                return str(value)
            return str(value)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for section, rows in sections:
            for row in rows:
                values = [cell(row.get(column, '')) for column in columns]
                if multiple:
                    values.insert(0, section)
                writer.writerow(values)
        filename = f'{report}-{timezone.localdate().isoformat()}.csv'
        response = HttpResponse(
            output.getvalue(), content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        log_action(
            request,
            'EXPORT',
            'reports',
            'Report',
            report,
            f'Exported report {report} as CSV',
        )
        return response


class SearchView(APIView):
    def get_required_permission(self):
        return 'search:view'

    def get(self, request):
        from crm.models import Client, Insurer
        from claims.models import Claim
        from finance.models import Invoice
        from operations.models import MotorDetail, Policy, Quotation

        query = (request.query_params.get('q') or '').strip()
        if len(query) < 2:
            return Response({'data': {'query': query, 'groups': []}})

        groups = []

        clients = Client.objects.filter(
            Q(name__icontains=query)
            | Q(client_number__icontains=query)
            | Q(national_id__icontains=query)
            | Q(registration_no__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query),
            deleted_at__isnull=True,
        )[:5]
        groups.append(
            {
                'type': 'clients',
                'label': 'Clients',
                'items': [
                    {
                        'id': str(c.id),
                        'title': c.name,
                        'subtitle': f'{c.client_number} · {c.phone}',
                        'type': 'client',
                    }
                    for c in clients
                ],
            }
        )

        policies = Policy.objects.filter(
            Q(policy_number__icontains=query)
            | Q(client__name__icontains=query)
            | Q(insurer__name__icontains=query)
        ).select_related('client')[:5]
        groups.append(
            {
                'type': 'policies',
                'label': 'Policies',
                'items': [
                    {
                        'id': str(p.id),
                        'title': p.policy_number,
                        'subtitle': f'{p.client.name} · {p.status}',
                        'type': 'policy',
                    }
                    for p in policies
                ],
            }
        )

        quotations = Quotation.objects.filter(
            Q(quotation_number__icontains=query) | Q(client__name__icontains=query)
        ).select_related('client')[:5]
        groups.append(
            {
                'type': 'quotations',
                'label': 'Quotations',
                'items': [
                    {
                        'id': str(q.id),
                        'title': q.quotation_number,
                        'subtitle': f'{q.client.name} · {q.status}',
                        'type': 'quotation',
                    }
                    for q in quotations
                ],
            }
        )

        claims = Claim.objects.filter(
            Q(claim_number__icontains=query)
            | Q(client__name__icontains=query)
            | Q(cause__icontains=query)
        ).select_related('client')[:5]
        groups.append(
            {
                'type': 'claims',
                'label': 'Claims',
                'items': [
                    {
                        'id': str(c.id),
                        'title': c.claim_number,
                        'subtitle': f'{c.client.name} · {c.status}',
                        'type': 'claim',
                    }
                    for c in claims
                ],
            }
        )

        vehicles = MotorDetail.objects.filter(
            Q(registration_number__icontains=query)
            | Q(chassis_number__icontains=query)
            | Q(engine_number__icontains=query)
        ).select_related('risk', 'risk__client')[:5]
        groups.append(
            {
                'type': 'vehicles',
                'label': 'Vehicles',
                'items': [
                    {
                        'id': str(v.id),
                        'title': v.registration_number,
                        'subtitle': f'{v.make} {v.model} · {v.risk.client.name}',
                        'type': 'motor',
                    }
                    for v in vehicles
                ],
            }
        )

        insurers = Insurer.objects.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )[:5]
        groups.append(
            {
                'type': 'insurers',
                'label': 'Insurers',
                'items': [
                    {
                        'id': str(i.id),
                        'title': i.name,
                        'subtitle': i.code,
                        'type': 'insurer',
                    }
                    for i in insurers
                ],
            }
        )

        invoices = Invoice.objects.filter(
            Q(invoice_number__icontains=query) | Q(client__name__icontains=query)
        ).select_related('client')[:5]
        groups.append(
            {
                'type': 'invoices',
                'label': 'Invoices',
                'items': [
                    {
                        'id': str(i.id),
                        'title': i.invoice_number,
                        'subtitle': f'{i.client.name} · {i.status}',
                        'type': 'invoice',
                    }
                    for i in invoices
                ],
            }
        )

        return Response(
            {
                'data': {
                    'query': query,
                    'groups': [g for g in groups if g['items']],
                }
            }
        )


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            database = 'ok'
            status_code = 200
        except Exception:
            database = 'unavailable'
            status_code = 503
        return Response(
            {
                'status': 'ok' if database == 'ok' else 'degraded',
                'database': database,
                'service': 'ibms-api',
                'version': '1.0.0',
            },
            status=status_code,
        )
# 2026-11-11T15:06:09Z dashboard endpoint
# 2026-11-11T15:06:09Z premium report
# 2026-11-11T15:06:09Z commission report
# 2026-11-11T15:06:10Z global search
# 2026-11-11T15:06:10Z health check
