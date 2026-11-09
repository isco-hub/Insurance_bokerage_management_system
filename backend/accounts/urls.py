from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    AuditLogViewSet,
    BranchViewSet,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    PermissionViewSet,
    RoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register('branches', BranchViewSet, basename='branches')
router.register('roles', RoleViewSet, basename='roles')
router.register('permissions', PermissionViewSet, basename='permissions')
router.register('users', UserViewSet, basename='users')
router.register('audit-logs', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('', include(router.urls)),
]
