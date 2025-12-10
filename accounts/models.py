
from django.db import models
from django.contrib.auth.models import User

class TeacherProfile(models.Model):
    STREAM_CHOICES = [
        ('1 WEST', '1 WEST'), ('1 EAST', '1 EAST'),
        ('1 NORTH', '1 NORTH'), ('1 SOUTH', '1 SOUTH'),
        ('2 WEST', '2 WEST'), ('2 EAST', '2 EAST'),
        ('2 NORTH', '2 NORTH'), ('2 SOUTH', '2 SOUTH'),
        ('3 WEST', '3 WEST'), ('3 EAST', '3 EAST'),
        ('3 NORTH', '3 NORTH'), ('3 SOUTH', '3 SOUTH'),
        ('4 WEST', '4 WEST'), ('4 EAST', '4 EAST'),
        ('4 NORTH', '4 NORTH'), ('4 SOUTH', '4 SOUTH'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50, blank=True)
    stream = models.CharField(max_length=20, choices=STREAM_CHOICES, blank=True)
    profile_picture = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
