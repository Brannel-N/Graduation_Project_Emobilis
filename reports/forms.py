from django import forms
from .models import DisciplineReport, Student, TeacherProfile

class DisciplineReportForm(forms.ModelForm):
    class Meta:
        model = DisciplineReport
        fields = ['student', 'category', 'description', 'evidence']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, user, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== FORM INIT START ===")
        
        initial = kwargs.get('initial', {})
        self.user = user
        self.student_id = initial.get('student') or initial.get('student_id')
        self.student = None
        self.teacher_profile = None
        
        # Call super().__init__() first to initialize self.fields
        super().__init__(*args, **kwargs)
        
        # Make student field not required by default
        self.fields['student'].required = False
        
        # Get teacher profile if user is a teacher
        if self.user.groups.filter(name='Teacher').exists():
            try:
                self.teacher_profile = TeacherProfile.objects.get(user=self.user)
                if not self.teacher_profile.stream:
                    logger.warning(f"Teacher {self.user.username} has no stream assigned")
                    self.fields['student'].queryset = Student.objects.none()
                    return
                
                # Normalize the stream name if needed
                teacher_stream = self.teacher_profile.stream.strip()
                if not teacher_stream.startswith('Form '):
                    try:
                        # Extract the form number and direction (e.g., '4 East' -> 'Form 4 East')
                        parts = teacher_stream.split(' ', 1)
                        if len(parts) == 2 and parts[0].isdigit():
                            teacher_stream = f"Form {teacher_stream}"
                            # Update the teacher's stream to the correct format
                            self.teacher_profile.stream = teacher_stream
                            self.teacher_profile.save()
                            logger.info(f"Updated teacher stream format to: {teacher_stream}")
                    except (ValueError, IndexError) as e:
                        logger.error(f"Error normalizing stream name: {e}")
                        
                # Set the student queryset to only show students in the teacher's stream
                if self.teacher_profile.stream:
                    self.fields['student'].queryset = Student.objects.filter(
                        stream=self.teacher_profile.stream
                    ).order_by('name')
                    
            except TeacherProfile.DoesNotExist:
                logger.error(f"Teacher profile not found for user {self.user.username}")
                self.fields['student'].queryset = Student.objects.none()
                self.fields['student'].help_text = 'Teacher profile not found. Please contact administrator.'
                return
        elif self.user.groups.filter(name='Parent').exists():
            children = self.user.children.all()
            logger.info(f"Parent user. Found {children.count()} children.")
            self.fields['student'].queryset = children.order_by('name')
        else:
            # For admins or other users, show all students
            all_students = Student.objects.all()
            logger.info(f"Admin/other user. Showing all {all_students.count()} students.")
            self.fields['student'].queryset = all_students.order_by('name')
        
        # If we have a student_id, try to get the student object
        if self.student_id:
            try:
                self.student = Student.objects.get(id=self.student_id)
                # If teacher, verify student is in their stream
                if self.teacher_profile and self.student.stream and self.teacher_profile.stream:
                    teacher_stream = self.teacher_profile.stream.strip().lower()
                    student_stream = self.student.stream.strip().lower()
                    if student_stream != teacher_stream:
                        logger.warning(f"Access denied: Student {self.student} not in teacher's stream")
                        self.fields['student'].queryset = Student.objects.none()
                        self.fields['student'].help_text = 'You can only create reports for students in your assigned stream.'
                        return
                
                # Set the student field as a hidden input with the pre-selected student
                self.fields['student'].widget = forms.HiddenInput()
                self.fields['student'].initial = self.student.id
                self.fields['student'].required = False
                logger.info(f"Pre-selected student: {self.student}")
                
            except (Student.DoesNotExist, ValueError) as e:
                logger.error(f"Student not found: {e}")
                self.student_id = None
        
        # Make required fields explicit (student is not in this list)
        for field_name in ['category', 'description']:
            self.fields[field_name].required = True
            
        # Make evidence field optional
        self.fields['evidence'].required = False
        
        logger.info("=== FORM INIT END ===")
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Additional validation for teacher's stream
        if self.teacher_profile and 'student' in cleaned_data:
            student = cleaned_data.get('student')
            if student and student.stream and self.teacher_profile.stream:
                # Normalize both stream names for comparison
                teacher_stream = self.teacher_profile.stream.strip().lower()
                student_stream = student.stream.strip().lower()
                
                if student_stream != teacher_stream:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Security violation: Teacher {self.user} tried to create report for student {student} not in their stream")
                    raise forms.ValidationError("You can only create reports for students in your assigned stream.")
        
        return cleaned_data
