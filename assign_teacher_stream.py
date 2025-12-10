import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

def assign_teacher_stream():
    from django.contrib.auth.models import User, Group
    from reports.models import TeacherProfile, Student
    
    # Get Jared's user account
    try:
        jared = User.objects.get(username='Jared')
        
        # Make sure Jared is in the Teacher group
        teacher_group, created = Group.objects.get_or_create(name='Teacher')
        if teacher_group not in jared.groups.all():
            jared.groups.add(teacher_group)
            print("Added Jared to the Teacher group")
        
        # Create or update teacher profile
        teacher_profile, created = TeacherProfile.objects.get_or_create(user=jared)
        
        # Find the most common stream among Jared's students
        from django.db.models import Count
        jareds_students = Student.objects.filter(parent=jared)
        if jareds_students.exists():
            # Get the most common stream among Jared's students
            common_stream = jareds_students.values('stream').annotate(count=Count('stream')).order_by('-count').first()
            if common_stream and common_stream['stream']:
                teacher_profile.stream = common_stream['stream']
                teacher_profile.save()
                print(f"Assigned stream '{teacher_profile.stream}' to Jared's teacher profile")
            else:
                print("No valid stream found among Jared's students.")
                # Assign a default stream if needed
                teacher_profile.stream = '4E'  # Example: Assign to Form 4 East
                teacher_profile.save()
                print(f"Assigned default stream '{teacher_profile.stream}' to Jared's teacher profile")
        else:
            print("Jared doesn't have any students assigned.")
            # Assign a default stream
            teacher_profile.stream = '4E'  # Example: Assign to Form 4 East
            teacher_profile.save()
            print(f"Assigned default stream '{teacher_profile.stream}' to Jared's teacher profile")
            
        # Verify the assignment
        print("\n=== Verification ===")
        print(f"Teacher: {jared.username}")
        print(f"Assigned Stream: {teacher_profile.stream}")
        print(f"Students in this stream: {Student.objects.filter(stream=teacher_profile.stream).count()}")
        
    except User.DoesNotExist:
        print("User 'Jared' not found.")

if __name__ == "__main__":
    assign_teacher_stream()
