
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher-dashboard'),
    path('dashboard/parent/', views.parent_dashboard, name='parent-dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin-dashboard'),
    # Superuser user management
    path('admin/users/', views.manage_users, name='manage-users'),
    path('admin/users/create/', views.create_user, name='create-user'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit-user'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete-user'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # API endpoints
    path('api/reports/today/count/', views.get_reports_today_count, name='reports-today-count'),
    path('api/teacher/dashboard/', views.get_teacher_dashboard_data, name='teacher-dashboard-data'),
]
