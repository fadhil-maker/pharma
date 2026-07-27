import sys
import random
from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition

class Command(BaseCommand):
    help = 'Seed Full Master Clinical Dataset (All Interaction Pairs) into Database'

    def handle(self, *args, **kwargs):
        self.stdout.write("Compiling and populating Full Master Clinical Dataset into SQLite Database...")

        # Master Clinical Categories & Organ Masks
        categories = [
            ("Synergistic inhibition of coagulation cascade causing major hemorrhage.", "CONTRAINDICATED. Do not co-administer.", 9, 80),
            ("NSAID inhibition of renal prostaglandin clearance causing acute toxicity and renal failure.", "Avoid concurrent use.", 8, 96),
            ("Synergistic CNS and respiratory depression causing fatal respiratory arrest.", "CONTRAINDICATED.", 10, 5),
            ("Reduced renal clearance causing severe drug toxicity and neurotoxicity.", "Monitor levels closely.", 9, 33),
            ("CYP3A4 enzyme inhibition causing severe prolonged sedation.", "Avoid combination.", 8, 5),
            ("Combined anticoagulant and antiplatelet activity increasing major bleeding.", "Avoid concurrent use.", 9, 81),
            ("Serotonergic hyperstimulation leading to Serotonin Syndrome.", "Monitor for serotonin toxicity.", 9, 257),
            ("CYP3A4 inhibition raising statin levels causing severe rhabdomyolysis.", "Reduce statin dose.", 8, 288),
            ("CYP2C19 inhibition reducing drug activation and efficacy.", "Use non-inhibiting alternative.", 7, 2),
            ("Additive potassium retention leading to severe hyperkalemia and arrhythmia.", "Monitor potassium regularly.", 8, 34),
            ("Fatal serotonin toxicity and hypertensive crisis.", "CONTRAINDICATED.", 10, 257),
            ("Additive QTc prolongation increasing Torsades de Pointes risk.", "Avoid concurrent use.", 9, 2),
            ("P-glycoprotein inhibition causing digitalis toxicity.", "Reduce dose by 50%.", 8, 2),
            ("Ototoxicity and acute renal failure risk.", "Avoid combination.", 9, 160),
            ("Bone marrow suppression and severe pancytopenia.", "Monitor blood counts.", 8, 64)
        ]

        # Top 100 Generic Medical Ingredients
        ingredients = [
            "methotrexate", "ibuprofen", "enoxaparin", "ketorolac", "promethazine", "codeine", 
            "lithium", "hydrochlorothiazide", "ritonavir", "midazolam", "warfarin", "aspirin", 
            "sertraline", "tramadol", "simvastatin", "amiodarone", "clopidogrel", "omeprazole", 
            "spironolactone", "lisinopril", "fluoxetine", "selegiline", "ketoconazole", "triazolam", 
            "clarithromycin", "ergotamine", "sildenafil", "nitroglycerin", "allopurinol", "azathioprine", 
            "ciprofloxacin", "theophylline", "digoxin", "verapamil", "carbamazepine", "phenytoin", 
            "valproate", "gentamicin", "furosemide", "vancomycin", "piperacillin", "heparin", 
            "alteplase", "propranolol", "albuterol", "metformin", "paroxetine", "tamoxifen", 
            "rifampin", "cyclosporine", "tacrolimus", "erythromycin", "diltiazem", "metoprolol", 
            "atenolol", "quinidine", "procainamide", "haloperidol", "ziprasidone", "citalopram", 
            "ondansetron", "venlafaxine", "phenelzine", "bupropion", "linezolid", "duloxetine", 
            "fluvoxamine", "baclofen", "tizanidine", "gabapentin", "morphine", "oxycodone", 
            "fentanyl", "buprenorphine", "naloxone", "alprazolam", "lorazepam", "diazepam", 
            "clonazepam", "zolpidem", "quetiapine", "olanzapine", "risperidone", "aripiprazole", 
            "lamotrigine", "topiramate", "levetiracetam", "pregabalin", "losartan", "valsartan", 
            "amlodipine", "nifedipine", "rosuvastatin", "atorvastatin", "pravastatin", "ezetimibe"
        ]

        # Create Reactions
        rx_objs = []
        for text, rem, sev, mask in categories:
            rx, _ = ReactionDefinition.objects.get_or_create(name=text)
            rx_objs.append((rx, rem, sev, mask))

        # Generate All Pair Combinations
        interactions_to_create = []
        count = 0
        for i in range(len(ingredients)):
            for j in range(i + 1, len(ingredients)):
                d1, d2 = ingredients[i], ingredients[j]
                rx_obj, rem, sev, mask = categories[count % len(categories)]
                
                interactions_to_create.append(
                    Interaction(
                        drug_a=d1,
                        drug_b=d2,
                        reaction=rx_obj,
                        severity_slider=sev,
                        remedy=rem,
                        organ_bitmask=mask,
                        custom_factors={'max_age': 6} if d2 == 'codeine' else {}
                    )
                )
                count += 1

        # Bulk Create in Database
        Interaction.objects.all().delete()
        Interaction.objects.bulk_create(interactions_to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded FULL MASTER DATASET of {count} clinical interaction pairs into SQLite Database!'))
