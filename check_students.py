import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

def check_teacher_and_students():
    from django.contrib.auth.models import User
    from reports.models import TeacherProfile, Student
    
    # Get Jared's user account
    try:
        jared = User.objects.get(username='Jared')
        print(f"\n=== Teacher Information ===")
        print(f"Username: {jared.username}")
        print(f"Full Name: {jared.get_full_name()}")
        
        # Get teacher profile
        try:
            teacher_profile = TeacherProfile.objects.get(user=jared)
            print(f"\n=== Teacher Profile ===")
            print(f"Assigned Stream: {teacher_profile.stream}")
            print(f"Stream Display: {teacher_profile.get_stream_display()}")
            
            # Get all students in the same stream
            if teacher_profile.stream:
                students = Student.objects.filter(stream=teacher_profile.stream).order_by('name')
                print(f"\n=== Students in stream '{teacher_profile.stream}' ===")
                if students.exists():
                    for student in students:
                        print(f"- {student.name} (ID: {student.id}): Stream: '{student.stream}' | Parent: {student.parent.username if student.parent else 'None'}")
                else:
                    print("No students found in this stream.")
                    
                    # Show all available streams
                    all_streams = Student.objects.exclude(stream__isnull=True).exclude(stream='').values_list('stream', flat=True).distinct()
                    print("\n=== Available streams in the system ===")
                    for stream in all_streams:
                        print(f"- '{stream}'")
            else:
                print("\nNo stream assigned to this teacher.")
                
        except TeacherProfile.DoesNotExist:
            print("\nNo teacher profile found for Jared.")
            
    except User.DoesNotExist:
        print("\nUser 'Jared' not found.")

if __name__ == "__main__":
    check_teacher_and_students()
