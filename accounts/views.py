from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
import json
import datetime

from .forms import LoginForm, UserCreateForm, UserUpdateForm, ProfilePictureForm
from .models import TeacherProfile, ParentProfile
from reports.models import DisciplineReport, Student

def home_view(request):
    return render(request, "home.html")

@require_GET
def get_reports_today_count(request):
    today = timezone.now().date()
    count = DisciplineReport.objects.filter(created_at__date=today).count()
    return JsonResponse({'count': count})

@login_required
@require_GET
def get_teacher_dashboard_data(request):
    if not request.user.groups.filter(name='Teacher').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=request.user)
        today = timezone.now().date()
        
        # Get teacher's stream
        stream = teacher_profile.stream
        if not stream:
            return JsonResponse({
                'error': 'No stream assigned to this teacher',
                'total_reports_today': 0,
                'total_students': 0,
                'recent_reports': []
            })
        
        # Get reports for teacher's stream
        reports_queryset = DisciplineReport.objects.filter(
            student__stream=stream
        ).select_related('student', 'reported_by')
        
        # Get today's reports
        today_reports = reports_queryset.filter(created_at__date=today).count()
        
        # Get total students in the stream
        total_students = Student.objects.filter(stream=stream).count()
        
        # Get recent reports (last 5)
        recent_reports = list(reports_queryset.order_by('-created_at')[:5].values(
            'id', 'student__name', 'category', 'status', 'created_at'
        ))
        
        # Format dates for JSON serialization
        for report in recent_reports:
            report['created_at'] = report['created_at'].strftime('%Y-%m-%d %H:%M')
        
        return JsonResponse({
            'total_reports_today': today_reports,
            'total_students': total_students,
            'recent_reports': recent_reports,
            'stream': stream
        })
        
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)

from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.views import LoginView as DjangoLoginView

class CustomLoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get(self, request, *args, **kwargs):
        # Ensure session is created before showing the login form
        if not request.session.session_key:
            request.session.create()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # Ensure session is created before processing the form
        if not self.request.session.session_key:
            self.request.session.create()
        return super().form_valid(form)

# Keep the old view for backward compatibility
login_view = CustomLoginView.as_view()

def redirect_after_login(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    
    # Superusers go to admin dashboard
    if user.is_superuser:
        return redirect('admin-dashboard')
    
    # Check user groups
    groups = user.groups.values_list('name', flat=True)
    if 'Teacher' in groups:
        return redirect('teacher-dashboard')
    if 'Parent' in groups:
        return redirect('parent-dashboard')
    
    # Default fallback for authenticated users without specific group
    return redirect('home')

@login_required
def teacher_dashboard(request):
    user = request.user
    today = timezone.now().date()
    
    # Check if user is admin
    is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
    
    # Base querysets
    reports_queryset = DisciplineReport.objects.all()
    students_queryset = Student.objects.all()
    teacher_profile = None
    
    # Check if user is a teacher
    is_teacher = user.groups.filter(name='Teacher').exists()
    
    if is_teacher and not is_admin:
        # Get or create teacher profile
        teacher_profile, created = TeacherProfile.objects.get_or_create(user=user)
        if created:
            messages.info(request, 'Welcome! Your teacher profile has been created. Please update your profile information.')
            
        if teacher_profile and teacher_profile.stream:
                # Get the teacher's stream and normalize it
                teacher_stream = teacher_profile.stream.strip()
                
                # Convert from '4 East' to 'Form 4 East' format if needed
                if not teacher_stream.startswith('Form '):
                    try:
                        # Extract the form number and direction (e.g., '4 East' -> 'Form 4 East')
                        parts = teacher_stream.split(' ', 1)
                        if len(parts) == 2 and parts[0].isdigit():
                            teacher_stream = f"Form {teacher_stream}"
                            # Update the teacher's stream to the correct format
                            teacher_profile.stream = teacher_stream
                            teacher_profile.save()
                    except (ValueError, IndexError):
                        pass
                
                try:
                    # Only show reports created by this teacher for their stream
                    reports_queryset = reports_queryset.filter(
                        reported_by=user,
                        student__stream__iexact=teacher_stream
                    )
                    # Only show students from teacher's stream (case-insensitive match)
                    students_queryset = students_queryset.filter(
                        stream__iexact=teacher_stream
                    ).order_by('name')
                except TeacherProfile.DoesNotExist:
                    reports_queryset = DisciplineReport.objects.none()
                    students_queryset = Student.objects.none()
        else:
            reports_queryset = DisciplineReport.objects.none()
            students_queryset = Student.objects.none()
    
    # Get dashboard statistics
    if is_admin:
        # For admin, show all reports
        total_reports_today = reports_queryset.filter(
            created_at__date=today
        ).count()
        total_reports_count = reports_queryset.count()
    else:
        # For teachers, only show their reports
        total_reports_today = reports_queryset.filter(
            created_at__date=today,
            reported_by=user
        ).count()
        total_reports_count = reports_queryset.filter(
            reported_by=user
        ).count()
    
    # Pending reports count (only for admin or teacher's own pending reports)
    pending_reports_count = reports_queryset.filter(
        status='pending'
    ).count()
    
    my_students_count = students_queryset.count()
    
    # Get recent reports (max 5)
    recent_reports = reports_queryset.select_related('student').order_by('-created_at')[:5]
    
    # Get category distribution for the chart
    category_data = reports_queryset.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    categories = [item['category'] for item in category_data]
    cat_values = [item['count'] for item in category_data]
    
    # If teacher has no stream assigned, show a warning
    if is_teacher and teacher_profile and not teacher_profile.stream:
        messages.warning(request, 'No stream assigned to your teacher profile. Please contact administrator.')
    
    context = {
        'is_admin': is_admin,
        'total_reports_today': total_reports_today,
        'pending_reports_count': pending_reports_count,
        'my_students_count': my_students_count,
        'total_reports_count': total_reports_count,
        'recent_reports': recent_reports,
        'categories_json': json.dumps(categories),
        'cat_values_json': json.dumps(cat_values),
        'students': students_queryset,
        'teacher_profile': teacher_profile
    }
    return render(request, "accounts/teacher_dashboard.html", context)

@login_required
def parent_dashboard(request):
    # Get only approved reports for the parent's children
    approved_reports = DisciplineReport.objects.filter(
        student__parent=request.user,
        status='approved'
    ).select_related('student', 'reported_by').order_by('-created_at')
    
    context = {
        'approved_reports': approved_reports,
    }
    return render(request, "accounts/parent_dashboard.html", context)

@login_required
def admin_dashboard(request):
    # compute stats
    today = timezone.now().date()
    
    # For admins, always show all reports
    reports_queryset = DisciplineReport.objects.select_related('student', 'reported_by').all()
    
    # Get all users, students, and teachers
    total_users = User.objects.count()
    total_students = Student.objects.count()
    total_teachers = User.objects.filter(groups__name='Teacher').distinct().count()
    
    # Get reports for today
    total_reports_today = reports_queryset.filter(created_at__date=today).count()
    
    # Get category distribution
    category_counts = reports_queryset.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get top students with most reports
    top_students = Student.objects.annotate(
        reports_count=Count('disciplinereport')
    ).filter(reports_count__gt=0).order_by('-reports_count')[:5]
    
    # Get recent reports (last 10)
    recent_reports = list(reports_queryset.order_by('-created_at')[:10])
    
    # Get top teachers based on reports created
    top_teachers = reports_queryset.values(
        'reported_by__username',
        'reported_by__first_name',
        'reported_by__last_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Prepare data for charts
    categories = [c['category'] for c in category_counts] if category_counts else []
    cat_values = [c['count'] for c in category_counts] if category_counts else []
    student_labels = [s.name for s in top_students] if top_students else []
    student_values = [s.reports_count for s in top_students] if top_students else []
    teacher_labels = [f"{t['reported_by__first_name']} {t['reported_by__last_name']}" or t['reported_by__username'] for t in top_teachers] if top_teachers else []
    teacher_values = [t['count'] for t in top_teachers] if top_teachers else []

    # Prepare user statistics for the pie chart
    user_stats = {
        'students': total_students,
        'teachers': total_teachers,
        'other': total_users - total_students - total_teachers  # Other users (admins, etc.)
    }

    # Prepare data for the line chart (last 7 days)
    today = timezone.now().date()
    date_range = [today - timezone.timedelta(days=i) for i in range(6, -1, -1)]
    
    # Get daily reports count for the last 7 days
    daily_reports = []
    for date in date_range:
        next_day = date + timezone.timedelta(days=1)
        count = DisciplineReport.objects.filter(
            created_at__date__gte=date,
            created_at__date__lt=next_day
        ).count()
        daily_reports.append(count)

    context = {
        'total_reports_today': total_reports_today,
        'total_reports_count': reports_queryset.count(),  # Total reports count
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'user_stats': user_stats,
        'daily_reports': daily_reports,
        'date_range': [date.strftime('%a') for date in date_range],  # Short day names for x-axis
        'recent_reports': recent_reports,
        'categories': categories,
        'cat_values': cat_values,
        'student_labels': student_labels,
        'student_values': student_values,
        'teacher_labels': teacher_labels,
        'teacher_values': teacher_values,
    }
    # Use the admin base template with sidebar
    return render(request, "accounts/admin_dashboard_clean.html", context)


@login_required
def manage_users(request):
    if not request.user.is_superuser:
        return redirect('home')
    
    # Import models
    from accounts.models import TeacherProfile
    from reports.models import Student
    
    # Get all teachers with their profiles (using select_related for optimization)
    teachers = User.objects.filter(groups__name='Teacher').select_related('teacherprofile').order_by('username')
    
    # Prepare teacher data with profile information
    teachers_with_profiles = []
    for teacher in teachers:
        try:
            profile = teacher.teacherprofile  # Using select_related so this won't hit the database
            teachers_with_profiles.append({
                'user': teacher,
                'stream': profile.get_stream_display() if profile.stream else 'Not assigned',
                'stream_code': profile.stream or ''
            })
        except TeacherProfile.DoesNotExist:
            # Create a teacher profile if it doesn't exist
            profile = TeacherProfile.objects.create(user=teacher)
            teachers_with_profiles.append({
                'user': teacher,
                'stream': profile.get_stream_display() if profile.stream else 'Not assigned',
                'stream_code': profile.stream or ''
            })
    
    # Get other users
    parents = User.objects.filter(groups__name='Parent').order_by('username')
    
    # Get all admins (both in Admin group and superusers)
    admins = User.objects.filter(Q(groups__name='Admin') | Q(is_superuser=True)).distinct().order_by('username')
    
    # Get all students
    students = Student.objects.all().order_by('name')
    
    # Prepare context
    context = {
        'teachers': teachers,  # For backward compatibility
        'teachers_with_profiles': teachers_with_profiles,  # Main list for the template
        'parents': parents,
        'admins': admins,
        'students': students,
    }
    
    return render(request, 'admin/users_list.html', context)


@login_required
def create_user(request):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
        
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'Successfully created {user.username} as a {form.cleaned_data.get("role")}')
                return redirect('manage-users')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error creating user: {str(e)}', exc_info=True)
        else:
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreateForm()
    
    return render(request, 'admin/user_form.html', {
        'form': form,
        'title': 'Create User'
    })


@login_required
def edit_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully')
            return redirect('manage-users')
    else:
        # Initialize form with all fields
        initial_data = {}
        
        # Add role from user's groups
        user_groups = user.groups.values_list('name', flat=True)
        if user_groups:
            initial_data['role'] = user_groups[0].lower()
        
        # Add teacher profile data if exists
        if hasattr(user, 'teacherprofile'):
            initial_data['stream'] = user.teacherprofile.stream
            if user.teacherprofile.profile_picture:
                initial_data['profile_picture'] = user.teacherprofile.profile_picture
        
        # Add parent profile data if exists
        if hasattr(user, 'parentprofile'):
            initial_data['phone'] = user.parentprofile.phone
            if user.parentprofile.profile_picture:
                initial_data['profile_picture'] = user.parentprofile.profile_picture
        
        form = UserUpdateForm(instance=user, initial=initial_data)
    
    return render(request, 'admin/user_form.html', {
        'form': form, 
        'title': f'Edit {user.get_full_name() or user.username}',
        'is_edit': True
    })


@login_required
def delete_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('home')
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted')
        return redirect('manage-users')
    return render(request, 'admin/user_confirm_delete.html', {'user': user})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    # Allow users to upload/update their profile picture
    form = ProfilePictureForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            pic = form.cleaned_data.get('profile_picture')
            if pic:
                # Determine which profile model to use
                profile_saved = False
                # Try TeacherProfile
                try:
                    tp, created = TeacherProfile.objects.get_or_create(user=request.user)
                    tp.profile_picture = pic
                    tp.save()
                    profile_saved = True
                except Exception as e:
                    profile_saved = False

                # Try ParentProfile if not saved
                if not profile_saved:
                    try:
                        pp, created = ParentProfile.objects.get_or_create(user=request.user)
                        pp.profile_picture = pic
                        pp.save()
                        profile_saved = True
                    except Exception as e:
                        profile_saved = False

                if profile_saved:
                    messages.success(request, 'Updates successifully')
                    return redirect('profile')
                else:
                    messages.error(request, 'Could not update profile picture')
            else:
                messages.info(request, 'Please select a file to upload')
        else:
            # Form has errors, they will be displayed in template
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)

    # For GET, try to show existing image if available
    existing_url = None
    try:
        tp = TeacherProfile.objects.filter(user=request.user).first()
        if tp and tp.profile_picture:
            existing_url = tp.profile_picture.url
    except Exception:
        existing_url = None
    if not existing_url:
        try:
            pp = ParentProfile.objects.filter(user=request.user).first()
            if pp and pp.profile_picture:
                existing_url = pp.profile_picture.url
        except Exception:
            existing_url = None

    return render(request, 'accounts/profile.html', {'form': form, 'existing_url': existing_url})
