from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

class CustomAdminSite(admin.AdminSite):
    def admin_view(self, view, cacheable=False):
        view = super().admin_view(view, cacheable)
        
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return self.login(request)
            if not request.user.is_superuser:
                return redirect('home')  # Redirect non-admin users to home
            return view(request, *args, **kwargs)
            
        return wrapper

# Create an instance of the custom admin site
admin_site = CustomAdminSite()
