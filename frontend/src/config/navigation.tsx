import {
  ArrowLeftRight,
  BadgeCheck,
  BarChart3,
  Building2,
  Car,
  CheckSquare,
  Contact,
  CreditCard,
  FileMinus,
  FilePenLine,
  FileText,
  FolderOpen,
  HeartPulse,
  IdCard,
  KeyRound,
  LayoutDashboard,
  MapPin,
  MessageSquare,
  MessagesSquare,
  Package,
  Percent,
  Receipt,
  RefreshCw,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  Tags,
  UserCog,
  Users,
  Wallet,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  permission?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navigation: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      {
        label: 'Dashboard',
        path: '/dashboard',
        icon: LayoutDashboard,
        permission: 'dashboard:view',
      },
      {
        label: 'Reports',
        path: '/reports',
        icon: BarChart3,
        permission: 'reports:view',
      },
    ],
  },
  {
    label: 'Customer Relationship',
    items: [
      { label: 'Clients', path: '/clients', icon: Users, permission: 'clients:view' },
      {
        label: 'Client Contacts',
        path: '/client-contacts',
        icon: Contact,
        permission: 'clients:view',
      },
      {
        label: 'Client Directors',
        path: '/client-directors',
        icon: IdCard,
        permission: 'clients:view',
      },
      {
        label: 'Insurers',
        path: '/insurers',
        icon: Building2,
        permission: 'insurers:view',
      },
      {
        label: 'Insurer Contacts',
        path: '/insurer-contacts',
        icon: MessagesSquare,
        permission: 'insurers:view',
      },
      {
        label: 'Insurer Branches',
        path: '/insurer-branches',
        icon: MapPin,
        permission: 'insurers:view',
      },
      {
        label: 'Products',
        path: '/products',
        icon: Package,
        permission: 'products:view',
      },
      {
        label: 'Insurance Classes',
        path: '/insurance-classes',
        icon: Tags,
        permission: 'products:view',
      },
    ],
  },
  {
    label: 'Brokerage Operations',
    items: [
      { label: 'Risks', path: '/risks', icon: ShieldAlert, permission: 'risks:view' },
      {
        label: 'Motor Details',
        path: '/motor-details',
        icon: Car,
        permission: 'motor:view',
      },
      {
        label: 'Quotations',
        path: '/quotations',
        icon: FileText,
        permission: 'quotations:view',
      },
      {
        label: 'Insurer Quotes',
        path: '/insurer-quotes',
        icon: MessagesSquare,
        permission: 'quotations:view',
      },
      {
        label: 'Policies',
        path: '/policies',
        icon: ShieldCheck,
        permission: 'policies:view',
      },
      {
        label: 'Endorsements',
        path: '/endorsements',
        icon: FilePenLine,
        permission: 'endorsements:view',
      },
      {
        label: 'Renewals',
        path: '/renewals',
        icon: RefreshCw,
        permission: 'renewals:view',
      },
    ],
  },
  {
    label: 'Finance',
    items: [
      { label: 'Premiums', path: '/premiums', icon: Wallet, permission: 'premiums:view' },
      { label: 'Invoices', path: '/invoices', icon: Receipt, permission: 'invoices:view' },
      {
        label: 'Payments',
        path: '/payments',
        icon: CreditCard,
        permission: 'payments:view',
      },
      {
        label: 'Credit / Debit Notes',
        path: '/credit-debit-notes',
        icon: FileMinus,
        permission: 'notes:view',
      },
      {
        label: 'Commissions',
        path: '/commissions',
        icon: Percent,
        permission: 'commissions:view',
      },
      {
        label: 'Remittances',
        path: '/remittances',
        icon: ArrowLeftRight,
        permission: 'remittances:view',
      },
    ],
  },
  {
    label: 'Claims',
    items: [
      {
        label: 'Claims',
        path: '/claims',
        icon: HeartPulse,
        permission: 'claims:view',
      },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { label: 'Tasks', path: '/tasks', icon: CheckSquare, permission: 'tasks:view' },
      {
        label: 'Approvals',
        path: '/approvals',
        icon: BadgeCheck,
        permission: 'approvals:view',
      },
      {
        label: 'Documents',
        path: '/documents',
        icon: FolderOpen,
        permission: 'documents:view',
      },
      {
        label: 'Communications',
        path: '/communications',
        icon: MessageSquare,
        permission: 'communications:view',
      },
    ],
  },
  {
    label: 'Administration',
    items: [
      { label: 'Users', path: '/users', icon: UserCog, permission: 'users:view' },
      { label: 'Roles & Permissions', path: '/roles', icon: KeyRound, permission: 'roles:view' },
      { label: 'Branches', path: '/branches', icon: MapPin, permission: 'branches:view' },
      { label: 'Audit Trail', path: '/audit-logs', icon: ScrollText, permission: 'audit:view' },
    ],
  },
];
