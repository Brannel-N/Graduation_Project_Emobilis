from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reports.models import TeacherProfile

class Command(BaseCommand):
    help = 'Assign a stream to the admin user'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get the admin user
        admin_user = User.objects.get(username='admin')
        
        # Create or update the teacher profile
        teacher_profile, created = TeacherProfile.objects.get_or_create(
            user=admin_user,
            defaults={'stream': '1E'}  # Assign to Form 1 East by default
        )
        
        if not created:
            teacher_profile.stream = '1E'
            teacher_profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned stream to admin user: {admin_user.username}'))
