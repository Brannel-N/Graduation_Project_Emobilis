import os
import sys
import pathlib
# Ensure project root is on sys.path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()
from django.db import connection
with connection.cursor() as c:
    try:
        c.execute("ALTER TABLE accounts_teacherprofile ADD COLUMN stream varchar(50) NOT NULL DEFAULT ''")
        print('ALTER OK')
    except Exception as e:
        print('ALTER FAILED', e)
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','project.settings')
import django
django.setup()
from django.db import connection
with connection.cursor() as c:
    try:
        c.execute("ALTER TABLE accounts_teacherprofile ADD COLUMN stream varchar(50) NOT NULL DEFAULT ''")
        print('ALTER OK')
    except Exception as e:
        print('ALTER FAILED', e)
