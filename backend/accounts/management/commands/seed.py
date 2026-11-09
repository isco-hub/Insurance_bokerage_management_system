from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    AuditLog,
    Branch,
    Permission,
    Role,
    RolePermission,
    User,
)
from claims.models import Claim, ClaimStatus
from crm.models import (
    ClassCategory,
    Client,
    ClientContact,
    ClientDirector,
    ClientType,
    Insurer,
    InsurerBranch,
    InsurerContact,
    InsuranceClass,
    KycStatus,
    Product,
)
from finance.models import (
    CommissionStatus,
    CreditDebitNote,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Remittance,
)
from finance.services import allocate_payment
from operations.models import (
    Endorsement,
    EndorsementStatus,
    EndorsementType,
    InsurerQuote,
    MotorDetail,
    Policy,
    PolicyStatus,
    Quotation,
    QuotationStatus,
    QuoteResponseStatus,
    RenewalStatus,
    Risk,
    RiskStatus,
)
from operations.services import create_policy
from common.numbering import next_number
from workspace.models import (
    Approval,
    ApprovalStatus,
    ApprovalType,
    CommChannel,
    Communication,
    Document,
    Priority,
    Task,
    TaskStatus,
)

MODULE_ACTIONS = {
    'dashboard': ['view'],
    'search': ['view'],
    'branches': ['view', 'create', 'edit', 'delete'],
    'users': ['view', 'create', 'edit', 'delete'],
    'roles': ['view', 'create', 'edit', 'delete'],
    'audit': ['view', 'report'],
    'approvals': ['view', 'approve'],
    'clients': ['view', 'create', 'edit', 'delete', 'report'],
    'insurers': ['view', 'create', 'edit', 'delete'],
    'products': ['view', 'create', 'edit', 'delete', 'report'],
    'risks': ['view', 'create', 'edit', 'delete'],
    'motor': ['view', 'create', 'edit', 'delete'],
    'quotations': ['view', 'create', 'edit', 'approve', 'delete', 'report'],
    'policies': ['view', 'create', 'edit', 'delete', 'report'],
    'endorsements': ['view', 'create', 'edit', 'approve'],
    'renewals': ['view', 'create', 'edit', 'report'],
    'premiums': ['view', 'create', 'edit', 'report'],
    'invoices': ['view', 'create', 'edit', 'delete'],
    'payments': ['view', 'create', 'edit', 'delete'],
    'notes': ['view', 'create', 'edit'],
    'commissions': ['view', 'create', 'edit', 'approve', 'report'],
    'remittances': ['view', 'create', 'edit', 'approve', 'report'],
    'claims': ['view', 'create', 'edit', 'approve', 'report'],
    'documents': ['view', 'create', 'edit', 'delete'],
    'communications': ['view', 'create', 'edit'],
    'tasks': ['view', 'create', 'edit', 'delete'],
    'reports': ['view'],
}

ALL_CODES = {
    f'{module}:{action}'
    for module, actions in MODULE_ACTIONS.items()
    for action in actions
}

COMMON = {'dashboard:view', 'search:view', 'reports:view'}

ROLE_GRANTS = {
    'ADMIN': ALL_CODES,
    'MD': COMMON
    | {
        'branches:view',
        'users:view',
        'roles:view',
        'audit:view',
        'audit:report',
        'approvals:view',
        'approvals:approve',
        'clients:view',
        'clients:report',
        'insurers:view',
        'products:view',
        'products:report',
        'risks:view',
        'motor:view',
        'quotations:view',
        'quotations:approve',
        'quotations:report',
        'policies:view',
        'policies:report',
        'endorsements:view',
        'endorsements:approve',
        'renewals:view',
        'renewals:report',
        'premiums:view',
        'premiums:report',
        'invoices:view',
        'payments:view',
        'notes:view',
        'commissions:view',
        'commissions:approve',
        'commissions:report',
        'remittances:view',
        'remittances:approve',
        'remittances:report',
        'claims:view',
        'claims:approve',
        'claims:report',
        'documents:view',
        'communications:view',
        'tasks:view',
    },
    'OPS': COMMON
    | {
        'branches:view',
        'users:view',
        'audit:view',
        'audit:report',
        'approvals:view',
        'approvals:approve',
        'clients:view',
        'clients:create',
        'clients:edit',
        'clients:report',
        'insurers:view',
        'insurers:create',
        'insurers:edit',
        'products:view',
        'products:create',
        'products:edit',
        'products:report',
        'risks:view',
        'risks:create',
        'risks:edit',
        'motor:view',
        'motor:create',
        'motor:edit',
        'quotations:view',
        'quotations:create',
        'quotations:edit',
        'quotations:approve',
        'quotations:report',
        'policies:view',
        'policies:create',
        'policies:edit',
        'policies:report',
        'endorsements:view',
        'endorsements:create',
        'endorsements:edit',
        'endorsements:approve',
        'renewals:view',
        'renewals:create',
        'renewals:edit',
        'renewals:report',
        'premiums:view',
        'premiums:report',
        'invoices:view',
        'payments:view',
        'notes:view',
        'commissions:view',
        'commissions:approve',
        'commissions:report',
        'remittances:view',
        'remittances:approve',
        'remittances:report',
        'claims:view',
        'claims:create',
        'claims:edit',
        'claims:approve',
        'claims:report',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'communications:create',
        'communications:edit',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'BRANCH': COMMON
    | {
        'branches:view',
        'users:view',
        'approvals:view',
        'approvals:approve',
        'clients:view',
        'clients:create',
        'clients:edit',
        'clients:report',
        'insurers:view',
        'products:view',
        'risks:view',
        'risks:create',
        'risks:edit',
        'motor:view',
        'motor:create',
        'motor:edit',
        'quotations:view',
        'quotations:create',
        'quotations:edit',
        'quotations:report',
        'policies:view',
        'policies:create',
        'policies:edit',
        'policies:report',
        'endorsements:view',
        'endorsements:create',
        'endorsements:edit',
        'endorsements:approve',
        'renewals:view',
        'renewals:create',
        'renewals:edit',
        'renewals:report',
        'premiums:view',
        'premiums:report',
        'invoices:view',
        'payments:view',
        'notes:view',
        'commissions:view',
        'commissions:report',
        'remittances:view',
        'claims:view',
        'claims:create',
        'claims:edit',
        'claims:report',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'communications:create',
        'communications:edit',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'BROKER': COMMON
    | {
        'approvals:view',
        'clients:view',
        'clients:create',
        'clients:edit',
        'clients:report',
        'insurers:view',
        'products:view',
        'risks:view',
        'risks:create',
        'risks:edit',
        'motor:view',
        'motor:create',
        'motor:edit',
        'quotations:view',
        'quotations:create',
        'quotations:edit',
        'quotations:report',
        'policies:view',
        'policies:create',
        'policies:edit',
        'policies:report',
        'endorsements:view',
        'renewals:view',
        'renewals:create',
        'renewals:edit',
        'renewals:report',
        'premiums:view',
        'invoices:view',
        'payments:view',
        'commissions:view',
        'claims:view',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'communications:create',
        'communications:edit',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'UNDERWRITING': COMMON
    | {
        'approvals:view',
        'insurers:view',
        'products:view',
        'products:create',
        'products:edit',
        'risks:view',
        'motor:view',
        'quotations:view',
        'quotations:create',
        'quotations:edit',
        'policies:view',
        'policies:create',
        'policies:edit',
        'endorsements:view',
        'endorsements:create',
        'endorsements:edit',
        'renewals:view',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'CLAIMS': COMMON
    | {
        'approvals:view',
        'clients:view',
        'policies:view',
        'claims:view',
        'claims:create',
        'claims:edit',
        'claims:report',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'communications:create',
        'communications:edit',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'FINANCE': COMMON
    | {
        'branches:view',
        'approvals:view',
        'approvals:approve',
        'clients:view',
        'insurers:view',
        'products:view',
        'quotations:view',
        'policies:view',
        'endorsements:view',
        'premiums:view',
        'premiums:create',
        'premiums:edit',
        'premiums:report',
        'invoices:view',
        'invoices:create',
        'invoices:edit',
        'payments:view',
        'payments:create',
        'payments:edit',
        'notes:view',
        'notes:create',
        'notes:edit',
        'commissions:view',
        'commissions:create',
        'commissions:edit',
        'commissions:approve',
        'commissions:report',
        'remittances:view',
        'remittances:create',
        'remittances:edit',
        'remittances:approve',
        'remittances:report',
        'claims:view',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'SERVICE': COMMON
    | {
        'clients:view',
        'clients:create',
        'clients:edit',
        'insurers:view',
        'products:view',
        'risks:view',
        'motor:view',
        'quotations:view',
        'policies:view',
        'renewals:view',
        'renewals:create',
        'renewals:edit',
        'claims:view',
        'documents:view',
        'documents:create',
        'documents:edit',
        'communications:view',
        'communications:create',
        'communications:edit',
        'tasks:view',
        'tasks:create',
        'tasks:edit',
    },
    'AUDITOR': COMMON
    | {
        'branches:view',
        'users:view',
        'roles:view',
        'audit:view',
        'audit:report',
        'approvals:view',
        'clients:view',
        'clients:report',
        'insurers:view',
        'products:view',
        'products:report',
        'risks:view',
        'motor:view',
        'quotations:view',
        'quotations:report',
        'policies:view',
        'policies:report',
        'endorsements:view',
        'renewals:view',
        'renewals:report',
        'premiums:view',
        'premiums:report',
        'invoices:view',
        'payments:view',
        'notes:view',
        'commissions:view',
        'commissions:report',
        'remittances:view',
        'remittances:report',
        'claims:view',
        'claims:report',
        'documents:view',
        'communications:view',
        'tasks:view',
    },
}

ROLE_NAMES = {
    'ADMIN': ('System Administrator', 'Full system administration'),
    'MD': ('Managing Director', 'Executive oversight and approvals'),
    'OPS': ('Operations Manager', 'Operations supervision and workflow'),
    'BRANCH': ('Branch Manager', 'Branch performance and operations'),
    'BROKER': ('Broker', 'Client acquisition and brokerage operations'),
    'UNDERWRITING': ('Underwriting Officer', 'Products, quotes and schedules'),
    'CLAIMS': ('Claims Officer', 'Claims registration and settlement'),
    'FINANCE': ('Finance Officer', 'Premiums, commissions and reconciliation'),
    'SERVICE': ('Customer Service Officer', 'Client service and communication'),
    'AUDITOR': ('Auditor', 'Read-only assurance and audit reporting'),
}


class Command(BaseCommand):
    help = 'Seed IBMS roles, permissions, demo users and demonstration data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='Password123!',
            help='Password assigned to demo users.',
        )
        parser.add_argument(
            '--skip-demo',
            action='store_true',
            help='Create only roles, permissions, branches and users.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding IBMS'))

        permissions = self._seed_permissions()
        roles = self._seed_roles(permissions)
        branches = self._seed_branches()
        users = self._seed_users(roles, branches, password)

        if options['skip_demo']:
            self.stdout.write(self.style.SUCCESS('Core seed complete.'))
            return

        classes = self._seed_classes()
        insurers = self._seed_insurers()
        products = self._seed_products(classes, insurers)
        clients = self._seed_clients(branches, users)

        if Policy.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    'Operational demo data already exists; skipping policies and '
                    'related transactions.'
                )
            )
        else:
            self._seed_operations(
                clients, products, insurers, branches, users
            )

        self.stdout.write(self.style.SUCCESS('Seed complete.'))
        self.stdout.write('Login with admin@ibms.local / ' + password)

    def _seed_permissions(self):
        permissions = {}
        for module, actions in MODULE_ACTIONS.items():
            for action in actions:
                perm, _ = Permission.objects.get_or_create(
                    module=module,
                    action=action,
                    defaults={
                        'description': f'{action.title()} access for {module}'
                    },
                )
                permissions[f'{module}:{action}'] = perm
        self.stdout.write(f'  Permissions: {len(permissions)}')
        return permissions

    def _seed_roles(self, permissions):
        roles = {}
        for code, name in ROLE_NAMES.items():
            role, _ = Role.objects.update_or_create(
                code=code,
                defaults={
                    'name': name[0],
                    'description': name[1],
                    'is_system': code == 'ADMIN',
                },
            )
            wanted = ROLE_GRANTS.get(code, set())
            RolePermission.objects.filter(role=role).exclude(
                permission__in=[
                    permissions[c] for c in wanted if c in permissions
                ]
            ).delete()
            for permission_code in wanted:
                permission = permissions.get(permission_code)
                if permission:
                    RolePermission.objects.get_or_create(
                        role=role, permission=permission
                    )
            roles[code] = role
        self.stdout.write(f'  Roles: {len(roles)}')
        return roles

    def _seed_branches(self):
        specs = [
            ('HQ', 'Head Office', 'Plot 12 Kampala Road, Kampala'),
            ('KLA', 'Kampala Branch', 'Plot 45 Nkrumah Road, Kampala'),
            ('ENT', 'Entebbe Branch', 'Plot 8 Airport Road, Entebbe'),
            ('GUL', 'Gulu Branch', 'Plot 21 Acholi Road, Gulu'),
        ]
        branches = {}
        for code, name, address in specs:
            branch, _ = Branch.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'physical_address': address,
                    'phone': '+256 414 000 000',
                    'email': f'{code.lower()}@ibms.local',
                    'is_active': True,
                },
            )
            branches[code] = branch
        self.stdout.write(f'  Branches: {len(branches)}')
        return branches

    def _seed_users(self, roles, branches, password):
        specs = [
            ('admin', 'admin@ibms.local', 'System', 'Administrator', 'ADMIN', 'HQ'),
            ('md', 'md@ibms.local', 'Mary', 'Nakato', 'MD', 'HQ'),
            ('ops', 'ops@ibms.local', 'Samuel', 'Okwir', 'OPS', 'HQ'),
            ('branch', 'branch@ibms.local', 'Alice', 'Achieng', 'BRANCH', 'KLA'),
            ('broker', 'broker@ibms.local', 'Brian', 'Ssemanda', 'BROKER', 'KLA'),
            ('underwriting', 'underwriting@ibms.local', 'Patricia', 'Namuli', 'UNDERWRITING', 'HQ'),
            ('claims', 'claims@ibms.local', 'David', 'Mugisha', 'CLAIMS', 'HQ'),
            ('finance', 'finance@ibms.local', 'Esther', 'Nabirye', 'FINANCE', 'HQ'),
            ('service', 'service@ibms.local', 'Grace', 'Atim', 'SERVICE', 'KLA'),
            ('auditor', 'auditor@ibms.local', 'Robert', 'Kato', 'AUDITOR', 'HQ'),
        ]
        users = {}
        for index, (key, email, first, last, role_code, branch_code) in enumerate(
            specs, start=1
        ):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'employee_no': f'EMP-{index:04d}',
                    'phone': f'+256 700 000 {index:03d}',
                    'role': roles[role_code],
                    'branch': branches[branch_code],
                    'is_active': True,
                    'is_staff': role_code == 'ADMIN',
                    'is_superuser': role_code == 'ADMIN',
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
            else:
                user.role = roles[role_code]
                user.branch = branches[branch_code]
                user.is_active = True
                user.save(update_fields=['role', 'branch', 'is_active'])
            users[key] = user
        self.stdout.write(f'  Users: {len(users)}')
        return users

    def _seed_classes(self):
        specs = [
            ('MOTOR', 'Motor', ClassCategory.GENERAL),
            ('FIRE', 'Fire & Property', ClassCategory.GENERAL),
            ('ACC', 'Accident & Personal Lines', ClassCategory.GENERAL),
            ('LIAB', 'Liability', ClassCategory.GENERAL),
            ('MARINE', 'Marine & Aviation', ClassCategory.GENERAL),
            ('ENG', 'Engineering', ClassCategory.GENERAL),
            ('AGR', 'Agriculture', ClassCategory.GENERAL),
            ('HEALTH', 'Health & Medical', ClassCategory.GENERAL),
            ('LIFE', 'Life', ClassCategory.LIFE),
        ]
        classes = {}
        for code, name, category in specs:
            obj, _ = InsuranceClass.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'category': category,
                    'description': f'{name} insurance class',
                    'is_active': True,
                },
            )
            classes[code] = obj
        self.stdout.write(f'  Insurance classes: {len(classes)}')
        return classes

    def _seed_insurers(self):
        specs = [
            ('UAP', 'UAP Old Mutual Insurance'),
            ('JUB', 'Jubilee Insurance Uganda'),
            ('BRITAM', 'Britam Insurance Uganda'),
            ('SANLAM', 'Sanlam General Insurance'),
            ('NIC', 'NIC General Insurance'),
            ('CASE', 'Case Medical Care'),
            ('PRUDENTIAL', 'Prudential Assurance Uganda'),
        ]
        insurers = {}
        for code, name in specs:
            insurer, _ = Insurer.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'email': f'{code.lower()}@insurer.local',
                    'phone': '+256 414 100 000',
                    'physical_address': 'Kampala, Uganda',
                    'is_active': True,
                },
            )
            insurers[code] = insurer
            InsurerContact.objects.get_or_create(
                insurer=insurer,
                full_name=f'{name} Underwriting',
                defaults={
                    'job_title': 'Underwriting Manager',
                    'email': f'underwriting@{code.lower()}.insurer.local',
                    'phone': '+256 414 100 100',
                    'is_primary': True,
                },
            )
            InsurerBranch.objects.get_or_create(
                insurer=insurer,
                name=f'{name} — Kampala',
                defaults={
                    'address': 'Plot 1, Kampala Road, Kampala',
                    'phone': '+256 414 100 200',
                    'email': f'kampala@{code.lower()}.insurer.local',
                    'is_active': True,
                },
            )
        self.stdout.write(f'  Insurers: {len(insurers)}')
        return insurers

    def _seed_products(self, classes, insurers):
        specs = [
            ('MOT-COM', 'Comprehensive Motor', 'MOTOR', 'UAP', '12.50'),
            ('MOT-TP', 'Third Party Motor', 'MOTOR', 'JUB', '10.00'),
            ('FIRE-IND', 'Industrial Fire', 'FIRE', 'BRITAM', '15.00'),
            ('HOME', 'Home Insurance', 'FIRE', 'SANLAM', '12.00'),
            ('MARINE-CARGO', 'Marine Cargo', 'MARINE', 'NIC', '10.00'),
            ('LIAB-PUB', 'Public Liability', 'LIAB', 'UAP', '15.00'),
            ('HEALTH-CORP', 'Corporate Medical', 'HEALTH', 'CASE', '8.00'),
            ('LIFE-GRP', 'Group Life', 'LIFE', 'PRUDENTIAL', '10.00'),
            ('ENG-ALL', 'Engineering All Risks', 'ENG', 'JUB', '12.00'),
            ('AGR-CROP', 'Crop Insurance', 'AGR', 'BRITAM', '10.00'),
        ]
        products = {}
        for code, name, class_code, insurer_code, rate in specs:
            product, _ = Product.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'insurance_class': classes[class_code],
                    'insurer': insurers[insurer_code],
                    'minimum_premium': Decimal('25000.00'),
                    'commission_rate': Decimal(rate),
                    'is_active': True,
                },
            )
            products[code] = product
        self.stdout.write(f'  Products: {len(products)}')
        return products

    def _seed_clients(self, branches, users):
        specs = [
            ('CLI-DEMO-01', ClientType.INDIVIDUAL, 'John Okello', 'KLA', KycStatus.VERIFIED, 'M'),
            ('CLI-DEMO-02', ClientType.INDIVIDUAL, 'Sarah Namutebi', 'KLA', KycStatus.VERIFIED, 'F'),
            ('CLI-DEMO-03', ClientType.CORPORATE, 'Acme Traders Ltd', 'HQ', KycStatus.VERIFIED, ''),
            ('CLI-DEMO-04', ClientType.CORPORATE, 'Kampala Hotels Ltd', 'KLA', KycStatus.VERIFIED, ''),
            ('CLI-DEMO-05', ClientType.CORPORATE, 'Lakeview Fisheries Ltd', 'ENT', KycStatus.PENDING, ''),
            ('CLI-DEMO-06', ClientType.INDIVIDUAL, 'Dr. Peter Ssemakula', 'HQ', KycStatus.VERIFIED, 'M'),
            ('CLI-DEMO-07', ClientType.CORPORATE, 'Greenfields Agro Ltd', 'GUL', KycStatus.VERIFIED, ''),
            ('CLI-DEMO-08', ClientType.CORPORATE, 'Metro Logistics Ltd', 'KLA', KycStatus.VERIFIED, ''),
            ('CLI-DEMO-09', ClientType.INDIVIDUAL, 'Grace Atim', 'GUL', KycStatus.VERIFIED, 'F'),
            ('CLI-DEMO-10', ClientType.CORPORATE, 'Nile Engineering Ltd', 'ENT', KycStatus.VERIFIED, ''),
        ]
        clients = []
        for index, (number, ctype, name, branch_code, kyc, gender) in enumerate(
            specs, start=1
        ):
            client, _ = Client.objects.update_or_create(
                client_number=number,
                defaults={
                    'client_type': ctype,
                    'name': name,
                    'national_id': f'CM{900000 + index}ABC' if ctype == ClientType.INDIVIDUAL else '',
                    'registration_no': f'8001000{index}' if ctype == ClientType.CORPORATE else '',
                    'tin': f'100000{index}',
                    'occupation': 'Business' if ctype == ClientType.CORPORATE else 'Professional',
                    'gender': gender,
                    'email': f'client{index}@example.com',
                    'phone': f'+256 772 000 {index:03d}',
                    'alt_phone': f'+256 702 000 {index:03d}',
                    'physical_address': 'Kampala, Uganda',
                    'kyc_status': kyc,
                    'kyc_verified_at': timezone.now() if kyc == KycStatus.VERIFIED else None,
                    'next_of_kin_name': 'Family Contact',
                    'next_of_kin_phone': f'+256 782 000 {index:03d}',
                    'next_of_kin_relationship': 'Relative',
                    'branch': branches[branch_code],
                    'relationship_manager': users['broker'],
                    'created_by': users['admin'],
                    'is_active': True,
                },
            )
            if ctype == ClientType.CORPORATE:
                ClientDirector.objects.get_or_create(
                    client=client,
                    full_name=f'Director {index}',
                    defaults={
                        'national_id': f'DIR{index:04d}',
                        'email': f'director{index}@example.com',
                        'phone': f'+256 752 000 {index:03d}',
                        'ownership_percentage': Decimal('100.00'),
                    },
                )
            ClientContact.objects.get_or_create(
                client=client,
                full_name=f'Contact {index}',
                defaults={
                    'job_title': 'Finance Manager',
                    'email': f'contact{index}@example.com',
                    'phone': f'+256 762 000 {index:03d}',
                    'is_primary': True,
                },
            )
            clients.append(client)
        self.stdout.write(f'  Clients: {len(clients)}')
        return clients

    def _seed_operations(self, clients, products, insurers, branches, users):
        today = timezone.localdate()
        broker = users['broker']
        admin = users['admin']
        finance = users['finance']
        claims_user = users['claims']
        ops = users['ops']

        risk_specs = [
            ('RSK-DEMO-01', 0, 'Motor', 'Kampala', 'Private motor vehicle - Toyota Harrier'),
            ('RSK-DEMO-02', 2, 'Fire', 'Kampala', 'Warehouse and stock'),
            ('RSK-DEMO-03', 3, 'Fire', 'Kampala', 'Hotel building and contents'),
            ('RSK-DEMO-04', 4, 'Marine', 'Entebbe', 'Fishing equipment and cargo'),
            ('RSK-DEMO-05', 7, 'Motor', 'Kampala', 'Fleet of delivery trucks'),
            ('RSK-DEMO-06', 9, 'Engineering', 'Entebbe', 'Construction plant'),
            ('RSK-DEMO-07', 6, 'Agriculture', 'Gulu', 'Crop stock and irrigation'),
            ('RSK-DEMO-08', 5, 'Health', 'Kampala', 'Medical malpractice and staff cover'),
        ]
        risks = []
        for number, client_index, category, location, description in risk_specs:
            risk, _ = Risk.objects.get_or_create(
                risk_number=number,
                defaults={
                    'client': clients[client_index],
                    'category': category,
                    'location': location,
                    'description': description,
                    'asset_details': {'source': 'demo'},
                    'previous_claims': 'None',
                    'status': RiskStatus.OPEN,
                    'created_by': broker,
                },
            )
            risks.append(risk)

        MotorDetail.objects.get_or_create(
            risk=risks[0],
            registration_number='UBG 123A',
            defaults={
                'chassis_number': 'JTMBFREV00J000001',
                'engine_number': '2AZ-0000001',
                'make': 'Toyota',
                'model': 'Harrier',
                'year': 2019,
                'vehicle_value': Decimal('65000000.00'),
                'driver_name': 'John Okello',
                'driver_license_no': 'DL-100001',
                'usage': 'Private',
            },
        )
        MotorDetail.objects.get_or_create(
            risk=risks[4],
            registration_number='UBF 456B',
            defaults={
                'chassis_number': 'JTMBFREV00J000002',
                'engine_number': '2AZ-0000002',
                'make': 'Isuzu',
                'model': 'FRR',
                'year': 2018,
                'vehicle_value': Decimal('95000000.00'),
                'driver_name': 'Metro Driver',
                'driver_license_no': 'DL-100002',
                'usage': 'Commercial',
            },
        )

        policy_specs = [
            {
                'client': 0,
                'product': 'MOT-COM',
                'insurer': 'UAP',
                'risk': 0,
                'premium': Decimal('3200000.00'),
                'taxes': Decimal('480000.00'),
                'sum_insured': Decimal('65000000.00'),
                'start': -300,
                'end': 65,
                'frequency': 'ANNUAL',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 2,
                'product': 'FIRE-IND',
                'insurer': 'BRITAM',
                'risk': 1,
                'premium': Decimal('7200000.00'),
                'taxes': Decimal('1080000.00'),
                'sum_insured': Decimal('450000000.00'),
                'start': -200,
                'end': 165,
                'frequency': 'QUARTERLY',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 3,
                'product': 'HOME',
                'insurer': 'SANLAM',
                'risk': 2,
                'premium': Decimal('4100000.00'),
                'taxes': Decimal('615000.00'),
                'sum_insured': Decimal('300000000.00'),
                'start': -30,
                'end': 335,
                'frequency': 'SEMI_ANNUAL',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 4,
                'product': 'MARINE-CARGO',
                'insurer': 'NIC',
                'risk': 3,
                'premium': Decimal('2800000.00'),
                'taxes': Decimal('420000.00'),
                'sum_insured': Decimal('180000000.00'),
                'start': -400,
                'end': 45,
                'frequency': 'ANNUAL',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 7,
                'product': 'MOT-TP',
                'insurer': 'JUB',
                'risk': 4,
                'premium': Decimal('1800000.00'),
                'taxes': Decimal('270000.00'),
                'sum_insured': Decimal('95000000.00'),
                'start': -500,
                'end': -30,
                'frequency': 'ANNUAL',
                'status': PolicyStatus.EXPIRED,
            },
            {
                'client': 9,
                'product': 'ENG-ALL',
                'insurer': 'JUB',
                'risk': 5,
                'premium': Decimal('5600000.00'),
                'taxes': Decimal('840000.00'),
                'sum_insured': Decimal('380000000.00'),
                'start': -60,
                'end': 305,
                'frequency': 'QUARTERLY',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 6,
                'product': 'AGR-CROP',
                'insurer': 'BRITAM',
                'risk': 6,
                'premium': Decimal('1500000.00'),
                'taxes': Decimal('225000.00'),
                'sum_insured': Decimal('120000000.00'),
                'start': -120,
                'end': 245,
                'frequency': 'ANNUAL',
                'status': PolicyStatus.ACTIVE,
            },
            {
                'client': 5,
                'product': 'HEALTH-CORP',
                'insurer': 'CASE',
                'risk': 7,
                'premium': Decimal('6900000.00'),
                'taxes': Decimal('1035000.00'),
                'sum_insured': Decimal('0.00'),
                'start': -15,
                'end': 350,
                'frequency': 'MONTHLY',
                'status': PolicyStatus.ACTIVE,
            },
        ]

        policies = []
        for spec in policy_specs:
            start_date = today + timedelta(days=spec['start'])
            end_date = today + timedelta(days=spec['end'])
            product = products[spec['product']]
            insurer = insurers[spec['insurer']]
            quotation = Quotation.objects.create(
                quotation_number=next_number(Quotation, 'quotation_number', 'QT'),
                client=clients[spec['client']],
                product=product,
                risk=risks[spec['risk']],
                broker=broker,
                branch=clients[spec['client']].branch,
                sum_insured=spec['sum_insured'],
                premium=spec['premium'],
                taxes=spec['taxes'],
                total_premium=spec['premium'] + spec['taxes'],
                valid_from=today - timedelta(days=15),
                valid_to=today + timedelta(days=15),
                status=QuotationStatus.SELECTED,
                selected_insurer=insurer,
                notes='SEED quotation',
                created_by=broker,
            )
            InsurerQuote.objects.create(
                quotation=quotation,
                insurer=insurer,
                premium=spec['premium'],
                taxes=spec['taxes'],
                terms='Standard terms',
                status=QuoteResponseStatus.RECEIVED,
                received_at=timezone.now() - timedelta(days=10),
                valid_until=today + timedelta(days=15),
            )
            InsurerQuote.objects.create(
                quotation=quotation,
                insurer=insurers['UAP'] if insurer.code != 'UAP' else insurers['JUB'],
                premium=spec['premium'] + Decimal('150000.00'),
                taxes=spec['taxes'],
                terms='Alternative terms',
                status=QuoteResponseStatus.RECEIVED,
                received_at=timezone.now() - timedelta(days=9),
                valid_until=today + timedelta(days=15),
            )
            policy = create_policy(
                {
                    'quotation': quotation,
                    'start_date': start_date,
                    'end_date': end_date,
                    'payment_frequency': spec['frequency'],
                    'status': spec['status'],
                    'notes': 'SEED policy',
                },
                broker,
                quotation,
            )
            policies.append(policy)

        payment_specs = [
            (0, Decimal('3680000.00'), PaymentMethod.BANK_TRANSFER),
            (1, Decimal('3000000.00'), PaymentMethod.CHEQUE),
            (2, Decimal('4715000.00'), PaymentMethod.MOBILE_MONEY),
            (3, Decimal('1500000.00'), PaymentMethod.BANK_TRANSFER),
            (5, Decimal('2000000.00'), PaymentMethod.CASH),
        ]
        for policy_index, amount, method in payment_specs:
            policy = policies[policy_index]
            invoice = policy.invoices.first()
            payment = Payment.objects.create(
                receipt_number=next_number(Payment, 'receipt_number', 'RCT'),
                client=policy.client,
                policy=policy,
                invoice=invoice,
                amount=amount,
                method=method,
                reference=f'REF-{policy_index + 1:04d}',
                paid_at=timezone.now() - timedelta(days=policy_index * 7 + 3),
                status=PaymentStatus.CONFIRMED,
                received_by=finance,
                notes='SEED payment',
            )
            allocate_payment(payment)

        claim_specs = [
            (0, 'Accidental collision', 24, Decimal('1200000.00'), Decimal('0.00'), ClaimStatus.UNDER_REVIEW),
            (1, 'Fire damage to warehouse', 40, Decimal('4500000.00'), Decimal('0.00'), ClaimStatus.RESERVED),
            (2, 'Water damage', 20, Decimal('800000.00'), Decimal('0.00'), ClaimStatus.NOTIFIED),
            (3, 'Cargo damage in transit', 55, Decimal('1600000.00'), Decimal('0.00'), ClaimStatus.APPROVED),
            (5, 'Plant breakdown', 70, Decimal('2200000.00'), Decimal('1800000.00'), ClaimStatus.SETTLED),
        ]
        for policy_index, cause, days_ago, reserve, paid, status in claim_specs:
            policy = policies[policy_index]
            Claim.objects.create(
                claim_number=next_number(Claim, 'claim_number', 'CLM'),
                policy=policy,
                client=policy.client,
                date_of_loss=today - timedelta(days=days_ago),
                cause=cause,
                description=f'SEED claim: {cause}',
                surveyor='Independent Loss Adjuster',
                reserve_amount=reserve,
                paid_amount=paid,
                recovered_amount=Decimal('0.00'),
                status=status,
                settled_at=timezone.now() if status == ClaimStatus.SETTLED else None,
                notes='SEED claim',
                handled_by=claims_user,
            )

        endorsement_specs = [
            (0, EndorsementType.ADDITION, EndorsementStatus.APPROVED, Decimal('150000.00'), 'Add theft cover'),
            (1, EndorsementType.AMENDMENT, EndorsementStatus.PENDING_APPROVAL, Decimal('220000.00'), 'Increase sum insured'),
            (2, EndorsementType.DELETION, EndorsementStatus.DRAFT, Decimal('-50000.00'), 'Remove portable items'),
        ]
        for policy_index, etype, status, adjustment, description in endorsement_specs:
            policy = policies[policy_index]
            Endorsement.objects.create(
                endorsement_number=next_number(
                    Endorsement, 'endorsement_number', 'END'
                ),
                policy=policy,
                type=etype,
                description=description,
                effective_date=today,
                premium_adjustment=adjustment,
                status=status,
                requested_by=broker,
                approved_by=ops if status == EndorsementStatus.APPROVED else None,
                approved_at=timezone.now() if status == EndorsementStatus.APPROVED else None,
            )

        CreditDebitNote.objects.create(
            note_number=next_number(CreditDebitNote, 'note_number', 'DBN'),
            note_type='DEBIT',
            client=policies[0].client,
            policy=policies[0],
            amount=Decimal('150000.00'),
            reason='Endorsement premium adjustment',
            status='ISSUED',
            issue_date=today,
            created_by=finance,
        )
        CreditDebitNote.objects.create(
            note_number=next_number(CreditDebitNote, 'note_number', 'CRN'),
            note_type='CREDIT',
            client=policies[2].client,
            policy=policies[2],
            amount=Decimal('50000.00'),
            reason='Removal of portable items',
            status='ISSUED',
            issue_date=today,
            created_by=finance,
        )

        Remittance.objects.create(
            remittance_number=next_number(
                Remittance, 'remittance_number', 'REM'
            ),
            insurer=insurers['UAP'],
            branch=branches['KLA'],
            period_from=today - timedelta(days=60),
            period_to=today - timedelta(days=30),
            gross_premium=Decimal('3200000.00'),
            commission_retained=Decimal('400000.00'),
            taxes=Decimal('480000.00'),
            net_amount=Decimal('2800000.00'),
            status='PAID',
            paid_at=timezone.now() - timedelta(days=25),
            reference='REM-REF-001',
            created_by=finance,
        )
        Remittance.objects.create(
            remittance_number=next_number(
                Remittance, 'remittance_number', 'REM'
            ),
            insurer=insurers['BRITAM'],
            branch=branches['HQ'],
            period_from=today - timedelta(days=30),
            period_to=today,
            gross_premium=Decimal('7200000.00'),
            commission_retained=Decimal('1080000.00'),
            taxes=Decimal('1080000.00'),
            net_amount=Decimal('6120000.00'),
            status='PENDING',
            reference='REM-REF-002',
            created_by=finance,
        )

        task_specs = [
            ('Call John Okello about motor renewal', users['broker'], TaskStatus.IN_PROGRESS, -2, Priority.HIGH),
            ('Prepare renewal quotation for Acme Traders', users['broker'], TaskStatus.TODO, 5, Priority.URGENT),
            ('Follow up outstanding premium - Kampala Hotels', users['finance'], TaskStatus.TODO, -1, Priority.HIGH),
            ('Submit claim documents to insurer', users['claims'], TaskStatus.IN_PROGRESS, 3, Priority.MEDIUM),
            ('Verify KYC for Lakeview Fisheries', users['service'], TaskStatus.TODO, 7, Priority.MEDIUM),
            ('Review commission reconciliation', users['finance'], TaskStatus.DONE, -10, Priority.LOW),
        ]
        for title, assignee, status, due_offset, priority in task_specs:
            Task.objects.create(
                title=title,
                description='SEED task',
                assigned_to=assignee,
                due_date=today + timedelta(days=due_offset),
                priority=priority,
                status=status,
                created_by=ops,
                completed_at=timezone.now() if status == TaskStatus.DONE else None,
            )

        for client_index, channel, subject in [
            (0, CommChannel.PHONE, 'Renewal reminder call'),
            (2, CommChannel.EMAIL, 'Policy documents sent'),
            (3, CommChannel.MEETING, 'Quarterly review meeting'),
            (4, CommChannel.SMS, 'Premium due reminder'),
            (7, CommChannel.EMAIL, 'Fleet policy schedule'),
        ]:
            Communication.objects.create(
                client=clients[client_index],
                channel=channel,
                subject=subject,
                message=f'SEED communication: {subject}',
                sent_at=timezone.now() - timedelta(days=client_index),
                status='SENT',
                sent_by=users['service'],
            )

        high_value = Quotation.objects.create(
            quotation_number=next_number(Quotation, 'quotation_number', 'QT'),
            client=clients[2],
            product=products['FIRE-IND'],
            risk=risks[1],
            broker=broker,
            branch=branches['HQ'],
            sum_insured=Decimal('900000000.00'),
            premium=Decimal('12000000.00'),
            taxes=Decimal('1800000.00'),
            total_premium=Decimal('13800000.00'),
            valid_from=today,
            valid_to=today + timedelta(days=30),
            status=QuotationStatus.SELECTED,
            selected_insurer=insurers['BRITAM'],
            notes='SEED high value quotation awaiting approval',
            created_by=broker,
        )
        InsurerQuote.objects.create(
            quotation=high_value,
            insurer=insurers['BRITAM'],
            premium=Decimal('12000000.00'),
            taxes=Decimal('1800000.00'),
            terms='High value terms',
            status=QuoteResponseStatus.RECEIVED,
            received_at=timezone.now(),
            valid_until=today + timedelta(days=30),
        )
        Approval.objects.create(
            type=ApprovalType.QUOTATION,
            entity_type='Quotation',
            entity_id=str(high_value.id),
            amount=high_value.total_premium,
            requested_by=broker,
            status=ApprovalStatus.PENDING,
            comments='High value quotation requires MD approval',
        )
        Approval.objects.create(
            type=ApprovalType.COMMISSION_OVERRIDE,
            entity_type='Commission',
            entity_id=str(policies[2].commissions.first().id),
            amount=Decimal('75000.00'),
            requested_by=finance,
            approver=ops,
            status=ApprovalStatus.APPROVED,
            comments='Approved override for strategic client',
            decided_at=timezone.now() - timedelta(days=5),
        )

        Document.objects.create(
            entity_type='Policy',
            entity_id=policies[0].id,
            name='Motor Policy Schedule.txt',
            category='Policy',
            file=ContentFile(
                b'IBMS demo policy schedule for ' + policies[0].policy_number.encode(),
                name='motor_policy_schedule.txt',
            ),
            uploaded_by=users['service'],
            version=1,
            is_current=True,
        )
        Document.objects.create(
            entity_type='Client',
            entity_id=clients[2].id,
            name='KYC Documents.txt',
            category='KYC',
            file=ContentFile(
                b'IBMS demo KYC documents for ' + clients[2].name.encode(),
                name='kyc_documents.txt',
            ),
            uploaded_by=users['service'],
            version=1,
            is_current=True,
        )

        for action, module, description, actor in [
            ('LOGIN', 'auth', 'Successful login', admin),
            ('CREATE', 'policies', 'Policy created from quotation', broker),
            ('UPDATE', 'premiums', 'Payment allocated to policy', finance),
            ('APPROVE', 'endorsements', 'Endorsement approved', ops),
            ('CREATE', 'claims', 'Claim registered', claims_user),
        ]:
            AuditLog.objects.create(
                user=actor,
                user_email=actor.email,
                action=action,
                module=module,
                description=description,
                entity_type=module.title(),
                entity_id=str(policies[0].id),
                ip_address='127.0.0.1',
                user_agent='seed-command',
            )

        self.stdout.write(f'  Policies: {len(policies)}')
        self.stdout.write('  Financial, claims, renewal and workspace data created')
