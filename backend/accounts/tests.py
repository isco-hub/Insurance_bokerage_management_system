from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_branch, make_client, make_role, make_user


class AuthAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = make_branch()
        self.user = make_user(
            email='admin@test.local',
            role=make_role('ADMIN'),
            branch=self.branch,
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.email, 'password': 'Password123!'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json()['data'])
        self.assertIn('refresh', response.json()['data'])
        self.assertEqual(response.json()['data']['user']['role_code'], 'ADMIN')

    def test_login_rejects_invalid_password(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.email, 'password': 'wrong-password'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['statusCode'], 401)

    @override_settings(MAX_LOGIN_ATTEMPTS=2, LOCK_MINUTES=15)
    def test_login_locks_after_repeated_failures(self):
        for _ in range(2):
            self.client.post(
                '/api/auth/login/',
                {'email': self.user.email, 'password': 'wrong-password'},
                format='json',
            )
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)

        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.email, 'password': 'Password123!'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn('locked', response.json()['message'].lower())

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_unlock_clears_failed_attempts_and_lock(self):
        target = make_user('locked@test.local', make_role('OPS'), self.branch)
        target.failed_login_attempts = 5
        target.locked_until = timezone.now() + timedelta(minutes=15)
        target.save(update_fields=['failed_login_attempts', 'locked_until'])

        self.client.force_authenticate(self.user)
        response = self.client.post(f'/api/users/{target.id}/unlock/', format='json')
        self.assertEqual(response.status_code, 200, response.content)

        target.refresh_from_db()
        self.assertEqual(target.failed_login_attempts, 0)
        self.assertIsNone(target.locked_until)
        self.assertFalse(response.json()['data']['is_locked'])


class PermissionAndScopeAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.hq = make_branch(code='HQ')
        self.upcountry = make_branch(code='UC', name='Upcountry Branch')
        self.role = make_role('BRANCH', ['clients:view', 'clients:delete'])
        self.user = make_user('ops@test.local', self.role, self.hq)

    def test_missing_permission_is_forbidden(self):
        no_access = make_user(
            'noaccess@test.local', make_role('NOACCESS'), self.hq
        )
        self.client.force_authenticate(no_access)
        response = self.client.get('/api/clients/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('clients:view', response.json()['message'])

    def test_branch_role_only_sees_own_branch(self):
        self.client.force_authenticate(self.user)
        make_client(self.hq, 'CLI-HQ-0001', 'HQ Client')
        make_client(self.upcountry, 'CLI-UC-0001', 'Upcountry Client')

        response = self.client.get('/api/clients/')
        self.assertEqual(response.status_code, 200)
        names = [row['name'] for row in response.json()['data']]
        self.assertEqual(names, ['HQ Client'])

    def test_admin_bypasses_permission_matrix(self):
        admin = make_user('root@test.local', make_role('ADMIN'), self.hq)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/clients/').status_code, 200)

    def test_soft_delete_hides_client_from_list(self):
        self.client.force_authenticate(self.user)
        client = make_client(self.hq, 'CLI-DEL-0001', 'Delete Me')

        response = self.client.delete(f'/api/clients/{client.id}/')
        self.assertEqual(response.status_code, 204)
        client.refresh_from_db()
        self.assertFalse(client.is_active)
        self.assertIsNotNone(client.deleted_at)
        self.assertEqual(self.client.get('/api/clients/').json()['data'], [])
# 2026-11-11T15:05:23Z JWT refresh tests
