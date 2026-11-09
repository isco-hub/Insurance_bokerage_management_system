from django.urls import include, path
from rest_framework.routers import DefaultRouter

from workspace.views import (
    ApprovalViewSet,
    CommunicationViewSet,
    DocumentViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='documents')
router.register('communications', CommunicationViewSet, basename='communications')
router.register('tasks', TaskViewSet, basename='tasks')
router.register('approvals', ApprovalViewSet, basename='approvals')

urlpatterns = [path('', include(router.urls))]
