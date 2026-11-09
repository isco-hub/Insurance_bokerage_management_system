from django.urls import include, path
from rest_framework.routers import DefaultRouter

from finance.views import (
    CommissionViewSet,
    CreditDebitNoteViewSet,
    InvoiceViewSet,
    PaymentViewSet,
    PremiumViewSet,
    RemittanceViewSet,
)

router = DefaultRouter()
router.register('premiums', PremiumViewSet, basename='premiums')
router.register('invoices', InvoiceViewSet, basename='invoices')
router.register('payments', PaymentViewSet, basename='payments')
router.register('credit-debit-notes', CreditDebitNoteViewSet, basename='notes')
router.register('commissions', CommissionViewSet, basename='commissions')
router.register('remittances', RemittanceViewSet, basename='remittances')

urlpatterns = [path('', include(router.urls))]
