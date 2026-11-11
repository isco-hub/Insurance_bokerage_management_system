from rest_framework.permissions import BasePermission


class IsAuthenticatedAndPermitted(BasePermission):
    """Authenticates the request and enforces the view's module permission.

    Views expose ``get_required_permission()`` returning a ``module:action`` code
    (for example ``clients:view``). ADMIN bypasses the matrix; all other roles
    must hold the exact permission.
    """

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if not user.is_active:
            return False

        getter = getattr(view, 'get_required_permission', None)
        code = getter() if callable(getter) else None
        if not code:
            return True

        role = getattr(user, 'role', None)
        if role and role.code == 'ADMIN':
            return True
        if user.has_permission(code):
            return True
        self.message = f'Missing permission: {code}'
        return False
# 2026-11-11T15:05:23Z permission helpers
# 2026-11-11T15:06:07Z permission helpers
