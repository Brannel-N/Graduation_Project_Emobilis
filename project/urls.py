
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from accounts import views as accounts_views
from django.conf import settings
from django.conf.urls.static import static
from .admin_site import admin_site as custom_admin_site

urlpatterns = [
    # Custom admin URL that only superusers can access
    path('admin/', custom_admin_site.urls),
    path('', accounts_views.home_view, name='home'),
    path('login/', accounts_views.login_view, name='login'),
    path('login', accounts_views.login_view, name='login-old'),  # Keep for backward compatibility
    path('redirect-after-login/', accounts_views.redirect_after_login, name='redirect-after-login'),
    # Redirect old admin URL to home to prevent unauthorized access
    path('django-admin/', lambda request: redirect('/')),
    path('admin/login/', lambda request: redirect('login')),
    path('accounts/', include('accounts.urls')),
    path('reports/', include('reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Override the default admin site
admin.site = custom_admin_site
admin.sites.site = custom_admin_site
admin.autodiscover()
