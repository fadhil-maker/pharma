import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from tracker.models import Drug, Interaction, ReactionDefinition
from django.db.models import Q

def diagnose():
    print(f"Drugs Count: {Drug.objects.count()}")
    print(f"Interactions Count: {Interaction.objects.count()}")
    print(f"Reaction Definitions Count: {ReactionDefinition.objects.count()}")
    
    if Interaction.objects.exists():
        first_inter = Interaction.objects.first()
        print(f"First interaction: {first_inter.drug_a} + {first_inter.drug_b} (Sev: {first_inter.severity_slider})")
        
    print("Diagnosis complete.")

if __name__ == '__main__':
    diagnose()
