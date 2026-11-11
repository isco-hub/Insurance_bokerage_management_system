from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_branch, make_client, make_product, make_role, make_user
from finance.models import Remittance
from operations.services import create_policy


class ReportingAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user('admin@test.local', make_role('ADMIN'), self.branch)
        self.client.force_authenticate(self.user)
        self.customer = make_client(self.branch, 'CLI-RPT-0001', 'Report Client')
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
        Remittance.objects.create(
            remittance_number='REM-TEST-0001',
            insurer=self.product.insurer,
            branch=self.branch,
            period_from=self.today,
            period_to=self.today,
            gross_premium=Decimal('1000.00'),
            commission_retained=Decimal('100.00'),
            taxes=Decimal('0.00'),
            net_amount=Decimal('900.00'),
            matched_amount=Decimal('900.00'),
            status='RECONCILED',
        )

    def test_dashboard_returns_kpis(self):
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('kpis', response.json()['data'])

    def test_premium_production_report_returns_rows_and_summary(self):
        response = self.client.get('/api/reports/premium-production/')
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['summary']['count'], 1)
        self.assertEqual(data['rows'][0]['policy_number'], self.policy.policy_number)

    def test_specialised_reports_return_expected_shapes(self):
        reports = {
            'commission-statement': ('rows', 'summary', 'by_insurer'),
            'remittance-reconciliation': ('rows', 'summary', 'by_status'),
            'debtors-ageing': ('rows', 'summary', 'buckets'),
            'quotation-conversion': ('rows', 'summary', 'by_status'),
            'claim-analysis': ('rows', 'summary', 'by_status'),
            'business-by-client': ('rows', 'summary'),
            'policy-register': ('rows', 'summary', 'by_status'),
        }
        for report, keys in reports.items():
            with self.subTest(report=report):
                response = self.client.get(f'/api/reports/{report}/')
                self.assertEqual(response.status_code, 200, response.content)
                data = response.json()['data']
                for key in keys:
                    self.assertIn(key, data)
        commission = self.client.get('/api/reports/commission-statement/')
        self.assertEqual(len(commission.json()['data']['rows']), 1)

    def test_report_export_returns_csv(self):
        response = self.client.get('/api/reports/commission-statement/export/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn(b'policy_number', response.content)

    def test_unknown_report_is_404(self):
        response = self.client.get('/api/reports/not-a-report/')
        self.assertEqual(response.status_code, 404)

    def test_health_is_public_and_healthy(self):
        anonymous = APIClient()
        response = anonymous.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['database'], 'ok')
# 2026-11-11T15:06:10Z dashboard tests
