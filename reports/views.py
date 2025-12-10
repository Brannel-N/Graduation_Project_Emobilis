from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import DisciplineReport, Student, TeacherProfile
from .forms import DisciplineReportForm
from django.contrib.auth.models import User, Group
from django.db.models import Q
from .admin_utils import approve_report_action, reject_report_action, delete_report_action

# Import status constants from DisciplineReport
STATUS_APPROVED = DisciplineReport.STATUS_APPROVED
from django.template.loader import render_to_string
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden
from django import forms
from django.db.models import Q
from django.views.decorators.http import require_http_methods

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'admission_number', 'stream', 'gender', 'parent', 'profile_picture']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['parent'].queryset = User.objects.filter(groups__name='Parent')
        self.fields['parent'].empty_label = "Select Parent (Optional)"

from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def create_student(request):
    # Only admins allowed to create students
    if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
        messages.error(request, 'You do not have permission to create students. Please contact an administrator.')
        return redirect('reports:students-list')

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)
            # Ensure the stream is properly set from the form
            if not student.stream and 'stream' in form.cleaned_data and form.cleaned_data['stream']:
                student.stream = form.cleaned_data['stream']
            student.save()
            messages.success(request, f'Successfully created student: {student.name}')
            return redirect('reports:students-list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm()
    
    return render(request, 'reports/create_student.html', {
        'form': form,
        'student': None
    })

@login_required
def students_list(request):
    # Admins see all students; teachers see their stream students; parents see their children
    if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
        students = Student.objects.all()
    elif request.user.groups.filter(name='Teacher').exists():
        # try to get teacher stream
        try:
            tp = TeacherProfile.objects.get(user=request.user)
            if tp.stream:
                students = Student.objects.filter(stream=tp.stream)
            else:
                students = Student.objects.none()
        except TeacherProfile.DoesNotExist:
            students = Student.objects.none()
    elif request.user.groups.filter(name='Parent').exists():
        students = Student.objects.filter(parent=request.user)
    else:
        students = Student.objects.none()
    
    # Check if user is in Admin group for template
    user_groups = request.user.groups.values_list('name', flat=True)
    
    return render(request, 'reports/students_list.html', {'students': students, 'user_groups': user_groups})

@login_required
def edit_student(request, pk):
    # Only admins allowed to edit
    if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
        messages.error(request, 'You do not have permission to edit students. Please contact an administrator.')
        return redirect('reports:students-list')
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            return redirect('reports:students-list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'reports/create_student.html', {'form': form, 'student': student})

@login_required
def delete_student(request, pk):
    # Only admins allowed to delete
    if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
        messages.error(request, 'You do not have permission to delete students. Please contact an administrator.')
        return redirect('reports:students-list')
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        return redirect('reports:students-list')
    return render(request, 'reports/student_confirm_delete.html', {'student': student})

@login_required
def create_report(request):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=== CREATE REPORT VIEW START ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"GET params: {request.GET}")
    logger.info(f"POST data: {request.POST}")
    
    # Only allow teachers to create reports
    if not request.user.groups.filter(name='Teacher').exists():
        error_msg = 'Only teachers are allowed to create reports.'
        logger.error(error_msg)
        messages.error(request, error_msg)
        return redirect('reports:report-list')
    
    # Get initial student if provided in URL
    student_id = request.GET.get('student') or request.GET.get('student_id')
    initial = {}
    selected_student = None
    
    logger.info(f"Student ID from URL: {student_id}")
    
    if student_id:
        try:
            selected_student = Student.objects.get(id=student_id)
            initial['student'] = selected_student.id  # Pass ID instead of object
            logger.info(f"Found student: {selected_student} (ID: {selected_student.id})")
            
            # If user is a teacher, verify the student is in their stream
            if request.user.groups.filter(name='Teacher').exists():
                try:
                    teacher_profile = TeacherProfile.objects.get(user=request.user)
                    if teacher_profile and teacher_profile.stream:
                        logger.info(f"[DEBUG] Teacher stream (raw): {repr(teacher_profile.stream)}")
                        logger.info(f"[DEBUG] Student stream (raw): {repr(selected_student.stream)}")
                        
                        # Normalize both stream names for comparison
                        teacher_stream = teacher_profile.stream.strip().lower()
                        student_stream = selected_student.stream.strip().lower() if selected_student.stream else ""
                        
                        logger.info(f"[DEBUG] Teacher stream (normalized): {repr(teacher_stream)}")
                        logger.info(f"[DEBUG] Student stream (normalized): {repr(student_stream)}")
                        logger.info(f"[DEBUG] Stream comparison: {student_stream} == {teacher_stream} -> {student_stream == teacher_stream}")
                        
                        # Compare the normalized stream names
                        if student_stream != teacher_stream:
                            error_msg = (
                                f'You can only create reports for students in your assigned stream.\n'
                                f'Your stream: {teacher_profile.stream} | Normalized: {teacher_stream}\n'
                                f'Student stream: {selected_student.stream} | Normalized: {student_stream}'
                            )
                            logger.error(f"[DEBUG] {error_msg}")
                            messages.error(request, error_msg)
                            return redirect('reports:report-list')
                        else:
                            logger.info("[DEBUG] Streams match, proceeding with report creation")
                except TeacherProfile.DoesNotExist:
                    error_msg = 'Teacher profile not found. Please contact administrator.'
                    logger.error(error_msg)
                    messages.error(request, error_msg)
                    return redirect('reports:report-list')
                    
        except (Student.DoesNotExist, ValueError) as e:
            error_msg = f'Student not found: {e}'
            logger.error(error_msg)
            messages.error(request, 'Student not found')
            return redirect('reports:report-list')
    
    logger.info(f"Initial form data: {initial}")
    
    # Initialize form with or without student
    form = DisciplineReportForm(
        user=request.user,
        data=request.POST or None,
        files=request.FILES or None,
        initial=initial
    )
    
    logger.info(f"Form is bound: {form.is_bound}")
    logger.info(f"Form errors: {form.errors}")
    
    # If we have a student, make sure the form has it set
    if selected_student and not form.is_bound:
        form.fields['student'].initial = selected_student.id
        logger.info(f"Set initial student ID: {selected_student.id}")
    
    if request.method == 'POST':
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            
            # Set the student from the form's cleaned_data if not already set
            if not report.student_id and 'student' in form.cleaned_data and form.cleaned_data['student']:
                report.student = form.cleaned_data['student']
                
            # For teachers, ensure they can only report for their stream
            if request.user.groups.filter(name='Teacher').exists():
                try:
                    teacher_profile = TeacherProfile.objects.get(user=request.user)
                    if teacher_profile.stream and report.student.stream != teacher_profile.stream:
                        messages.error(request, 'You can only create reports for students in your assigned stream.')
                        return redirect('reports:report-list')
                except TeacherProfile.DoesNotExist:
                    messages.error(request, 'Teacher profile not found. Please contact administrator.')
                    return redirect('reports:report-list')
            
            # Ensure student is set before saving
            if not report.student_id:
                if student_id:  # Use the student_id from URL if available
                    try:
                        report.student = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        messages.error(request, 'Student not found')
                        return redirect('reports:report-list')
                else:  # If no student is selected and no student_id in URL
                    messages.error(request, 'Please select a student')
                    return redirect('reports:report-create')
            
            report.save()
            
            # Send email notification to parent if exists
            parent_user = report.student.parent
            if parent_user and parent_user.email:
                subject = f"Urgent: Behavior Alert for Your Child"
                context = {
                    'student': report.student,
                    'report': report,
                    'school_name': 'Your School Name',
                    'parent': parent_user,
                    'action_url': request.build_absolute_uri(report.get_absolute_url()),
                }
                html_message = render_to_string('email/report_notification.html', context)
                plain_message = f"Your child, {report.student.name}, was involved in {report.get_category_display()} on {report.created_at.strftime('%d %b %Y')}. Please log in to the portal for details."
                
                # Send email in background thread to prevent blocking
                from threading import Thread
                from django.core.mail import EmailMessage
                import logging
                
                def send_email_async():
                    try:
                        email = EmailMessage(
                            subject=subject,
                            body=html_message,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                            to=[parent_user.email],
                        )
                        email.content_subtype = "html"
                        email.send(fail_silently=True)
                    except Exception as e:
                        logging.error(f"Error sending email: {str(e)}")
                
                # Start the email sending in a separate thread
                Thread(target=send_email_async).start()
            
            messages.success(
                request,
                'Report created successfully!',
                extra_tags='alert alert-success'
            )
            return redirect('reports:report-detail', pk=report.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    
    # Get the students based on user type
    students = None
    if request.user.groups.filter(name='Teacher').exists():
        try:
            teacher_profile = TeacherProfile.objects.get(user=request.user)
            if teacher_profile and teacher_profile.stream:
                # Get all students in the teacher's stream
                students = Student.objects.filter(stream=teacher_profile.stream).order_by('name')
                if not students.exists():
                    messages.info(request, f'No students found in your assigned stream: {teacher_profile.get_stream_display()}')
            else:
                messages.warning(request, 'No stream assigned to your teacher profile. Please contact administrator.')
        except TeacherProfile.DoesNotExist:
            messages.error(request, 'Teacher profile not found. Please contact administrator.')
    elif request.user.groups.filter(name='Parent').exists():
        students = Student.objects.filter(parent=request.user).order_by('name')
        if not students.exists():
            messages.info(request, 'No students are assigned to your parent account.')
    else:  # Admin or other users
        students = Student.objects.all().order_by('name')
        if not students.exists():
            messages.info(request, 'No students found in the system.')

    # For GET requests or if there was an error in POST
    context = {
        'form': form,
        'selected_student': selected_student,
        'students': students or []
    }
    
    # If we have a student, make sure it's in the context
    if hasattr(form, 'student') and form.student:
        context['student'] = form.student
    
    return render(request, 'reports/create_report.html', context)

@login_required
def report_list(request):
    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
    student_id = request.GET.get('student_id')
    parent_id = request.GET.get('parent_id')
    
    if is_admin:
        # Show all reports to admin users
        reports = DisciplineReport.objects.all()
    elif hasattr(user, 'parentprofile'):
        # For parents, only show approved reports for their children
        reports = DisciplineReport.objects.filter(
            student__parent=user,
            status=DisciplineReport.STATUS_APPROVED
        )
        
        # If a specific student_id is provided and belongs to this parent
        if student_id:
            reports = reports.filter(student_id=student_id, student__parent=user)
            
    elif hasattr(user, 'teacherprofile'):
        # Teachers only see reports they created
        reports = DisciplineReport.objects.filter(reported_by=user)
    else:
        reports = DisciplineReport.objects.none()
    
    # Handle parent_id parameter (for the 'View All' link from parent dashboard)
    if parent_id and str(user.id) == parent_id and hasattr(user, 'parentprofile'):
        reports = DisciplineReport.objects.filter(
            student__parent=user,
            status=DisciplineReport.STATUS_APPROVED
        )
    
    # Always order by created_at descending (newest first)
    reports = reports.select_related('student', 'reported_by', 'reviewed_by').order_by('-created_at')
    
    # If a specific student is selected, get that student for the template
    selected_student = None
    if student_id and (is_admin or hasattr(user, 'parentprofile')):
        try:
            if is_admin:
                selected_student = Student.objects.get(id=student_id)
            else:
                selected_student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            pass
    
    return render(request, 'reports/report_list.html', {
        'reports': reports,
        'is_admin': is_admin,
        'is_teacher': hasattr(user, 'teacherprofile'),
        'is_parent': hasattr(user, 'parentprofile'),
        'selected_student': selected_student,
        'parent_id': parent_id if str(user.id) == str(parent_id) else None
    })

@login_required
def report_detail(request, pk):
    report = get_object_or_404(DisciplineReport.objects.select_related(
        'student', 'reported_by', 'reviewed_by'
    ), pk=pk)
    
    user = request.user
    is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
    
    # Check if user has permission to view this report
    can_view = False
    
    # Admins can view all reports
    if is_admin:
        can_view = True
    # Teachers can view reports for students in their stream or reports they created
    elif hasattr(user, 'teacherprofile'):
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
            if teacher_profile.stream:
                can_view = (
                    report.reported_by == user or  # Teacher created the report
                    (
                        report.student.stream == teacher_profile.stream and
                        report.status != DisciplineReport.STATUS_REJECTED  # Don't show rejected reports
                    )
                )
            else:
                can_view = (report.reported_by == user)
        except TeacherProfile.DoesNotExist:
            can_view = False
    # Parents can view approved reports for their children
    elif hasattr(user, 'parentprofile'):
        can_view = (
            report.student.parent == user and 
            report.status == DisciplineReport.STATUS_APPROVED
        )
    
    if not can_view:
        messages.error(request, "You don't have permission to view this report.")
        return redirect('reports:report-list')
    
    # Get the status choices for the status dropdown (for admins)
    status_choices = []
    if is_admin:
        status_choices = DisciplineReport.STATUS_CHOICES
    
    return render(request, 'reports/report_detail.html', {
        'report': report,
        'is_admin': is_admin,
        'is_teacher': hasattr(user, 'teacherprofile'),
        'is_parent': hasattr(user, 'parentprofile'),
        'status_choices': status_choices,
        'STATUS_APPROVED': DisciplineReport.STATUS_APPROVED,
        'STATUS_PENDING': DisciplineReport.STATUS_PENDING,
        'STATUS_REJECTED': DisciplineReport.STATUS_REJECTED,
    })

# Status constants for better readability
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'

@login_required
@require_http_methods(['POST'])
def delete_report(request, pk):
    report = get_object_or_404(DisciplineReport, pk=pk)
    success, message = delete_report_action(request, report)
    
    if success:
        messages.success(request, message)
        return redirect('reports:report-list')
    else:
        messages.error(request, message)
        return redirect('reports:report-detail', pk=report.pk)

@login_required
def edit_report(request, pk):
    if not (request.user.has_perm('reports.can_manage_reports') or request.user.is_superuser):
        messages.error(request, 'You do not have permission to edit reports.')
        return redirect('reports:report-list')
    
    report = get_object_or_404(DisciplineReport, pk=pk)
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Admin').exists()
    
    if request.method == 'POST':
        # Update the report with the submitted data
        report.description = request.POST.get('description', report.description)
        report.category = request.POST.get('category', report.category)
        
        # Only update status if it's being changed by an admin
        if 'status' in request.POST and is_admin:
            report.status = request.POST['status']
            if report.status != STATUS_PENDING:
                report.reviewed_by = request.user
                report.reviewed_at = timezone.now()
        
        report.save()
        messages.success(request, 'Report has been updated successfully.')
        return redirect('reports:report-detail', pk=report.pk)
    
    # For GET request, show the edit form
    return render(request, 'reports/edit_report.html', {
        'report': report,
        'is_admin': is_admin,
        'STATUS_CHOICES': [
            (STATUS_PENDING, 'Pending'),
            (STATUS_APPROVED, 'Approved'),
            (STATUS_REJECTED, 'Rejected'),
        ]
    })

@login_required
@require_http_methods(['POST'])
def approve_report(request, pk):
    if not (request.user.has_perm('reports.can_manage_reports') or request.user.is_superuser):
        messages.error(request, 'You do not have permission to approve reports.')
        return redirect('reports:report-list')
        
    report = get_object_or_404(DisciplineReport, pk=pk)
    if report.status != DisciplineReport.STATUS_PENDING:
        messages.warning(request, 'This report has already been processed.')
        return redirect('reports:report-detail', pk=report.pk)
    
    success, message = approve_report_action(request, report)
    if success:
        messages.success(request, message)
    else:
        messages.warning(request, message)
        
    return redirect('reports:report-detail', pk=report.pk)

@login_required
@require_http_methods(['POST'])
def reject_report(request, pk):
    if not (request.user.has_perm('reports.can_manage_reports') or request.user.is_superuser):
        messages.error(request, 'You do not have permission to reject reports.')
        return redirect('reports:report-list')
        
    report = get_object_or_404(DisciplineReport, pk=pk)
    if report.status != DisciplineReport.STATUS_PENDING:
        messages.warning(request, 'This report has already been processed.')
        return redirect('reports:report-detail', pk=report.pk)
    
    review_notes = request.POST.get('review_notes', 'Rejected via web interface')
    success, message = reject_report_action(request, report, review_notes)
    if success:
        messages.success(request, message)
    else:
        messages.warning(request, message)
        
    return redirect('reports:report-detail', pk=report.pk)
