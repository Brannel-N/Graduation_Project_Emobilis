from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reports.models import TeacherProfile

class Command(BaseCommand):
    help = 'Assign a stream to a teacher'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the teacher')
        parser.add_argument('stream', type=str, help='Stream code (e.g., 1E, 2W, etc.)')

    def handle(self, *args, **options):
        User = get_user_model()
        
        try:
            teacher = User.objects.get(username=options['username'])
            if not hasattr(teacher, 'teacher_profile'):
                self.stdout.write(self.style.ERROR(f'User {options["username"]} is not a teacher'))
                return
                
            # Update the teacher's stream
            teacher.teacher_profile.stream = options['stream']
            teacher.teacher_profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully assigned stream {options["stream"]} to teacher {teacher.username}')
            )
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {options["username"]} does not exist'))
