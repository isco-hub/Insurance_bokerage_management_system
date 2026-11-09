from django.urls import path

from reporting.views import (
    DashboardView,
    HealthView,
    ReportExportView,
    ReportsView,
    SearchView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('search/', SearchView.as_view(), name='search'),
    path('reports/<str:report>/', ReportsView.as_view(), name='reports'),
    path(
        'reports/<str:report>/export/',
        ReportExportView.as_view(),
        name='report-export',
    ),
    path('health/', HealthView.as_view(), name='health'),
]
