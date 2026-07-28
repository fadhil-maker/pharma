from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition, Drug

class Command(BaseCommand):
    help = 'Wipes the synthetic database completely and seeds the Drug model with real base APIs.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("WIPING ENTIRE SYNTHETIC DATABASE..."))
        
        # 1. Wipe everything
        Interaction.objects.all().delete()
        ReactionDefinition.objects.all().delete()
        Drug.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS("Database wiped completely! 0 rows remain."))

        # 2. Seed initial pure Drug selector
        self.stdout.write("Seeding Drug selector with top real APIs...")
        
        top_200 = [
            "atorvastatin", "levothyroxine", "lisinopril", "metformin", "amlodipine", "metoprolol", "albuterol", "omeprazole", "losartan", "gabapentin",
            "hydrochlorothiazide", "sertraline", "simvastatin", "montelukast", "pantoprazole", "acetaminophen", "escitalopram", "fluoxetine", "amoxicillin", "bupropion",
            "trazodone", "ibuprofen", "rosuvastatin", "pravastatin", "citalopram", "tamsulosin", "carvedilol", "potassium", "meloxicam", "clopidogrel",
            "tramadol", "alprazolam", "duloxetine", "venlafaxine", "ranitidine", "cyclobenzaprine", "glipizide", "diclofenac", "amphetamine", "lorazepam",
            "clonazepam", "cetirizine", "oxycodone", "allopurinol", "venlafaxine", "naproxen", "paroxetine", "vitamin d", "spironolactone", "fenofibrate",
            "losartan", "methylprednisolone", "amitriptyline", "diltiazem", "budesonide", "furosemide", "cefalexin", "quetiapine", "ondansetron", "clonidine",
            "fluticasone", "ezetimibe", "diazepam", "latanoprost", "sitagliptin", "pregabalin", "azithromycin", "insulin", "topiramate", "valproate",
            "lamotrigine", "mirtazapine", "donepezil", "levetiracetam", "ropinirole", "risperidone", "aripiprazole", "memantine", "baclofen", "methotrexate",
            "hydroxychloroquine", "sulfasalazine", "prednisone", "doxycycline", "ciprofloxacin", "levofloxacin", "clindamycin", "cephalexin", "fluconazole", "valacyclovir",
            "acyclovir", "finasteride", "sildenafil", "tadalafil", "vardenafil", "nitroglycerin", "isosorbide", "digoxin", "amiodarone", "warfarin"
        ]
        
        # Deduplicate and sort
        top_200 = sorted(list(set(top_200)))
        
        Drug.objects.bulk_create([Drug(name=d) for d in top_200])
        
        self.stdout.write(self.style.SUCCESS(f"Pre-seeded {len(top_200)} drugs into the selector!"))
        self.stdout.write(self.style.SUCCESS("Production Architecture Ready! The Gemini engine will now handle new pairings dynamically."))
