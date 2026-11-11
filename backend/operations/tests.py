from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_branch, make_client, make_product, make_role, make_user
from finance.models import Commission, Invoice, Premium
from operations.models import InsurerQuote, Policy, Quotation, QuoteResponseStatus, Renewal
from operations.services import create_policy
from workspace.models import Approval, ApprovalStatus


class QuotationWorkflowAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('admin@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(self.branch, 'CLI-QT-0001', 'Quotation Client')
        self.product = make_product()
        self.today = timezone.localdate()

    def make_quotation(self, premium='1000.00', taxes='100.00'):
        quotation = Quotation.objects.create(
            quotation_number='QT-TEST-0001',
            client=self.customer,
            product=self.product,
            broker=self.user,
            branch=self.branch,
            sum_insured=Decimal('500000.00'),
            premium=Decimal(premium),
            taxes=Decimal(taxes),
            total_premium=Decimal(premium) + Decimal(taxes),
            valid_from=self.today,
            valid_to=self.today + timedelta(days=30),
        )
        InsurerQuote.objects.create(
            quotation=quotation,
            insurer=self.product.insurer,
            premium=Decimal(premium),
            taxes=Decimal(taxes),
            status=QuoteResponseStatus.RECEIVED,
        )
        return quotation

    def test_select_insurer_then_accept_creates_policy_bundle(self):
        quotation = self.make_quotation()
        select_response = self.client.post(
            f'/api/quotations/{quotation.id}/select/',
            {'insurer_id': str(self.product.insurer_id)},
            format='json',
        )
        self.assertEqual(select_response.status_code, 200)
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, 'SELECTED')
        self.assertEqual(quotation.selected_insurer_id, self.product.insurer_id)

        accept_response = self.client.post(
            f'/api/quotations/{quotation.id}/accept/',
            {
                'start_date': self.today.isoformat(),
                'end_date': (self.today + timedelta(days=365)).isoformat(),
                'payment_frequency': 'QUARTERLY',
            },
            format='json',
        )
        self.assertEqual(accept_response.status_code, 201, accept_response.content)

        policy = Policy.objects.get(quotation=quotation)
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, 'ACCEPTED')
        self.assertEqual(policy.total_premium, Decimal('1100.00'))
        self.assertEqual(Invoice.objects.filter(policy=policy).count(), 1)
        self.assertEqual(Premium.objects.filter(policy=policy).count(), 4)
        self.assertEqual(Commission.objects.filter(policy=policy).count(), 1)
        self.assertEqual(Renewal.objects.filter(policy=policy).count(), 1)

    def test_accept_requires_management_approval_above_threshold(self):
        quotation = self.make_quotation(premium='60000.00', taxes='0.00')
        self.client.post(
            f'/api/quotations/{quotation.id}/select/',
            {'insurer_id': str(self.product.insurer_id)},
            format='json',
        )

        response = self.client.post(
            f'/api/quotations/{quotation.id}/accept/',
            {'start_date': self.today.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('approval threshold', response.json()['message'])
        self.assertFalse(Policy.objects.filter(quotation=quotation).exists())
        self.assertTrue(
            Approval.objects.filter(
                type='QUOTATION',
                entity_id=quotation.id,
                status=ApprovalStatus.PENDING,
            ).exists()
        )

    def test_approval_review_exposes_linked_quotation(self):
        quotation = self.make_quotation()
        approval = Approval.objects.create(
            type='QUOTATION',
            entity_type='Quotation',
            entity_id=str(quotation.id),
            amount=quotation.total_premium,
            requested_by=self.user,
            status=ApprovalStatus.PENDING,
        )
        response = self.client.get(f'/api/approvals/{approval.id}/review/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertTrue(data['entity_available'])
        self.assertEqual(
            data['entity']['quotation_number'], quotation.quotation_number
        )
        self.assertEqual(data['approval']['id'], str(approval.id))

    def test_accept_rejects_expired_quotation(self):
        quotation = self.make_quotation()
        quotation.valid_to = self.today - timedelta(days=1)
        quotation.save(update_fields=['valid_to'])
        self.client.post(
            f'/api/quotations/{quotation.id}/select/',
            {'insurer_id': str(self.product.insurer_id)},
            format='json',
        )

        response = self.client.post(
            f'/api/quotations/{quotation.id}/accept/',
            {'start_date': self.today.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        quotation.refresh_from_db()
        self.assertEqual(quotation.status, 'EXPIRED')


class PolicyCancellationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('admin@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(self.branch, 'CLI-CAN-0001', 'Cancellation Client')
        self.product = make_product()
        self.today = timezone.localdate()
        self.policy = create_policy(
            {
                'client': self.customer,
                'product': self.product,
                'branch': self.branch,
                'broker': self.user,
                'premium': Decimal('1000.00'),
                'start_date': self.today,
                'end_date': self.today + timedelta(days=365),
                'payment_frequency': 'QUARTERLY',
            },
            self.user,
        )

    def test_cancel_policy_lapses_renewals_and_cancels_commissions(self):
        Commission.objects.filter(policy=self.policy).update(status='PENDING')
        response = self.client.post(
            f'/api/policies/{self.policy.id}/cancel/',
            {'effective_date': self.today.isoformat(), 'reason': 'Client request'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, 'CANCELLED')
        self.assertEqual(self.policy.cancellation_reason, 'Client request')
        self.assertEqual(self.policy.cancellation_effective_date, self.today)
        self.assertIsNotNone(self.policy.cancelled_at)
        self.assertFalse(
            Renewal.objects.filter(policy=self.policy).exclude(status='LAPSED').exists()
        )
        self.assertFalse(
            Commission.objects.filter(policy=self.policy).exclude(status='CANCELLED').exists()
        )

    def test_cancel_requires_reason(self):
        response = self.client.post(
            f'/api/policies/{self.policy.id}/cancel/',
            {'effective_date': self.today.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.policy.refresh_from_db()
        self.assertNotEqual(self.policy.status, 'CANCELLED')
# 2026-11-11T15:06:08Z quotation tests
# 2026-11-11T15:06:08Z renewal tests
