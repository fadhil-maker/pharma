from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fixes severity distribution in fast 100k chunks to prevent database lockups.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting chunked severity update..."))
        
        with connection.cursor() as cursor:
            # First, get the maximum ID in the table to know when to stop
            cursor.execute("SELECT MAX(id) FROM tracker_interaction")
            max_id = cursor.fetchone()[0]
            
            if not max_id:
                self.stdout.write(self.style.ERROR("Database is empty!"))
                return
                
            chunk_size = 100000
            current_start = 1
            
            while current_start <= max_id:
                current_end = current_start + chunk_size - 1
                
                # Update only a 100,000 chunk at a time
                cursor.execute(f"""
                    UPDATE tracker_interaction 
                    SET severity_slider = (id % 10) + 1 
                    WHERE id >= {current_start} AND id <= {current_end}
                """)
                
                pct = (min(current_end, max_id) / max_id) * 100
                self.stdout.write(self.style.SUCCESS(f"⚡ Updated severities up to ID {min(current_end, max_id):,} ({pct:.1f}% complete)..."))
                
                current_start += chunk_size
                
        self.stdout.write(self.style.SUCCESS("🎉 COMPLETED! All severities have been perfectly distributed!"))
