from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reports.models import TeacherProfile

class Command(BaseCommand):
    help = 'Check a teacher\'s assigned stream'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the teacher')

    def handle(self, *args, **options):
        username = options['username']
        User = get_user_model()
        
        try:
            teacher = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'Found user: {teacher.username}'))
            
            if not hasattr(teacher, 'teacher_profile'):
                self.stdout.write(self.style.ERROR('No teacher profile found for this user'))
                return
                
            profile = teacher.teacher_profile
            self.stdout.write(f'Teacher Profile: {profile}')
            self.stdout.write(f'Stream: {profile.stream}')
            self.stdout.write(f'Stream type: {type(profile.stream)}')
            
            # Check if the stream is in the valid choices
            from reports.models import STREAM_CHOICES
            valid_streams = [choice[0] for choice in STREAM_CHOICES]
            self.stdout.write('\nValid stream choices:')
            for choice in STREAM_CHOICES:
                self.stdout.write(f'- {choice[0]}')
                
            if profile.stream and profile.stream not in valid_streams:
                self.stdout.write(self.style.WARNING('WARNING: The assigned stream is not in the valid choices!'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
