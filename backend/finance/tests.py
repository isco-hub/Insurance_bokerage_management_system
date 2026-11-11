from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_branch, make_client, make_product, make_role, make_user
from finance.models import Invoice, Payment, Premium
from operations.services import create_policy


class PaymentAllocationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('finance@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(self.branch, 'CLI-FIN-0001', 'Finance Client')
        self.product = make_product()
        self.today = timezone.localdate()
        self.policy = create_policy(
            {
                'client': self.customer,
                'product': self.product,
                'branch': self.branch,
                'broker': self.user,
                'premium': Decimal('1000.00'),
                'taxes': Decimal('0.00'),
                'start_date': self.today,
                'end_date': self.today + timedelta(days=365),
                'payment_frequency': 'QUARTERLY',
            },
            self.user,
        )
        self.invoice = Invoice.objects.get(policy=self.policy)

    def test_confirmed_payment_updates_invoice_and_installments(self):
        response = self.client.post(
            '/api/payments/',
            {
                'client': str(self.customer.id),
                'policy': str(self.policy.id),
                'invoice': str(self.invoice.id),
                'amount': '300.00',
                'method': 'CASH',
                'status': 'CONFIRMED',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Payment.objects.filter(policy=self.policy).exists())

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('300.00'))
        self.assertEqual(self.invoice.status, 'PARTIAL')

        premiums = list(
            Premium.objects.filter(policy=self.policy).order_by('installment_no')
        )
        self.assertEqual(premiums[0].amount_paid, Decimal('250.00'))
        self.assertEqual(premiums[0].status, 'PAID')
        self.assertEqual(premiums[1].amount_paid, Decimal('50.00'))
        self.assertEqual(premiums[1].status, 'PARTIAL')

    def test_refund_reverses_invoice_and_premium_allocations(self):
        create_response = self.client.post(
            '/api/payments/',
            {
                'client': str(self.customer.id),
                'policy': str(self.policy.id),
                'invoice': str(self.invoice.id),
                'amount': '300.00',
                'method': 'CASH',
                'status': 'CONFIRMED',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        payment_id = create_response.json()['data']['id']

        partial = self.client.post(
            f'/api/payments/{payment_id}/refund/',
            {'amount': '100.00', 'reason': 'Overpayment correction'},
            format='json',
        )
        self.assertEqual(partial.status_code, 200, partial.content)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('200.00'))
        premiums = list(
            Premium.objects.filter(policy=self.policy).order_by('installment_no')
        )
        self.assertEqual(premiums[0].amount_paid, Decimal('200.00'))
        self.assertEqual(premiums[0].status, 'PARTIAL')
        self.assertEqual(premiums[1].amount_paid, Decimal('0.00'))
        self.assertEqual(premiums[1].status, 'UNPAID')

        full = self.client.post(
            f'/api/payments/{payment_id}/refund/',
            {'amount': '200.00', 'reason': 'Full refund requested'},
            format='json',
        )
        self.assertEqual(full.status_code, 200, full.content)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('0.00'))
        self.assertEqual(Payment.objects.get(id=payment_id).status, 'REVERSED')

    def test_pending_payment_does_not_allocate(self):
        response = self.client.post(
            '/api/payments/',
            {
                'client': str(self.customer.id),
                'policy': str(self.policy.id),
                'amount': '100.00',
                'method': 'CASH',
                'status': 'PENDING',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('0.00'))
# 2026-11-11T15:06:09Z premium tests
# 2026-11-11T15:06:09Z commission edge cases
