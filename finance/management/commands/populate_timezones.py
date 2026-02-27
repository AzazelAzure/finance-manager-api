# TODO: Actually make this work

# sample to fix
from myapp.models import Timezone
import zoneinfo

def populate_timezones():
    tz_names = sorted(zoneinfo.available_timezones())
    
    # Use bulk_create for O(1) database hit performance
    timezone_objects = [Timezone(name=tz) for tz in tz_names]
    
    # Use ignore_conflicts=True if you have a unique constraint on 'name'
    Timezone.objects.bulk_create(timezone_objects, ignore_conflicts=True)

populate_timezones()