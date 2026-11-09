from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('crm.urls')),
    path('api/', include('operations.urls')),
    path('api/', include('finance.urls')),
    path('api/', include('claims.urls')),
    path('api/', include('workspace.urls')),
    path('api/', include('reporting.urls')),
]

urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
        name='media',
    )
]
