"""
Setup script to create default groups: Teacher, Parent, Admin
Run this once to initialize the groups in your database.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import Group

# Create groups if they don't exist
groups = ['Teacher', 'Parent', 'Admin']

for group_name in groups:
    group, created = Group.objects.get_or_create(name=group_name)
    if created:
        print(f"✓ Created group: {group_name}")
    else:
        print(f"✓ Group already exists: {group_name}")

print("\nAll groups are ready!")
