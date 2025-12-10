import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from reports.models import Student

def list_students():
    print("\n=== Students and Their Parents ===")
    students = Student.objects.all().select_related('parent')
    
    if not students.exists():
        print("No students found in the database.")
        return
    
    for student in students:
        parent_username = student.parent.username if student.parent else "None"
        print(f"- {student.name} (ID: {student.id}): Parent: {parent_username}")

if __name__ == "__main__":
    list_students()
