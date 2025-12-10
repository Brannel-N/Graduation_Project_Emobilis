
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from .models import Student, DisciplineReport, TeacherProfile
from .admin_utils import approve_report_action, reject_report_action, get_report_actions

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'admission_number', 'get_stream_display', 'gender', 'parent_name', 'profile_picture_preview')
    list_filter = ('stream', 'gender')
    search_fields = ('name', 'admission_number', 'parent__first_name', 'parent__last_name')
    list_per_page = 20
    
    def parent_name(self, obj):
        return f"{obj.parent.get_full_name()}" if obj.parent else "-"
    parent_name.short_description = 'Parent'
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.profile_picture.url)
        return "No Image"
    profile_picture_preview.short_description = 'Profile Picture'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('name', 'admission_number', 'stream', 'gender', 'profile_picture')
        }),
        ('Parent Information', {
            'fields': ('parent',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DisciplineReport)
class DisciplineReportAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_category_display', 'status', 'reported_by', 'created_at', 'review_status')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('student__name', 'description', 'reported_by__username', 'review_notes')
    readonly_fields = ('created_at', 'reviewed_at', 'reviewed_by')
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['approve_selected_reports', 'reject_selected_reports']
    
    def has_add_permission(self, request):
        # Disable adding new reports for all users including admins
        return False
        
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # This is a new report
            obj.reported_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:report_id>/approve/',
                self.admin_site.admin_view(self.approve_report),
                name='approve-report',
            ),
            path(
                '<int:report_id>/reject/',
                self.admin_site.admin_view(self.reject_report),
                name='reject-report',
            ),
        ]
        return custom_urls + urls
    
    fieldsets = (
        ('Report Details', {
            'fields': ('student', 'category', 'description', 'evidence')
        }),
        ('Status Information', {
            'fields': ('status', 'review_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('reported_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def review_status(self, obj):
        if obj.status == 'approved':
            return format_html('<span style="color: green;">✓ Approved</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="color: red;">✗ Rejected</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    review_status.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # If this is a new report
            obj.reported_by = request.user
        
        # If status is being changed, update reviewed_by and reviewed_at
        if 'status' in form.changed_data and obj.status in ['approved', 'rejected']:
            if obj.status == 'approved':
                success, _ = approve_report_action(request, obj)
            else:
                success, _ = reject_report_action(request, obj)
        
        super().save_model(request, obj, form, change)
    
    def approve_selected_reports(self, request, queryset):
        success_count = 0
        for report in queryset:
            success, _ = approve_report_action(request, report)
            if success:
                success_count += 1
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully approved {success_count} report(s).",
                messages.SUCCESS
            )
    approve_selected_reports.short_description = "Approve selected reports"
    
    def reject_selected_reports(self, request, queryset):
        success_count = 0
        for report in queryset:
            success, _ = reject_report_action(request, report, "Rejected via admin action")
            if success:
                success_count += 1
        
        if success_count > 0:
            self.message_user(
                request,
                f"Successfully rejected {success_count} report(s).",
                messages.SUCCESS
            )
    reject_selected_reports.short_description = "Reject selected reports"
    
    def approve_report(self, request, report_id):
        report = self.get_object(request, report_id)
        if not report:
            self.message_user(request, 'Report not found.', level=messages.ERROR)
            return HttpResponseRedirect("../")
            
        success, message = approve_report_action(request, report)
        if success:
            self.message_user(request, message, level=messages.SUCCESS)
        else:
            self.message_user(request, message, level=messages.WARNING)
            
        return HttpResponseRedirect("../")
    
    def reject_report(self, request, report_id):
        report = self.get_object(request, report_id)
        if not report:
            self.message_user(request, 'Report not found.', level=messages.ERROR)
            return HttpResponseRedirect("../")
            
        success, message = reject_report_action(request, report, "Rejected via admin action")
        if success:
            self.message_user(request, message, level=messages.SUCCESS)
        else:
            self.message_user(request, message, level=messages.WARNING)
            
        return HttpResponseRedirect("../")

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_stream_display')
    list_filter = ('stream',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
