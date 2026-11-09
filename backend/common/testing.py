"""Shared fixtures for Django/DRF tests."""

from decimal import Decimal

from accounts.models import Branch, Permission, Role, RolePermission, User
from crm.models import Client, InsuranceClass, Insurer, Product


def make_branch(code='HQ', name='Head Office'):
    branch, _ = Branch.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'phone': '+256 414 000 000',
            'email': f'{code.lower()}@ibms.test',
        },
    )
    return branch


def make_role(code='OPS', permissions=()):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={'name': code.title(), 'is_system': code in {'ADMIN', 'MD'}},
    )
    for permission_code in permissions:
        module, action = permission_code.split(':', 1)
        permission, _ = Permission.objects.get_or_create(
            module=module,
            action=action,
            defaults={'description': permission_code},
        )
        RolePermission.objects.get_or_create(role=role, permission=permission)
    return role


def make_user(email='user@ibms.test', role=None, branch=None, password='Password123!'):
    return User.objects.create_user(
        email=email,
        password=password,
        first_name='Test',
        last_name='User',
        role=role,
        branch=branch,
    )


def make_client(branch, number='CLI-TEST-0001', name='Test Client', **overrides):
    values = {
        'client_number': number,
        'name': name,
        'phone': '+256 772 000 000',
        'branch': branch,
        'kyc_status': 'VERIFIED',
    }
    values.update(overrides)
    return Client.objects.create(**values)


def make_product(code='TEST-MOTOR', commission_rate='12.50'):
    insurer, _ = Insurer.objects.get_or_create(
        code='TESTINS',
        defaults={'name': 'Test Insurer', 'phone': '+256 414 100 000'},
    )
    insurance_class, _ = InsuranceClass.objects.get_or_create(
        code='TESTMOTOR',
        defaults={'name': 'Test Motor', 'category': 'GENERAL'},
    )
    product, _ = Product.objects.get_or_create(
        code=code,
        defaults={
            'name': 'Test Comprehensive Motor',
            'insurance_class': insurance_class,
            'insurer': insurer,
            'minimum_premium': Decimal('10000.00'),
            'commission_rate': Decimal(commission_rate),
        },
    )
    return product
