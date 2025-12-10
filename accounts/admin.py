from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import TeacherProfile, ParentProfile
from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


# =========================
# INLINE TEACHER PROFILE
# =========================
class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    verbose_name_plural = 'Teacher Profile'
    fk_name = 'user'
    fields = ('employee_id', 'stream', 'profile_picture')
    extra = 0
    max_num = 1


# =========================
# CUSTOM USER ADMIN
# =========================
class TeacherUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    inlines = (TeacherProfileInline,)

    list_display = ('username', 'email', 'get_role', 'get_stream_display', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'teacherprofile__stream')
    list_select_related = ('teacherprofile',)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'teacherprofile__stream')

    # Prefetch TeacherProfile to ensure get_stream works
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacherprofile')

    # Stream column for list_display with sorting
    def get_stream_display(self, obj):
        try:
            return obj.teacherprofile.get_stream_display()
        except (TeacherProfile.DoesNotExist, AttributeError):
            return 'N/A'
    get_stream_display.short_description = 'Stream'
    get_stream_display.admin_order_field = 'teacherprofile__stream'
    
    # Keep the original get_stream for backward compatibility
    def get_stream(self, obj):
        try:
            return obj.teacherprofile.stream
        except (TeacherProfile.DoesNotExist, AttributeError):
            return 'N/A'

    # Role column for list_display
    def get_role(self, obj):
        groups = obj.groups.values_list('name', flat=True)
        return ', '.join(groups) if groups else 'None'
    get_role.short_description = 'Role'

    # Always show inline for existing users
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    # Include stream in add/edit forms
    def get_fieldsets(self, request, obj=None):
        if not obj:  # Adding a new user
            return (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'email', 'password1', 'password2', 'groups'),
                }),
                ('Teacher Information', {
                    'classes': ('collapse',),
                    'fields': ('stream',),
                    'description': 'Fill these fields if creating a teacher account',
                }),
            )
        # For existing users, use default fieldsets and add teacher fields
        fieldsets = super().get_fieldsets(request, obj)
        if obj.groups.filter(name='Teacher').exists():
            fieldsets += (
                ('Teacher Information', {
                    'fields': ('stream',),
                }),
            )
        return fieldsets

    # Add form field for stream
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add stream field to the form
        if 'stream' not in form.base_fields:
            from .models import TeacherProfile
            form.base_fields['stream'] = forms.ChoiceField(
                choices=TeacherProfile.STREAM_CHOICES,
                required=False,
                label='Stream',
                help_text='Select the stream this teacher will be responsible for'
            )
        return form
    
    # Save model and ensure TeacherProfile exists
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Handle stream field for new users
        if not change and 'stream' in form.cleaned_data and form.cleaned_data['stream']:
            TeacherProfile.objects.create(
                user=obj,
                stream=form.cleaned_data['stream']
            )
        # For existing users, update the stream if it's a teacher
        elif change and obj.groups.filter(name='Teacher').exists():
            teacher_profile, created = TeacherProfile.objects.get_or_create(user=obj)
            if 'stream' in form.cleaned_data:
                teacher_profile.stream = form.cleaned_data['stream']
                teacher_profile.save()


# =========================
# RE-REGISTER USER MODEL
# =========================
if User in admin.site._registry:
    admin.site.unregister(User)
admin.site.register(User, TeacherUserAdmin)


# =========================
# PARENT PROFILE ADMIN
# =========================
@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


# =========================
# TEACHER PROFILE ADMIN
# =========================
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'stream')
    list_filter = ('stream',)
    search_fields = ('user__username', 'employee_id')
