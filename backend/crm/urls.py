from django.urls import include, path
from rest_framework.routers import DefaultRouter

from crm.views import (
    ClientContactViewSet,
    ClientDirectorViewSet,
    ClientViewSet,
    InsuranceClassViewSet,
    InsurerBranchViewSet,
    InsurerContactViewSet,
    InsurerViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register('clients', ClientViewSet, basename='clients')
router.register('client-contacts', ClientContactViewSet, basename='client-contacts')
router.register('client-directors', ClientDirectorViewSet, basename='client-directors')
router.register('insurers', InsurerViewSet, basename='insurers')
router.register('insurer-contacts', InsurerContactViewSet, basename='insurer-contacts')
router.register('insurer-branches', InsurerBranchViewSet, basename='insurer-branches')
router.register('insurance-classes', InsuranceClassViewSet, basename='insurance-classes')
router.register('products', ProductViewSet, basename='products')

urlpatterns = [path('', include(router.urls))]
