from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.audit import log_action

ACTION_PERMISSIONS = {
    'list': 'view',
    'retrieve': 'view',
    'create': 'create',
    'update': 'edit',
    'partial_update': 'edit',
    'destroy': 'delete',
    'metadata': 'view',
}

BRANCH_SCOPED_ROLES = {'BRANCH', 'BROKER', 'SERVICE'}


class PermissionViewSetMixin:
    module = None
    extra_permissions = {}
    action_permissions = ACTION_PERMISSIONS
    scope_branch = False
    branch_filter = 'branch'
    audit_entity = None

    def get_required_permission(self):
        if not self.module:
            return None
        if self.action in self.extra_permissions:
            return self.extra_permissions[self.action]
        suffix = self.action_permissions.get(self.action, 'view')
        return f'{self.module}:{suffix}'

    def get_queryset(self):
        qs = super().get_queryset()
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None)
        if (
            self.scope_branch
            and user
            and getattr(user, 'is_authenticated', False)
            and getattr(user, 'role', None)
            and user.role.code in BRANCH_SCOPED_ROLES
            and user.branch_id
        ):
            qs = qs.filter(**{self.branch_filter: user.branch_id})
        return qs

    def _entity(self):
        return self.audit_entity or (self.module or 'record').rstrip('s').title()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'data': serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'data': serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'data': serializer.data})

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            self.request,
            'CREATE',
            self.module or 'system',
            self._entity(),
            getattr(instance, 'pk', ''),
            f'Created {self._entity()}',
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request,
            'UPDATE',
            self.module or 'system',
            self._entity(),
            getattr(instance, 'pk', ''),
            f'Updated {self._entity()}',
        )

    def perform_destroy(self, instance):
        entity_id = getattr(instance, 'pk', '')
        instance.delete()
        log_action(
            self.request,
            'DELETE',
            self.module or 'system',
            self._entity(),
            entity_id,
            f'Deleted {self._entity()}',
        )


class BaseModelViewSet(PermissionViewSetMixin, viewsets.ModelViewSet):
    pass


class BaseReadOnlyViewSet(PermissionViewSetMixin, viewsets.ReadOnlyModelViewSet):
    pass


class BaseGenericViewSet(PermissionViewSetMixin, viewsets.GenericViewSet):
    pass


class SoftDeleteMixin:
    """Deactivate master data instead of physically deleting it."""

    def perform_destroy(self, instance):
        updated = []
        if hasattr(instance, 'is_active'):
            instance.is_active = False
            updated.append('is_active')
        if hasattr(instance, 'deleted_at'):
            from django.utils import timezone

            instance.deleted_at = timezone.now()
            updated.append('deleted_at')
        if updated:
            instance.save(update_fields=updated)
        else:
            instance.delete()
        log_action(
            self.request,
            'DELETE',
            getattr(self, 'module', 'system'),
            getattr(self, 'audit_entity', 'Record'),
            getattr(instance, 'pk', ''),
            'Deactivated/deleted record',
        )
