from django.urls import include, path
from rest_framework.routers import DefaultRouter

from operations.views import (
    EndorsementViewSet,
    InsurerQuoteViewSet,
    MotorDetailViewSet,
    PolicyViewSet,
    QuotationViewSet,
    RenewalViewSet,
    RiskViewSet,
)

router = DefaultRouter()
router.register('risks', RiskViewSet, basename='risks')
router.register('motor-details', MotorDetailViewSet, basename='motor-details')
router.register('quotations', QuotationViewSet, basename='quotations')
router.register('insurer-quotes', InsurerQuoteViewSet, basename='insurer-quotes')
router.register('policies', PolicyViewSet, basename='policies')
router.register('endorsements', EndorsementViewSet, basename='endorsements')
router.register('renewals', RenewalViewSet, basename='renewals')

urlpatterns = [path('', include(router.urls))]
