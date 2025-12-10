from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'List all teachers and their assigned streams'

    def handle(self, *args, **options):
        User = get_user_model()
        teachers = User.objects.filter(teacher_profile__isnull=False)
        
        if not teachers.exists():
            self.stdout.write(self.style.WARNING('No teachers found in the database'))
            return
            
        self.stdout.write(self.style.SUCCESS('List of teachers and their streams:'))
        for teacher in teachers:
            stream = teacher.teacher_profile.get_stream_display() if teacher.teacher_profile.stream else 'No Stream'
            self.stdout.write(f'- {teacher.username}: {stream}')
