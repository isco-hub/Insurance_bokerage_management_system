from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from claims.models import Claim
from common.testing import make_branch, make_client, make_product, make_role, make_user
from operations.services import create_policy


class ClaimSettlementAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('claims@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(self.branch, 'CLI-CLM-0001', 'Claims Client')
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
            },
            self.user,
        )
        self.claim = Claim.objects.create(
            claim_number='CLM-TEST-0001',
            policy=self.policy,
            client=self.customer,
            date_of_loss=self.today,
            cause='Accident',
            reserve_amount=Decimal('500.00'),
        )

    def test_settle_claim_records_paid_amount_and_status(self):
        response = self.client.post(
            f'/api/claims/{self.claim.id}/settle/',
            {'paid_amount': '500.00', 'recovered_amount': '0.00', 'notes': 'Settled'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, 'SETTLED')
        self.assertEqual(self.claim.paid_amount, Decimal('500.00'))
        self.assertIsNotNone(self.claim.settled_at)
