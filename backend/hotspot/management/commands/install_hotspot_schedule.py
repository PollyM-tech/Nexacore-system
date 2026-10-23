from django.core.management.base import BaseCommand
from django_q.models import Schedule
from django.utils import timezone


class Command(BaseCommand):
    help = 'Explicitly install the every-minute voucher enforcement and disconnect retry worker.'
    def handle(self, *args, **options):
        Schedule.objects.update_or_create(func='hotspot.tasks.network_access_maintenance', defaults={
            'name': 'Hotspot expiry and RADIUS disconnect retries', 'schedule_type': 'I', 'minutes': 1,
            'repeats': -1, 'next_run': timezone.now()})
        self.stdout.write('Network access maintenance schedule installed (every minute).')
