from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import AuditLog, Branch, Permission, Role, User
from accounts.serializers import (
    AuditLogSerializer,
    BranchSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserSerializer,
)
from common.audit import log_action
from common.throttles import LoginRateThrottle
from common.viewsets import BaseModelViewSet, BaseReadOnlyViewSet, SoftDeleteMixin


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''
        if not email or not password:
            return Response(
                {'statusCode': 400, 'message': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.select_related('role', 'branch').filter(email=email).first()
        if not user:
            log_action(
                request,
                'LOGIN_FAILED',
                'auth',
                'User',
                '',
                f'Unknown email {email}',
            )
            return Response(
                {'statusCode': 401, 'message': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'statusCode': 401, 'message': 'Account is inactive'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.locked_until and user.locked_until > timezone.now():
            return Response(
                {
                    'statusCode': 401,
                    'message': 'Account is temporarily locked. Try again later.',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        authenticated = authenticate(
            request, username=email, password=password
        )
        if not authenticated:
            attempts = user.failed_login_attempts + 1
            locked = attempts >= settings.MAX_LOGIN_ATTEMPTS
            user.failed_login_attempts = 0 if locked else attempts
            if locked:
                user.locked_until = timezone.now() + timezone.timedelta(
                    minutes=settings.LOCK_MINUTES
                )
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            log_action(
                request,
                'LOGIN_FAILED',
                'auth',
                'User',
                user.id,
                'Account locked after repeated failures'
                if locked
                else f'Invalid password (attempt {attempts})',
            )
            message = (
                f'Too many failed attempts. Account locked for '
                f'{settings.LOCK_MINUTES} minutes.'
                if locked
                else 'Invalid email or password'
            )
            return Response(
                {'statusCode': 401, 'message': message},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = timezone.now()
        user.last_login_at = timezone.now()
        user.save(
            update_fields=[
                'failed_login_attempts',
                'locked_until',
                'last_login',
                'last_login_at',
            ]
        )
        refresh = RefreshToken.for_user(user)
        log_action(
            request,
            'LOGIN',
            'auth',
            'User',
            user.id,
            'Successful login',
            user=user,
        )
        data = UserSerializer(user, context={'request': request}).data
        return Response(
            {
                'data': {
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': data,
                }
            }
        )


class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass
        log_action(
            request,
            'LOGOUT',
            'auth',
            'User',
            request.user.id,
            'User logged out',
        )
        return Response({'data': {'success': True}})


class MeView(APIView):
    def get(self, request):
        return Response(
            {'data': UserSerializer(request.user, context={'request': request}).data}
        )


class ChangePasswordView(APIView):
    def post(self, request):
        current = request.data.get('currentPassword') or request.data.get(
            'current_password'
        )
        new = request.data.get('newPassword') or request.data.get('new_password')
        if not current or not new:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Current and new password are required',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        if not user.check_password(current):
            return Response(
                {'statusCode': 400, 'message': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new, user)
        except DjangoValidationError as exc:
            return Response(
                {'statusCode': 400, 'message': '; '.join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        log_action(
            request,
            'UPDATE',
            'users',
            'User',
            user.id,
            'Password changed',
        )
        return Response({'data': {'success': True}})


class BranchViewSet(SoftDeleteMixin, BaseModelViewSet):
    module = 'branches'
    audit_entity = 'Branch'
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'email']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['name']


class RoleViewSet(BaseModelViewSet):
    module = 'roles'
    audit_entity = 'Role'
    queryset = Role.objects.prefetch_related(
        'role_permissions__permission', 'users'
    )
    serializer_class = RoleSerializer
    filterset_fields = ['is_system']
    search_fields = ['code', 'name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('System roles cannot be deleted.')
        super().perform_destroy(instance)


class PermissionViewSet(BaseReadOnlyViewSet):
    module = 'roles'
    audit_entity = 'Permission'
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    filterset_fields = ['module', 'action']
    search_fields = ['module', 'action']
    ordering = ['module', 'action']
    pagination_class = None


class UserViewSet(SoftDeleteMixin, BaseModelViewSet):
    module = 'users'
    audit_entity = 'User'
    queryset = User.objects.select_related('role', 'branch').all()
    serializer_class = UserSerializer
    filterset_fields = ['role', 'branch', 'is_active']
    search_fields = ['first_name', 'last_name', 'email', 'employee_no', 'phone']
    ordering_fields = ['first_name', 'last_name', 'email', 'created_at']
    ordering = ['first_name', 'last_name']
    extra_permissions = {'unlock': 'users:edit'}

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])
        log_action(
            request,
            'UPDATE',
            'users',
            'User',
            user.id,
            'Account unlocked',
        )
        return Response(
            {'data': UserSerializer(user, context={'request': request}).data}
        )

    def perform_create(self, serializer):
        user = serializer.save(created_by=self.request.user)
        log_action(
            self.request,
            'CREATE',
            'users',
            'User',
            user.id,
            'Created user',
        )

    def perform_update(self, serializer):
        user = serializer.save()
        log_action(
            self.request,
            'UPDATE',
            'users',
            'User',
            user.id,
            'Updated user',
        )

    def perform_destroy(self, instance):
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You cannot deactivate your own account.')
        super().perform_destroy(instance)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            user = self.request.user
            if user.role and user.role.code == 'BRANCH' and user.branch_id:
                qs = qs.filter(branch_id=user.branch_id)
        return qs


class AuditLogViewSet(BaseReadOnlyViewSet):
    module = 'audit'
    audit_entity = 'AuditLog'
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    filterset_fields = ['action', 'module', 'user', 'entity_type']
    search_fields = [
        'description',
        'entity_id',
        'user_email',
        'user__first_name',
        'user__last_name',
    ]
    ordering_fields = ['created_at', 'action', 'module']
    ordering = ['-created_at']
# 2026-11-11T15:05:22Z user registration
# 2026-11-11T15:05:22Z JWT login
# 2026-11-11T15:05:22Z password hash fix
# 2026-11-11T15:06:07Z user registration
# 2026-11-11T15:06:07Z JWT login
# 2026-11-11T15:06:07Z password hash fix
