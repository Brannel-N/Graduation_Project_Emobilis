
from django.urls import path
from . import views

app_name = 'reports'  # This sets the application namespace

urlpatterns = [
    # Main reports list at /reports/
    path('', views.report_list, name='report-list'),
    
    # Student management
    path('students/', views.students_list, name='students-list'),
    path('student/new/', views.create_student, name='create-student'),
    path('student/<int:pk>/edit/', views.edit_student, name='edit-student'),
    path('student/<int:pk>/delete/', views.delete_student, name='delete-student'),
    
    # Report management
    path('create/', views.create_report, name='create-report'),  # Changed from 'report/new/'
    path('report/<int:pk>/', views.report_detail, name='report-detail'),
    path('report/<int:pk>/edit/', views.edit_report, name='edit-report'),
    path('report/<int:pk>/delete/', views.delete_report, name='delete-report'),
    path('report/<int:pk>/approve/', views.approve_report, name='approve-report'),
    path('report/<int:pk>/reject/', views.reject_report, name='reject-report'),
    
    # Legacy URL for backward compatibility
    path('report/new/', views.create_report, name='create-report-legacy'),
    path('report/', views.report_list, name='report-list-legacy'),
]
