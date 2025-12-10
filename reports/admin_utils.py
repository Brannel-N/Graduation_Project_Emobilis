from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from .models import DisciplineReport

def approve_report_action(request, report):
    """Approve a discipline report and update related fields."""
    if report.status == DisciplineReport.STATUS_APPROVED:
        return False, 'Report is already approved.'
        
    report.status = DisciplineReport.STATUS_APPROVED
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    return True, 'Report has been approved successfully.'

def reject_report_action(request, report, review_notes=''):
    """Reject a discipline report and update related fields."""
    if report.status == DisciplineReport.STATUS_REJECTED:
        return False, 'Report is already rejected.'
        
    report.status = DisciplineReport.STATUS_REJECTED
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    if review_notes:
        report.review_notes = review_notes
    report.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])
    return True, 'Report has been rejected.'

def delete_report_action(request, report):
    """Delete a discipline report with permission check."""
    if not (request.user.has_perm('reports.can_manage_reports') or request.user.is_superuser):
        return False, 'You do not have permission to delete reports.'
    
    report.delete()
    return True, 'Report has been deleted.'

def get_report_actions():
    """Return a dictionary of available report actions for the admin interface."""
    return {
        'approve_selected': {
            'label': 'Approve selected reports',
            'function': approve_report_action,
            'permission': 'reports.can_manage_reports'
        },
        'reject_selected': {
            'label': 'Reject selected reports',
            'function': reject_report_action,
            'permission': 'reports.can_manage_reports'
        },
    }
