from django.urls import include, path
from rest_framework.routers import DefaultRouter

from claims.views import ClaimViewSet

router = DefaultRouter()
router.register('claims', ClaimViewSet, basename='claims')

urlpatterns = [path('', include(router.urls))]
