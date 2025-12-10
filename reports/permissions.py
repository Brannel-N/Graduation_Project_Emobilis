from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import DisciplineReport

def setup_report_permissions():
    # Get or create the content type for DisciplineReport
    content_type = ContentType.objects.get_for_model(DisciplineReport)
    
    # Define the permissions we want to create
    permissions = [
        ('can_manage_reports', 'Can manage discipline reports (view, approve, reject)'),
    ]
    
    # Create permissions if they don't exist
    for codename, name in permissions:
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )
        if created:
            print(f"[OK] Created permission: {name}")
        else:
            print(f"[OK] Permission already exists: {name}")
    
    # Assign permissions to Admin group
    try:
        admin_group = Group.objects.get(name='Admin')
        for codename, _ in permissions:
            permission = Permission.objects.get(codename=codename, content_type=content_type)
            admin_group.permissions.add(permission)
            print(f"[OK] Assigned '{permission.name}' to Admin group")
    except Group.DoesNotExist:
        print("[WARNING] Admin group does not exist. Please run setup_groups.py first.")
    except Permission.DoesNotExist:
        print("[WARNING] Could not find permission. Make sure migrations are applied.")

if __name__ == "__main__":
    setup_report_permissions()
