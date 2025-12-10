


from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.db import transaction
from reports.models import Student
from .models import TeacherProfile, ParentProfile

# Role choices for quick assignment
ROLE_CHOICES = [
    ('', '--- Select a role ---'),
    ('teacher', 'Teacher'),
    ('parent', 'Parent'),
    ('admin', 'Admin'),
]


class CustomUserCreationForm(UserCreationForm):
    """A form for creating new users with role-based fields."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    role = forms.ChoiceField(
        choices=[
            ('teacher', 'Teacher'),
            ('parent', 'Parent'),
            ('admin', 'Admin')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Teacher-specific fields
    stream = forms.ChoiceField(
        required=False,
        label='Stream',
        help_text='Select the stream this teacher will be responsible for',
        choices=TeacherProfile.STREAM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Parent-specific fields
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set field classes
        for field_name, field in self.fields.items():
            if field_name not in ['role', 'stream']:  # Skip fields we've already configured
                field.widget.attrs['class'] = 'form-control'
    
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        if commit:
            user.save()
            
            if role == 'teacher':
                # Create teacher profile with profile picture
                profile_picture = self.cleaned_data.get('profile_picture')
                teacher_profile = TeacherProfile.objects.create(
                    user=user,
                    stream=self.cleaned_data.get('stream', '')
                )
                
                # Handle profile picture if provided
                if profile_picture:
                    teacher_profile.profile_picture = profile_picture
                    teacher_profile.save()
                
                # Add to Teacher group
                teacher_group, _ = Group.objects.get_or_create(name='Teacher')
                user.groups.add(teacher_group)
                
            elif role == 'parent':
                # Create parent profile with profile picture
                profile_picture = self.cleaned_data.get('profile_picture')
                parent_profile = ParentProfile.objects.create(
                    user=user,
                    phone=self.cleaned_data.get('phone', '')
                )
                
                # Handle profile picture if provided
                if profile_picture:
                    parent_profile.profile_picture = profile_picture
                    parent_profile.save()
                
                # Add to Parent group
                parent_group, _ = Group.objects.get_or_create(name='Parent')
                user.groups.add(parent_group)
                
            elif role == 'admin':
                # Add to Admin group
                admin_group, _ = Group.objects.get_or_create(name='Admin')
                user.groups.add(admin_group)
                user.is_staff = True
                user.save()
        
        return user


class CustomUserChangeForm(UserChangeForm):
    """A form for updating users with role-based fields."""
    role = forms.ChoiceField(
        choices=[
            ('teacher', 'Teacher'),
            ('parent', 'Parent'),
            ('admin', 'Admin')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Teacher-specific fields
    stream = forms.ChoiceField(
        required=False,
        label='Stream',
        choices=TeacherProfile.STREAM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Parent-specific fields
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial role from user's groups
        if self.instance and self.instance.pk:
            user_groups = self.instance.groups.values_list('name', flat=True)
            if user_groups:
                self.fields['role'].initial = user_groups[0].lower()
            
            # Set initial values for profile-specific fields
            if hasattr(self.instance, 'teacherprofile'):
                self.fields['stream'].initial = self.instance.teacherprofile.stream
            if hasattr(self.instance, 'parentprofile'):
                self.fields['phone'].initial = self.instance.parentprofile.phone
        
        # Set field classes
        for field_name, field in self.fields.items():
            if field_name not in ['role', 'stream']:  # Skip fields we've already configured
                field.widget.attrs['class'] = 'form-control'
    
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        if commit:
            user.save()
            
            # Clear existing groups
            user.groups.clear()
            
            if role == 'teacher':
                # Update or create teacher profile
                teacher_profile, created = TeacherProfile.objects.get_or_create(user=user)
                teacher_profile.stream = self.cleaned_data.get('stream', '')
                teacher_profile.save()
                
                # Remove parent profile if it exists
                ParentProfile.objects.filter(user=user).delete()
                
                # Add to Teacher group
                teacher_group, _ = Group.objects.get_or_create(name='Teacher')
                user.groups.add(teacher_group)
                
            elif role == 'parent':
                # Update or create parent profile
                parent_profile, created = ParentProfile.objects.get_or_create(user=user)
                parent_profile.phone = self.cleaned_data.get('phone', '')
                parent_profile.save()
                
                # Remove teacher profile if it exists
                TeacherProfile.objects.filter(user=user).delete()
                
                # Add to Parent group
                parent_group, _ = Group.objects.get_or_create(name='Parent')
                user.groups.add(parent_group)
                
            elif role == 'admin':
                # Remove any profile if exists
                TeacherProfile.objects.filter(user=user).delete()
                ParentProfile.objects.filter(user=user).delete()
                
                # Add to Admin group and make staff
                admin_group, _ = Group.objects.get_or_create(name='Admin')
                user.groups.add(admin_group)
                user.is_staff = True
                user.save()
        
        return user


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, 
        required=True, 
        help_text="Assign a role to this user",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    stream = forms.ChoiceField(
        choices=TeacherProfile.STREAM_CHOICES,
        required=False,
        label='Stream',
        help_text='(For Teachers) Select the stream this teacher will be responsible for',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
            widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='(For Parents) Contact number'
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='(Optional) Upload a profile picture'
    )
    linked_students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        help_text='(For Parents) Link student(s) to this parent'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required attribute for role field
        self.fields['role'].required = True
        
        # Make sure password fields are included and styled
        if 'password1' in self.fields and 'password2' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Enter a strong password'
            })
            self.fields['password2'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Confirm your password'
            })
            self.fields['password1'].help_text = "<ul class='text-muted small'>" + "\n".join(
                ["<li>" + line + "</li>" for line in self.fields['password1'].help_text.split("\n") if line]
            ) + "</ul>"
            self.fields['password2'].help_text = "Enter the same password as before, for verification."
        
        # Add bootstrap classes to widgets
        for name, field in self.fields.items():
            if name not in ['password1', 'password2']:  # Skip password fields we've already configured
                if isinstance(field.widget, forms.SelectMultiple):
                    field.widget.attrs.setdefault('class', 'form-select')
                elif isinstance(field.widget, forms.Select):
                    field.widget.attrs.setdefault('class', 'form-select')
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs.setdefault('class', 'form-check-input')
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        if commit:
            # Set password if provided
            if 'password1' in self.cleaned_data and self.cleaned_data['password1']:
                user.set_password(self.cleaned_data['password1'])
            
            # Save the user first to get an ID
            user.save()
            
            # Handle role assignment
            if role:
                # Remove from all groups first
                user.groups.clear()
                
                if role == 'teacher':
                    group, _ = Group.objects.get_or_create(name='Teacher')
                    user.groups.add(group)
                    
                    # Create or update teacher profile
                    teacher_profile, created = TeacherProfile.objects.update_or_create(
                        user=user,
                        defaults={'stream': self.cleaned_data.get('stream', '')}
                    )
                    
                elif role == 'parent':
                    # Add to Parent group
                    group, _ = Group.objects.get_or_create(name='Parent')
                    user.groups.add(group)
                    
                    # Create or update parent profile
                    parent_profile, created = ParentProfile.objects.update_or_create(
                        user=user,
                        defaults={'phone': self.cleaned_data.get('phone', '')}
                    )
                    
                    # Link students if any
                    if 'linked_students' in self.cleaned_data and self.cleaned_data['linked_students']:
                        parent_profile.students.set(self.cleaned_data['linked_students'])
                        
                elif role == 'admin':
                    # Add to Admin group and make staff
                    group, _ = Group.objects.get_or_create(name='Admin')
                    user.groups.add(group)
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
            
            # Handle profile picture if provided
            if 'profile_picture' in self.cleaned_data and self.cleaned_data['profile_picture']:
                if role == 'teacher' and hasattr(user, 'teacherprofile'):
                    user.teacherprofile.profile_picture = self.cleaned_data['profile_picture']
                    user.teacherprofile.save()
                elif role == 'parent' and hasattr(user, 'parentprofile'):
                    user.parentprofile.profile_picture = self.cleaned_data['profile_picture']
                    user.parentprofile.save()
        
        return user


class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        help_text="Leave blank to keep current password"
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, 
        required=True, 
        help_text="User role",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    stream = forms.ChoiceField(
        choices=TeacherProfile.STREAM_CHOICES,
        required=False,
        label='Stream',
        help_text='(For Teachers) Select the stream this teacher is responsible for',
        widget=forms.Select(attrs={'class': 'form-select role-specific-field', 'id': 'id_stream'})
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control role-specific-field', 'id': 'id_phone'}),
        help_text='(For Parents) Contact number'
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='(Optional) Upload a profile picture'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'role', 'stream', 'phone', 'password', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make sure all fields are included in self.fields
        for field_name in self.Meta.fields:
            if field_name not in self.fields:
                if field_name == 'stream':
                    self.fields[field_name] = forms.ChoiceField(
                        choices=TeacherProfile.STREAM_CHOICES,
                        required=False,
                        label='Stream',
                        help_text='(For Teachers) Select the stream this teacher is responsible for',
                        widget=forms.Select(attrs={'class': 'form-select role-specific-field', 'id': 'id_stream'})
                    )
                elif field_name == 'phone':
                    self.fields[field_name] = forms.CharField(
                        required=False,
                        max_length=20,
                        widget=forms.TextInput(attrs={'class': 'form-control role-specific-field', 'id': 'id_phone'}),
                        help_text='(For Parents) Contact number'
                    )
        
        # Set initial role from user's groups
        if self.instance and self.instance.pk:
            user_groups = self.instance.groups.values_list('name', flat=True)
            if user_groups:
                role = user_groups[0].lower()
                self.fields['role'].initial = role
            
            # Set initial values for profile-specific fields
            if hasattr(self.instance, 'teacherprofile'):
                teacher_profile = self.instance.teacherprofile
                self.fields['stream'].initial = teacher_profile.stream
                if teacher_profile.profile_picture:
                    self.fields['profile_picture'].initial = teacher_profile.profile_picture
            if hasattr(self.instance, 'parentprofile'):
                self.fields['phone'].initial = self.instance.parentprofile.phone
                if self.instance.parentprofile.profile_picture:
                    self.fields['profile_picture'].initial = self.instance.parentprofile.profile_picture

        # Add CSS classes to form fields
        for field_name, field in self.fields.items():
            if field_name not in ['role', 'stream', 'is_active']:  # Skip fields we've already configured
                if isinstance(field.widget, forms.SelectMultiple):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field, forms.BooleanField):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        stream = cleaned_data.get('stream')
        
        # Handle password change if provided
        if 'password' in cleaned_data and cleaned_data['password']:
            if len(cleaned_data['password']) < 8:
                self.add_error('password', 'Password must be at least 8 characters long')
        
        # Additional validation for teacher role
        if role == 'teacher':
            if not stream:
                self.add_error('stream', 'Stream is required for teacher users')
            else:
                # Check if this stream is already assigned to another teacher
                existing_teacher = TeacherProfile.objects.filter(stream=stream).exclude(user=self.instance).first()
                if existing_teacher:
                    self.add_error('stream', f'This stream is already assigned to {existing_teacher.user.get_full_name() or existing_teacher.user.username}')
        
        # Additional validation for parent role
        if role == 'parent' and 'phone' in cleaned_data and cleaned_data['phone']:
            phone = cleaned_data['phone']
            if not phone.isdigit() or len(phone) < 10:
                self.add_error('phone', 'Please enter a valid phone number (at least 10 digits)')
        
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Handle password change if provided
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            
            # Handle role assignment
            role = self.cleaned_data.get('role')
            profile_picture = self.cleaned_data.get('profile_picture')
            
            if role:
                # Remove from all groups first
                user.groups.clear()
                
                if role == 'teacher':
                    # Add to Teacher group
                    group, _ = Group.objects.get_or_create(name='Teacher')
                    user.groups.add(group)
                    
                    # Create or update teacher profile
                    stream = self.cleaned_data.get('stream', '')
                    teacher_profile, created = TeacherProfile.objects.get_or_create(
                        user=user,
                        defaults={'stream': stream}
                    )
                    
                    if not created:
                        teacher_profile.stream = stream
                        teacher_profile.save()  # Save the stream update
                    
                    # Handle profile picture update
                    if profile_picture:
                        teacher_profile.profile_picture = profile_picture
                        teacher_profile.save()
                    
                    # Remove parent profile if exists
                    if hasattr(user, 'parentprofile'):
                        user.parentprofile.delete()
                    
                elif role == 'parent':
                    # Add to Parent group
                    group, _ = Group.objects.get_or_create(name='Parent')
                    user.groups.add(group)
                    
                    # Create or update parent profile
                    phone = self.cleaned_data.get('phone', '')
                    parent_profile, created = ParentProfile.objects.get_or_create(
                        user=user,
                        defaults={'phone': phone}
                    )
                    
                    if not created:
                        parent_profile.phone = phone
                        
                    # Handle profile picture update
                    if profile_picture:
                        parent_profile.profile_picture = profile_picture
                        parent_profile.save()
                    
                    # Remove teacher profile if exists
                    if hasattr(user, 'teacherprofile'):
                        user.teacherprofile.delete()
                        
                elif role == 'admin':
                    # Add to Admin group
                    group, _ = Group.objects.get_or_create(name='Admin')
                    user.groups.add(group)
                    user.is_staff = True
                    user.save()
            
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email or username')


class ProfilePictureForm(forms.Form):
    profile_picture = forms.ImageField(required=False)

    def clean_profile_picture(self):
        pic = self.cleaned_data.get('profile_picture')
        if pic:
            max_size = 15 * 1024 * 1024  # 15 MB
            if pic.size > max_size:
                raise forms.ValidationError('File too large (max 15MB).')
        return pic
