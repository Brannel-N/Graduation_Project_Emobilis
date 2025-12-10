import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

def list_all_streams():
    from reports.models import Student
    
    # Get all unique streams
    streams = Student.objects.exclude(stream__isnull=True).exclude(stream='').values_list('stream', flat=True).distinct()
    
    print("\n=== Available Streams in the System ===")
    if streams:
        for stream in streams:
            # Count students in each stream
            count = Student.objects.filter(stream=stream).count()
            print(f"- '{stream}': {count} students")
            
            # List students in this stream
            students = Student.objects.filter(stream=stream).order_by('name')
            for student in students:
                print(f"  - {student.name} (ID: {student.id}) | Parent: {student.parent.username if student.parent else 'None'}")
    else:
        print("No streams found in the system.")

if __name__ == "__main__":
    list_all_streams()
