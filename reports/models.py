
from django.db import models
from django.contrib.auth.models import User

# Define stream choices at the module level
STREAM_CHOICES = [
    ('Form 1 East', 'Form 1 East'),
    ('Form 1 West', 'Form 1 West'),
    ('Form 1 North', 'Form 1 North'),
    ('Form 1 South', 'Form 1 South'),
    ('Form 2 East', 'Form 2 East'),
    ('Form 2 West', 'Form 2 West'),
    ('Form 2 North', 'Form 2 North'),
    ('Form 2 South', 'Form 2 South'),
    ('Form 3 East', 'Form 3 East'),
    ('Form 3 West', 'Form 3 West'),
    ('Form 3 North', 'Form 3 North'),
    ('Form 3 South', 'Form 3 South'),
    ('Form 4 East', 'Form 4 East'),
    ('Form 4 West', 'Form 4 West'),
    ('Form 4 North', 'Form 4 North'),
    ('Form 4 South', 'Form 4 South'),
]

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    stream = models.CharField(max_length=15, choices=STREAM_CHOICES, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_stream_display() if self.stream else 'No Stream'}"

class Student(models.Model):
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    admission_number = models.CharField(max_length=50, unique=True)
    stream = models.CharField(max_length=15, choices=STREAM_CHOICES, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    profile_picture = models.ImageField(upload_to='students/', null=True, blank=True)
    parent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        return f"{self.name} ({self.admission_number})"

class DisciplineReport(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    
    CATEGORY_CHOICES = [
        ('cheating', 'Cheating'),
        ('bullying', 'Bullying'),
        ('lateness', 'Lateness'),
        ('disruption', 'Class Disruption'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reported_cases')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    evidence = models.FileField(upload_to='evidence/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.get_category_display()} ({self.created_at.date()})"
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('reports:report-detail', kwargs={'pk': self.pk})
