from django.core.management.base import BaseCommand
from tracker.models import Drug, Interaction, ReactionDefinition

class Command(BaseCommand):
    help = 'Diagnose the database counts'

    def handle(self, *args, **options):
        self.stdout.write(f"Drugs Count: {Drug.objects.count()}")
        self.stdout.write(f"Interactions Count: {Interaction.objects.count()}")
        self.stdout.write(f"Reaction Definitions Count: {ReactionDefinition.objects.count()}")
        
        if Interaction.objects.exists():
            first_inter = Interaction.objects.first()
            self.stdout.write(f"First interaction: {first_inter.drug_a} + {first_inter.drug_b} (Sev: {first_inter.severity_slider})")
            
        self.stdout.write("Diagnosis complete.")
