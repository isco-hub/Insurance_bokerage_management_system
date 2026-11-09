from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import (
    make_branch,
    make_client,
    make_product,
    make_role,
    make_user,
)
from operations.models import Quotation
from operations.services import create_policy
from workspace.models import Communication, Task


class CommunicationDeliveryAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('admin@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(
            self.branch,
            'CLI-COM-0001',
            'Communication Client',
            email='client@example.test',
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_email_communication_is_sent_and_marked_sent(self):
        communication = Communication.objects.create(
            client=self.customer,
            channel='EMAIL',
            subject='Policy renewal',
            message='Your policy is due for renewal.',
        )
        response = self.client.post(
            f'/api/communications/{communication.id}/send/', format='json'
        )
        self.assertEqual(response.status_code, 200, response.content)
        communication.refresh_from_db()
        self.assertEqual(communication.status, 'SENT')
        self.assertIsNotNone(communication.sent_at)
        self.assertEqual(communication.sent_by, self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['client@example.test'])

    @override_settings(SMS_GATEWAY_URL='')
    def test_sms_without_gateway_is_marked_failed(self):
        communication = Communication.objects.create(
            client=self.customer,
            channel='SMS',
            message='Your policy is due for renewal.',
        )
        response = self.client.post(
            f'/api/communications/{communication.id}/send/', format='json'
        )
        self.assertEqual(response.status_code, 400)
        communication.refresh_from_db()
        self.assertEqual(communication.status, 'FAILED')
        self.assertIn('not configured', response.json()['message'])


class AutomationCommandTests(TestCase):
    def setUp(self):
        cache.clear()
        self.branch = make_branch()
        self.user = make_user('admin@test.local', make_role('ADMIN'), self.branch)
        self.customer = make_client(
            self.branch,
            'CLI-AUTO-0001',
            'Automation Client',
            email='automation@example.test',
        )
        self.product = make_product()
        self.today = timezone.localdate()
        self.policy = create_policy(
            {
                'client': self.customer,
                'product': self.product,
                'branch': self.branch,
                'broker': self.user,
                'premium': Decimal('1200.00'),
                'start_date': self.today,
                'end_date': self.today + timedelta(days=365),
            },
            self.user,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_renewal_automation_generates_quote_and_one_reminder(self):
        renewal = self.policy.renewals.get()
        renewal.due_date = self.today + timedelta(days=55)
        renewal.stage_days = 90
        renewal.save(update_fields=['due_date', 'stage_days'])
        self.policy.end_date = renewal.due_date
        self.policy.save(update_fields=['end_date'])

        output = StringIO()
        call_command('run_automation', stdout=output)

        renewal.refresh_from_db()
        self.assertIsNotNone(renewal.renewal_quotation_id)
        self.assertEqual(renewal.stage_days, 60)
        self.assertEqual(renewal.status, 'QUOTED')
        self.assertEqual(
            Communication.objects.filter(
                related_entity_type='Renewal',
                related_entity_id=renewal.id,
                status='SENT',
            ).count(),
            1,
        )

        call_command('run_automation', stdout=StringIO())
        renewal.refresh_from_db()
        self.assertEqual(
            Communication.objects.filter(
                related_entity_type='Renewal',
                related_entity_id=renewal.id,
            ).count(),
            1,
        )
        self.assertEqual(
            Quotation.objects.filter(
                renewal__policy=self.policy
            ).count(),
            1,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_collection_automation_marks_overdue_and_reminds_once(self):
        premium = self.policy.premiums.first()
        premium.due_date = self.today - timedelta(days=5)
        premium.status = 'UNPAID'
        premium.save(update_fields=['due_date', 'status'])

        call_command('run_automation', stdout=StringIO())

        premium.refresh_from_db()
        self.assertEqual(premium.status, 'OVERDUE')
        self.assertEqual(
            Communication.objects.filter(
                related_entity_type='Premium',
                related_entity_id=premium.id,
                status='SENT',
            ).count(),
            1,
        )

        call_command('run_automation', stdout=StringIO())
        self.assertEqual(
            Communication.objects.filter(
                related_entity_type='Premium',
                related_entity_id=premium.id,
            ).count(),
            1,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_failed_delivery_creates_one_follow_up_task(self):
        self.customer.email = ''
        self.customer.save(update_fields=['email'])
        premium = self.policy.premiums.first()
        premium.due_date = self.today - timedelta(days=2)
        premium.save(update_fields=['due_date'])
        # The client has a phone but SMS is not configured, so delivery fails.
        call_command('run_automation', stdout=StringIO())
        call_command('run_automation', stdout=StringIO())
        self.assertEqual(
            Task.objects.filter(
                related_entity_type='Premium',
                related_entity_id=premium.id,
                status='TODO',
            ).count(),
            1,
        )
