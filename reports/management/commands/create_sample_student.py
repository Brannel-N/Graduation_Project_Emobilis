from django.core.management.base import BaseCommand
from reports.models import Student
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a sample student for testing'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Create a test admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        
        # Create a sample student
        student, created = Student.objects.get_or_create(
            name='Test Student',
            admission_number='STD001',
            stream='1E',  # Using one of the stream choices
            gender='M',   # Using one of the gender choices
            defaults={
                'parent': admin_user  # Assigning the admin as parent for testing
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created student with ID: {student.id}'))
            self.stdout.write(self.style.SUCCESS(f'You can now edit the student at: http://127.0.0.1:8000/reports/student/{student.id}/edit/'))
        else:
            self.stdout.write(self.style.SUCCESS('Sample student already exists'))
