import csv
from django.core.management.base import BaseCommand
from management.models import Qrcode_data
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Upload QR data from a CSV file to Qrcode_data table'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the CSV file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        # Using get_or_create to avoid IntegrityErrors with duplicates
                        obj, created = Qrcode_data.objects.get_or_create(
                            qr_code_id=row['Code'],
                            defaults={'is_assigned': False}
                        )
                        if created:
                            count += 1
                    except IntegrityError:
                        self.stdout.write(self.style.WARNING(f"Skipping duplicate: {row['Code']}"))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully uploaded {count} new QR codes!'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found at: {file_path}'))