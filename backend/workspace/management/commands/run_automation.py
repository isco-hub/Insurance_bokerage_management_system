from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import AuditLog, User
from common.numbering import next_number
from finance.models import Premium
from operations.models import Quotation, Renewal
from workspace.delivery import deliver_communication
from workspace.models import Communication, Priority, Task, TaskStatus


class Command(BaseCommand):
    help = (
        'Run idempotent renewal, quotation and premium collection automation. '
        'Safe to run hourly or nightly from cron or the scheduler service.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            dest='run_date',
            help='Run for a specific ISO date (defaults to today).',
        )

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        if options.get('run_date'):
            try:
                run_date = date.fromisoformat(options['run_date'])
            except ValueError as exc:
                raise CommandError('--date must be an ISO date (YYYY-MM-DD)') from exc

        counts = {
            'renewals_reviewed': 0,
            'quotations_created': 0,
            'renewal_reminders': 0,
            'collection_reminders': 0,
            'tasks_created': 0,
        }
        self.process_renewals(run_date, counts)
        self.process_collections(run_date, counts)

        AuditLog.objects.create(
            action='AUTOMATION',
            module='automation',
            entity_type='AutomationRun',
            description=(
                'Automation run: '
                + ', '.join(f'{key}={value}' for key, value in counts.items())
            ),
            metadata={'date': run_date.isoformat(), **counts},
        )
        summary = ', '.join(f'{key}={value}' for key, value in counts.items())
        self.stdout.write(self.style.SUCCESS(f'Automation complete: {summary}'))

    def process_renewals(self, today, counts):
        renewals = (
            Renewal.objects.select_related(
                'policy',
                'policy__client',
                'policy__product',
                'policy__branch',
                'policy__broker',
                'policy__quotation',
                'handled_by',
            )
            .filter(
                status__in=['UPCOMING', 'DUE', 'QUOTED'],
                due_date__gte=today,
                due_date__lte=today
                + timedelta(days=settings.AUTOMATION_RENEWAL_DAYS),
            )
            .order_by('due_date')
        )
        stage_days = {90, 60, 30, 14, 7}
        for renewal in renewals:
            days = (renewal.due_date - today).days
            stage = self.stage_for(days)
            updates = []
            if renewal.stage_days != stage:
                renewal.stage_days = stage
                updates.append('stage_days')
            if stage <= 30 and renewal.status == 'UPCOMING':
                renewal.status = 'DUE'
                updates.append('status')
            if updates:
                renewal.save(update_fields=[*updates, 'updated_at'])
            counts['renewals_reviewed'] += 1

            if (
                renewal.renewal_quotation_id is None
                and days <= settings.AUTOMATION_RENEWAL_QUOTE_DAYS
                and self.generate_renewal_quotation(renewal, today)
            ):
                counts['quotations_created'] += 1
                renewal.refresh_from_db(fields=['renewal_quotation', 'status'])

            if stage in stage_days and self.create_renewal_reminder(
                renewal, stage, today
            ):
                counts['renewal_reminders'] += 1
                if renewal.reminder_task_created:
                    counts['tasks_created'] += 1

    def process_collections(self, today, counts):
        premiums = (
            Premium.objects.select_related(
                'policy',
                'policy__client',
                'policy__broker',
                'policy__created_by',
                'policy__client__relationship_manager',
            )
            .filter(
                status__in=['UNPAID', 'PARTIAL', 'OVERDUE'],
                due_date__lte=today,
            )
            .exclude(amount_due=F('amount_paid'))
            .order_by('due_date')
        )
        for premium in premiums:
            if premium.amount_due <= premium.amount_paid:
                continue
            if premium.status != 'OVERDUE':
                premium.status = 'OVERDUE'
                premium.save(update_fields=['status', 'updated_at'])
            if self.create_collection_reminder(premium, today):
                counts['collection_reminders'] += 1
                if premium.reminder_task_created:
                    counts['tasks_created'] += 1

    def stage_for(self, days):
        if days > 60:
            return 90
        if days > 30:
            return 60
        if days > 14:
            return 30
        if days > 7:
            return 14
        return 7

    def generate_renewal_quotation(self, renewal, today):
        policy = renewal.policy
        broker = renewal.handled_by or policy.broker or policy.created_by
        if not broker:
            return False
        start = policy.end_date + timedelta(days=1)
        valid_to = max(today + timedelta(days=30), start + timedelta(days=30))
        attempts = 0
        while attempts < 5:
            attempts += 1
            try:
                with transaction.atomic():
                    quotation = Quotation.objects.create(
                        quotation_number=next_number(
                            Quotation, 'quotation_number', 'QT'
                        ),
                        client=policy.client,
                        product=policy.product,
                        risk=(
                            policy.quotation.risk
                            if policy.quotation_id and policy.quotation.risk_id
                            else None
                        ),
                        broker=broker,
                        branch=policy.branch,
                        sum_insured=policy.sum_insured,
                        premium=policy.premium,
                        taxes=policy.taxes,
                        total_premium=policy.total_premium,
                        valid_from=today,
                        valid_to=valid_to,
                        status='DRAFT',
                        selected_insurer=policy.insurer,
                        notes=(
                            f'Automatically prepared renewal quotation for '
                            f'{policy.policy_number}.'
                        ),
                    )
                    renewal.renewal_quotation = quotation
                    if renewal.status in ('UPCOMING', 'DUE'):
                        renewal.status = 'QUOTED'
                    renewal.save(
                        update_fields=[
                            'renewal_quotation',
                            'status',
                            'updated_at',
                        ]
                    )
                    return True
            except IntegrityError:
                if attempts >= 5:
                    raise
        return False

    def create_renewal_reminder(self, renewal, stage, today):
        renewal.reminder_task_created = False
        subject = f'Policy renewal reminder — {stage} days'
        if Communication.objects.filter(
            related_entity_type='Renewal',
            related_entity_id=renewal.id,
            subject=subject,
        ).exists():
            return False
        client = renewal.policy.client
        commit = self.send_reminder(
            client=client,
            subject=subject,
            message=(
                f'Dear {client.name}, your {renewal.policy.product.name} policy '
                f'{renewal.policy.policy_number} is due for renewal on '
                f'{renewal.due_date:%d %b %Y}. Please contact us to review the '
                'renewal terms.'
            ),
            related_entity_type='Renewal',
            related_entity_id=renewal.id,
            today=today,
        )
        if commit and not commit['delivered']:
            renewal.reminder_task_created = self.create_task(
                title=f'Renewal follow-up — {renewal.policy.policy_number}',
                description=(
                    f'{stage}-day renewal reminder for {client.name}. '
                    f'Due {renewal.due_date:%d %b %Y}.'
                ),
                assigned_to=(
                    renewal.handled_by
                    or renewal.policy.broker
                    or renewal.policy.created_by
                    or client.relationship_manager
                ),
                related_entity_type='Renewal',
                related_entity_id=renewal.id,
                due_date=renewal.due_date,
                priority=Priority.HIGH if stage <= 14 else Priority.MEDIUM,
            )
        return True

    def create_collection_reminder(self, premium, today):
        premium.reminder_task_created = False
        interval = settings.AUTOMATION_COLLECTION_INTERVAL_DAYS
        recent = Communication.objects.filter(
            related_entity_type='Premium',
            related_entity_id=premium.id,
            created_at__gte=timezone.now() - timedelta(days=interval),
        ).exists()
        if recent:
            return False
        open_task = Task.objects.filter(
            related_entity_type='Premium',
            related_entity_id=premium.id,
            status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
        ).exists()
        if open_task:
            return False
        client = premium.policy.client
        balance = premium.amount_due - premium.amount_paid
        subject = f'Premium payment reminder — {premium.policy.policy_number}'
        commit = self.send_reminder(
            client=client,
            subject=subject,
            message=(
                f'Dear {client.name}, the outstanding balance of '
                f'{balance:,.2f} for instalment {premium.installment_no} of '
                f'policy {premium.policy.policy_number} was due on '
                f'{premium.due_date:%d %b %Y}. Kindly arrange payment.'
            ),
            related_entity_type='Premium',
            related_entity_id=premium.id,
            today=today,
        )
        if commit and not commit['delivered']:
            premium.reminder_task_created = self.create_task(
                title=(
                    f'Premium collection — {premium.policy.policy_number} '
                    f'#{premium.installment_no}'
                ),
                description=(
                    f'Collect outstanding balance of {balance:,.2f} from '
                    f'{client.name}. Due {premium.due_date:%d %b %Y}.'
                ),
                assigned_to=(
                    premium.policy.broker
                    or premium.policy.created_by
                    or client.relationship_manager
                ),
                related_entity_type='Premium',
                related_entity_id=premium.id,
                due_date=today,
                priority=Priority.HIGH,
            )
        return True

    def send_reminder(
        self,
        client,
        subject,
        message,
        related_entity_type,
        related_entity_id,
        today,
    ):
        channel = 'EMAIL' if client.email else ('SMS' if client.phone else '')
        if not channel:
            return {'delivered': False, 'communication': None}
        communication = Communication.objects.create(
            client=client,
            channel=channel,
            subject=subject,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            status='PENDING',
        )
        try:
            delivered, _ = deliver_communication(communication)
        except Exception:
            delivered = False
        communication.status = 'SENT' if delivered else 'FAILED'
        communication.sent_at = timezone.now() if delivered else None
        communication.save(update_fields=['status', 'sent_at', 'updated_at'])
        return {'delivered': delivered, 'communication': communication}

    def create_task(
        self,
        title,
        description,
        assigned_to,
        related_entity_type,
        related_entity_id,
        due_date,
        priority,
    ):
        if not assigned_to:
            assigned_to = (
                User.objects.filter(is_active=True)
                .order_by('date_joined', 'email')
                .first()
            )
        if not assigned_to:
            return False
        if Task.objects.filter(
            title=title,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
        ).exists():
            return False
        Task.objects.create(
            title=title,
            description=description,
            assigned_to=assigned_to,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            due_date=due_date,
            priority=priority,
        )
        return True
