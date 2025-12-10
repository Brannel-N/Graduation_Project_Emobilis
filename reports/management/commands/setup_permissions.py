from django.core.management.base import BaseCommand
from reports.permissions import setup_report_permissions

class Command(BaseCommand):
    help = 'Set up custom permissions for reports app'

    def handle(self, *args, **options):
        setup_report_permissions()
        self.stdout.write(self.style.SUCCESS('Successfully set up report permissions'))
